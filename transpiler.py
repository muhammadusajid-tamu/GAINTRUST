import json
import logging
import anthropic
from llms import QueryEngine, Prompt
from utils import *


class Transpiler:
    def __init__(
        self,
        prompt,
        comp_fixer,
        eq_fixer,
        src_lang,
        benchmark,
        fname,
        query_engine: QueryEngine,
        transpl_attempt_budget,
        work_dir,
        model_params={"temperature": 0.2},
    ) -> None:
        self.src_lang = src_lang
        self.benchmark = benchmark
        self.fname = fname
        self.benchmark_path = f"bms/{src_lang}/{benchmark}"
        # self.benchmark_workspace = f"benchmarks/workspace"
        self.prompt = prompt
        self.comp_fixer = comp_fixer
        self.eq_fixer = eq_fixer
        self.query_engine = query_engine
        self.transpl_attempt_budget = transpl_attempt_budget
        # self.tag = tag
        self.hint = ""
        self.model_params = model_params
        self.work_dir = work_dir

    def transpile(self):
        if self.prompt == "base":
            return self.transpile_base()
        elif self.prompt == "mutate":
            return self.transpile_mutate()
        elif self.prompt == "decomp-iter":
            return self.transpile_decomp_iter()

    def update_prompt(self, cur_code, cur_answer):
        prompt = Prompt(
            context=f"You are given a {self.src_lang.capitalize()} code contained in <code> tags. We need to translate this code to Rust."
            + tag(cur_code, "code"),
            instruction=f"Give me the Rust translation of the above {self.src_lang.capitalize()} code.",
            constraints=[
                "Make sure it includes all imports, uses safe rust, and compiles.",
                "Use the same function name, same argument and return types.",
                "Don't use raw pointers.",
                "Use box pointer whenever possible. Box pointers are preferable to other alternatives.",
                "Try not to use Traits if possible. I would not like to have Traits in resulting Rust code.",
                "Try not to use custom Generics if possible.",
                "Do not give me main function.",
            ],
            preamble=cur_answer,
        )

        return prompt

    def transpile_decomp_iter(self):
        compiles = False
        logging.info(f"Now transpiling {self.fname}.")

        src_dir = f"{self.work_dir}/wspace/"
        res_dir = f"{self.work_dir}/results/"

        source_dict = json.load(open(f"{self.benchmark_path}/{self.fname}.json", "r"))
        imports = source_dict["Includes"]
        structs = source_dict["Structs"]
        declarations = source_dict["Function Declarations"]
        implementations = source_dict["Function Implementations"]
        enums = source_dict["Enums"]
        defines = source_dict["Defines"]
        type_defs = source_dict["TypeDefs"]
        global_vars = source_dict["Globals"]
        all_aux = (
            "\n".join(enums)
            + "\n"
            + "\n".join(type_defs)
            + "\n"
            + "\n".join(defines)
            + "\n"
            + "\n".join(global_vars)
        )

        func_name = "header"

        all_imp = "\n".join(imports)
        all_st = "\n".join(structs)
        # cur_code = "\n" + all_imp + "\n" + all_st
        cur_code = "\n" + all_imp + "\n" + all_aux + "\n" + all_st
        cur_answer = ""

        prompt = Prompt(
            context=f"You are given a {self.src_lang.capitalize()} code contained in <code> tags. "
            + "This code contains only import statements and possibly structs and gloabal variables. We need to translate this code piece to Rust.\n"
            + tag(cur_code, "code"),
            instruction=f"Give me the Rust translation of the above {self.src_lang.capitalize()} code.",
            constraints=[
                "Make sure it includes all imports, uses safe rust, and compiles.",
                "Don't use raw pointers.",
                "Use box pointer whenever possible. Box pointers are preferable to other alternatives.",
                "Try not to use Traits if possible. I would not like to have Traits in resulting Rust code.",
                "Try not to use custom Generics if possible.",
                "Do not give me main function.",
            ],
        )

        for func_dec, func_impl in zip(declarations, implementations):
            logging.info(f"   Working on {func_name} function.")

            min_num_errs = 2**32
            for attempt in range(1, self.transpl_attempt_budget + 1):
                # answer = claude_gen(
                #     self.query_engine, prompt, model_params=self.model_params
                # )
                # cand_answer_processed, comp_out = postprocess(
                #     answer, src_dir, prompt, log_id=func_name
                # )
                answer = self.query_engine.generate_code(prompt, model_params=self.model_params)
                cand_answer_processed = answer
                comp_out = compile_and_record_query(answer, src_dir, self.query_engine.stringify_prompt(prompt), log_id=func_name)
                parsed_comp_out = parse_error_timepass(comp_out.stderr, self.fname)
                num_errs = parsed_comp_out[-1]

                logging.info(f"\tAttempt {attempt}: {num_errs} errors.")
                if num_errs < min_num_errs:
                    min_num_errs = num_errs
                    best_answer_processed = cand_answer_processed

                if not num_errs:
                    break


            # answer_processed, _ = postprocess(
            #     best_answer_processed, src_dir, prompt, log_id=func_name
            # )
            _ = compile_and_record_query(best_answer_processed, src_dir, self.query_engine.stringify_prompt(prompt), log_id=func_name)
            answer_processed = best_answer_processed

            cur_answer += answer_processed
            cur_code = cur_code + "\n" + func_dec + "\n" + func_impl

            prompt = self.update_prompt(cur_code, cur_answer)

            if self.src_lang == "c":
                func_name = (
                    func_dec.split("(")[0].split("\n")[-1].strip().split(" ")[-1]
                )
            else:
                func_name = (
                    func_impl.split("{")[0]
                    .split("(")[-2]
                    .split("\n")[-1]
                    .strip()
                    .split(" ")[-1]
                )

        logging.info(f"   Working on {func_name} function.")
        min_num_errs = 2**32
        for attempt in range(1, self.transpl_attempt_budget + 1):
            answer = self.query_engine.generate_code(prompt, model_params=self.model_params)
            cand_answer_processed = answer
            comp_out = compile_and_record_query(answer, src_dir, self.query_engine.stringify_prompt(prompt), log_id=func_name)

            parsed_comp_out = parse_error_timepass(comp_out.stderr, self.fname)
            num_errs = parsed_comp_out[-1]

            logging.info(f"\tAttempt {attempt}: {num_errs} errors.")
            if num_errs < min_num_errs:
                min_num_errs = num_errs
                best_answer_processed = cand_answer_processed

            if not num_errs:
                break

        cur_answer += best_answer_processed

        comp_out = compile_and_record_query(cur_answer, src_dir, self.query_engine.stringify_prompt(prompt), log_id=func_name)
        answer_processed = cur_answer
        parsed_comp_out = parse_error_timepass(comp_out.stderr, self.fname)

        if self.comp_fixer.fix_type == "comp-msft-fix" and parsed_comp_out[-1]:
            logging.info(
                "\tTranspilation FAILED. Attempting to fix compilation errors via LLM."
            )
            _, _, _, _, init_num_err = parsed_comp_out

            rust_code, fnl_num_err, num_llm_call = self.comp_fixer.fix(
                answer_processed, parsed_comp_out, src_dir
            )

            logging.info(
                f"\t\tNum errors decreased from {init_num_err} to {fnl_num_err}. Fix path was {self.comp_fixer.fix_path}."
            )
            if not fnl_num_err:
                os.makedirs(f"{res_dir}", exist_ok=True)
                subprocess.run(
                    f"cp {self.benchmark_path}/{self.fname}.json {res_dir}/", shell=True
                )
                subprocess.run(
                    f"cp {self.benchmark_path}/{self.fname}.{self.src_lang} {res_dir}/", shell=True
                )

                with open(f"{res_dir}/{self.fname}.rs", "w") as fw:
                    fw.write(rust_code)

                compiles = True

        elif (
            self.comp_fixer is not None and parsed_comp_out[-1]
        ):  # if comp_fixer is set and if there is error
            logging.info(
                "\tTranspilation FAILED. Attempting to fix compilation errors via LLM."
            )
            rust_code, fnl_comp_out, num_llm_call = self.comp_fixer.fix(
                answer_processed, parsed_comp_out, src_dir
            )

            logging.info(
                f"\t\tNum errors decreased from {init_num_err} to {fnl_comp_out[-1]}. Fix path was {self.comp_fixer.fix_path}."
            )
            if not fnl_comp_out[-1]:
                os.makedirs(f"{res_dir}/", exist_ok=True)
                subprocess.run(
                    f"cp {self.benchmark_path}/{self.fname}.json {res_dir}/", shell=True
                )

                with open(f"{res_dir}/{self.fname}.rs", "w") as fw:
                    fw.write(rust_code)

                compiles = True
        else:
            logging.info("\tTranspilation PASSED.")
            # num_pass_transpl += 1

            os.makedirs(f"{res_dir}", exist_ok=True)
            subprocess.run(
                f"cp {self.benchmark_path}/{self.fname}.json {res_dir}/", shell=True
            )
            subprocess.run(
                f"cp {self.benchmark_path}/{self.fname}.{self.src_lang} {res_dir}/", shell=True
            )

            with open(f"{res_dir}/{self.fname}.rs", "w") as fw:
                fw.write(answer_processed)

            compiles = True

        # clean project to reduce size
        with cd(f"{src_dir}"):
            subprocess.run("cargo clean", capture_output=True, shell=True)

        return compiles

    def write_src_code_to_res_dir(self, res_dir: str, src_code: str):
        with open(f"{res_dir}/{self.fname}.{self.src_lang}", "w") as fw:
            fw.write(src_code)
        subprocess.run(
            f"cp {self.benchmark_path}/{self.fname}.json {res_dir}/",
            shell=True,
        )

    # @profile
    def transpile_base(self):
        cum_init_err_c_num_dict, cum_fnl_err_c_num_dict = {}, {}
        cum_init_err_phase_num_dict, cum_fnl_err_phase_num_dict = {}, {}
        tot_num_llm_call_for_fix, num_pass_transpl, num_complete_fixed_transpl = 0, 0, 0

        compiles = False
        logging.info(f"Now transpiling {self.fname}.")
        with open(f"{self.benchmark_path}/{self.fname}.{self.src_lang}", "r") as f:
            code = f.read()

        src_dir = f"{self.work_dir}/wspace/"
        res_dir = f"{self.work_dir}/results/"
        print("DEBUG: writing prompt")
        
        prompt = Prompt(
            context=(
                f"You are given a {self.src_lang.capitalize()} code contained in <code> tags."
                + " We need to translate this code to Rust.\n\n"
                + tag(code, "code")
            ),
            instruction=f"Give me Rust refactoring of above {self.src_lang.capitalize()} code.",
            constraints=[
                "Give me only the refactored code, don't add explanations comments or anything else.",
                "Use the same function name, same argument and return types.",
                "Make sure it includes all imports, uses safe rust, and compiles.",
                "Don't use raw pointers.",
                "Use box pointer whenever possible. Box pointers are preferable to other alternatives.",
                "Try not to use Traits if possible. I would not like to have Traits in resulting Rust code.",
                "Try not to use Generics if possible.",
                "Do NOT give a main() function or any example usage",

            ],
            extra_information=self.hint,
        )

        min_num_errs = 2**32
        for attempt in range(1, self.transpl_attempt_budget + 1):
            cand_answer_processed = self.query_engine.generate_code(
                prompt, model_params=self.model_params
            )
            print("DEBUG: prompted model")

            comp_out = compile_and_record_query(cand_answer_processed, src_dir, self.query_engine.stringify_prompt(prompt))
            print("DEBUG: compiled and recorded")

            cand_init_comp_out = parse_error_timepass(comp_out.stderr, self.fname)
            num_errs = cand_init_comp_out[-1]

            logging.info(f"\tAttempt {attempt}: {num_errs} errors.")
            if num_errs < min_num_errs:
                min_num_errs = num_errs
                best_answer_processed = cand_answer_processed

            if not num_errs:
                break

        # below is needed to write the best program to file
        # answer_processed, comp_out = postprocess(best_answer_processed, src_dir, prompt)
        comp_out = compile_and_record_query(best_answer_processed, src_dir, self.query_engine.stringify_prompt(prompt))
        answer_processed = best_answer_processed
        init_comp_out = parse_error_timepass(comp_out.stderr, self.fname)

        # apply cargo fix
        self.comp_fixer.cargo_fix(src_dir)

        if self.comp_fixer.fix_type == "comp-msft-fix" and init_comp_out[-1]:
            logging.info(
                "\tTranspilation FAILED. Attempting to fix compilation errors via LLM."
            )
            _, _, _, _, init_num_err = init_comp_out

            rust_code, fnl_num_err, num_llm_call = self.comp_fixer.fix(
                answer_processed, init_comp_out, src_dir
            )
            tot_num_llm_call_for_fix += num_llm_call

            logging.info(
                f"\t\tNum errors decreased from {init_num_err} to {fnl_num_err}. Fix path was {self.comp_fixer.fix_path}."
            )
            if not fnl_num_err:
                os.makedirs(f"{res_dir}", exist_ok=True)
                self.write_src_code_to_res_dir(res_dir, code)
                with open(f"{res_dir}/{self.fname}.rs", "w") as fw:
                    fw.write(rust_code)

                num_complete_fixed_transpl += 1
                compiles = True

        elif (
            self.comp_fixer is not None and init_comp_out[-1]
        ):  # if comp_fixer is set and if there is error
            logging.info(
                "\tTranspilation FAILED. Attempting to fix compilation errors via LLM."
            )
            rust_code, fnl_comp_out, num_llm_call = self.comp_fixer.fix(
                answer_processed, init_comp_out, src_dir
            )

            tot_num_llm_call_for_fix += num_llm_call
            (
                _,
                init_err_c_num_dict,
                init_err_phase_num_dict,
                _,
                init_num_err,
            ) = init_comp_out
            _, fnl_err_c_num_dict, fnl_err_phase_num_dict, _, fnl_num_err = fnl_comp_out

            logging.info(
                f"\t\tNum errors decreased from {init_num_err} to {fnl_num_err}. Fix path was {self.comp_fixer.fix_path}."
            )
            if not fnl_num_err:
                os.makedirs(f"{res_dir}/", exist_ok=True)
                self.write_src_code_to_res_dir(res_dir, code)
                with open(f"{res_dir}/{self.fname}.rs", "w") as fw:
                    fw.write(rust_code)

                num_complete_fixed_transpl += 1
                compiles = True

            cum_init_err_c_num_dict = {
                k: cum_init_err_c_num_dict.get(k, 0) + init_err_c_num_dict.get(k, 0)
                for k in set(cum_init_err_c_num_dict) | set(init_err_c_num_dict)
            }
            cum_fnl_err_c_num_dict = {
                k: cum_fnl_err_c_num_dict.get(k, 0) + fnl_err_c_num_dict.get(k, 0)
                for k in set(cum_fnl_err_c_num_dict) | set(fnl_err_c_num_dict)
            }
            cum_init_err_phase_num_dict = {
                k: cum_init_err_phase_num_dict.get(k, 0)
                + init_err_phase_num_dict.get(k, 0)
                for k in set(cum_init_err_phase_num_dict) | set(init_err_phase_num_dict)
            }
            cum_fnl_err_phase_num_dict = {
                k: cum_fnl_err_phase_num_dict.get(k, 0)
                + fnl_err_phase_num_dict.get(k, 0)
                for k in set(cum_fnl_err_phase_num_dict) | set(fnl_err_phase_num_dict)
            }
        elif init_comp_out[-1]:
            logging.info("\tTranspilation FAILED. No fixer is set.")
        else:
            logging.info("\tTranspilation PASSED.")
            num_pass_transpl += 1

            os.makedirs(f"{res_dir}", exist_ok=True)
            self.write_src_code_to_res_dir(res_dir, code)
            with open(f"{res_dir}/{self.fname}.rs", "w") as fw:
                fw.write(answer_processed)

            compiles = True

        # clean project to reduce size
        with cd(f"{src_dir}"):
            subprocess.run("cargo clean", capture_output=True, shell=True)

        return compiles
