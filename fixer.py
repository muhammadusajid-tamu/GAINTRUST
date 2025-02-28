import copy
import random
import logging
import anthropic
import subprocess
import numpy as np
from llms import Prompt, QueryEngine
from utils import *


class Fixer:
    def __init__(
        self, fix_type, query_engine: QueryEngine, comp_fix_attempt_budget=3
    ) -> None:
        self.comp_fix_attempt_budget = comp_fix_attempt_budget
        self.fix_type = fix_type
        self.query_engine = query_engine

    def fix(self, rust_code="", comp_out=None, work_dir=None):
        self.fix_path = []
        return self.comp_fix_msft_work(rust_code, comp_out, work_dir)

    def cargo_fix(self, work_dir):
        with cd(f"{work_dir}"):
            subprocess.run(f"cargo clean", capture_output=True, shell=True)
            comp_output_bf_cfix = subprocess.run(
                f'RUSTFLAGS="-Z track-diagnostics -Z time-passes" cargo build --manifest-path Cargo.toml',
                capture_output=True,
                shell=True,
            )
            _, _, _, _, init_num_errors = parse_error_timepass(
                comp_output_bf_cfix.stderr, work_dir.split("/")[-1]
            )

            subprocess.run(f"cargo fix --allow-no-vcs", capture_output=True, shell=True)

            subprocess.run(f"cargo clean", capture_output=True, shell=True)
            comp_output_af_cfix = subprocess.run(
                f'RUSTFLAGS="-Z track-diagnostics -Z time-passes" cargo build --manifest-path Cargo.toml',
                capture_output=True,
                shell=True,
            )
            _, _, _, _, fnl_num_errors = parse_error_timepass(
                comp_output_af_cfix.stderr, work_dir.split("/")[-1]
            )

            logging.info(
                f"\tNumber of errors decreased from {init_num_errors} to {fnl_num_errors} with cargo fix."
            )

    def comp_fix_msft_work(self, rust_code, init_comp_out, work_dir):
        errors = init_comp_out[0]
        num_llm_call = 0
        while errors:
            snap = rust_code
            error = random.choice(errors)

            cur_errors = set([error])
            rep_counter = 0
            while True:
                cur_err = cur_errors.pop()
                prompt = Prompt(
                    context=(
                        f"You are given a Rust code contained in <code> tags.\n"
                        + tag(rust_code, "code")
                        + "\n"
                        + "This code does not compile. Here are some error messages contained in <error-message> tags\n"
                        + tag(cur_err.body, "error-message")
                        + "\n"
                    ),
                    instruction="Fix the above compilation errors.",
                    constraints=[
                        # "Give me the whole fixed code back, dont add explanation, comment or anything else.",
                        "Use only safe Rust.",
                        "Don't use raw pointers.",
                        "Use box pointer whenever possible. Box pointers are preferable to other alternatives.",
                        "Try not to use Traits if possible. I would not like to have Traits in resulting Rust code.",
                        "Try not to use Generics if possible.",
                        "Do not put any explanation or example comments.",
                        "Do not add a main function",
                    ],
                )

                rust_code = self.query_engine.generate_code(prompt)
                num_llm_call += 1  # increment before log
                comp_output = compile_and_record_query(
                    rust_code, work_dir, self.query_engine.stringify_prompt(prompt), num_llm_call
                )

                fnl_comp_out = parse_error_timepass(
                    comp_output.stderr, work_dir.split("/")[-1]
                )
                new_errors = fnl_comp_out[0]
                cur_errors = set(new_errors) - set(errors)

                if not cur_errors:
                    errors = new_errors
                    break

                rep_counter += 1
                if rep_counter == 4:
                    rust_code = snap
                    break

            # we project that 12 would give #llm_calls similar to adv-err-fix
            if num_llm_call >= 10:
                break

        return rust_code, len(errors), num_llm_call

    def compare(
        self,
        cur_errors,
        prev_errors,
        cur_err_code_num,
        prev_err_code_num,
        cur_comp_steps,
        prev_comp_steps,
        err_code="",
    ):
        # TODO remove this, old basic comparison
        ##########################################
        # if len(cur_errors) < len(prev_errors) or cur_err_code_num[err_code] < prev_err_code_num[err_code]:
        #     self.fix_path.append(1)
        #     return True
        # else:
        #     self.fix_path.append(-1)
        #     return False
        ##########################################

        # current set of errors is a subset of previous set of errors
        cond1 = not set(cur_errors) - set(prev_errors) and not len(cur_errors) == len(
            prev_errors
        )
        if cond1:
            self.fix_path.append(1)
            return True

        def find_last_match(cur_comp_steps, prev_comp_steps):
            for d_cur, step_cur in enumerate(reversed(cur_comp_steps)):
                for d_prev, step_prev in enumerate(reversed(prev_comp_steps)):
                    if step_cur == step_prev:
                        return d_cur, d_prev

            return len(cur_comp_steps), len(prev_comp_steps)

        d_cur, d_prev = find_last_match(cur_comp_steps, prev_comp_steps)

        # compilation steps for the current code is deeper.
        # we also force the matching step to be at the last position.
        # otherwise it means that there is divergence (different code can go through different steps)
        # and in that situation making any claim is not straightforward.
        cond2 = d_cur > 0 and d_prev == 0
        if cond2:
            self.fix_path.append(2)
            return True

        # (compilation go through the same steps or diverges before end) and (number of errors decreased, or number of attempted error decreased).
        cond3 = ((d_cur == 0 and d_prev == 0) or (d_cur > 0 and d_prev > 0)) and (
            len(cur_errors) < len(prev_errors)
            or cur_err_code_num[err_code] < prev_err_code_num[err_code]
        )
        if cond3:
            self.fix_path.append(3)
            return True

        self.fix_path.append(-1)
        return False
