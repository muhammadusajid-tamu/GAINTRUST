import os
import re
import json
import logging
import anthropic
import subprocess
import matplotlib.pyplot as plt
from error import Error
from pathlib import Path
from typing import List
from collections import defaultdict
from contextlib import contextmanager
from tenacity import retry, wait_random_exponential


@contextmanager
def cd(path: Path):
    """Sets the cwd within the context

    Args:
        path (Path): The path to the cwd

    Yields:
        None
    """

    origin = Path().absolute()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)


def tag(content: str, tag_name: str) -> str:
    if not content:
        return content
    return f"\n<{tag_name}>\n{content}\n</{tag_name}>\n"


def make_prompt(
    preamble: str,
    code: str,
    examples: str,
    enhancement: str,
    instruction: str,
) -> str:
    assert code
    assert preamble
    assert instruction
    prompt = f"""{anthropic.HUMAN_PROMPT}\n\n{preamble + tag(code, "code") + tag(examples, "testcases") + enhancement + instruction}{anthropic.AI_PROMPT}"""

    return prompt


# ==== Experimental constraints

constraint_wrap_code: str = "Wrap any code in <code></code> blocks"
constraint_code_only: str = (
    "Give me code only, don't include any explanations in your responses"
)
constraint_na: str = 'Return "N/A" if you can not find an answer'
constraints_style: List[str] = [
    "Don't use raw pointers.",
    "Use box pointer whenever possible. Box pointers are preferable to other alternatives.",
    "Try not to use Rust Traits if possible.",
    "Try not to use Generics if possible.",
]


def make_instruction(preamble: str, constraints: List[str]) -> str:
    constraints_str = ""
    for c_id, constraint in enumerate(constraints):
        constraints_str = constraints_str + "\n\t" + str(c_id + 1) + ". " + constraint

    constraints_str = tag(constraints_str, "list")

    if not preamble.endswith("\n"):
        preamble = preamble + "\n"

    instruction = preamble + constraints_str

    return instruction


@retry(wait=wait_random_exponential(multiplier=1, max=120))
def claude_gen(query_engine, prompt, model_params={"temperature": 0.2}):
    return query_engine.raw_query(prompt, model_params)
    # body = json.dumps(
    #     {
    #         "prompt": prompt,
    #         "max_tokens_to_sample": 2000,
    #         "temperature": model_params["temperature"],
    #     }
    # )

    # modelId = "anthropic.claude-v2:1"  # TODO compare anthropic.claude-v2 and anthropropic.claude-v2:1 later
    # accept = "application/json"
    # contentType = "application/json"

    # response = bedrock.invoke_model(
    #     body=body, modelId=modelId, accept=accept, contentType=contentType
    # )
    # response_body = json.loads(response.get("body").read())
    # answer = response_body.get("completion")

    # if answer.startswith(" "):
    #     answer = answer[1:]

    # logging.info(
    #     f"A query to Anthropic Claude2 is made with model paramters as follows: {str(model_params)}"
    # )
    # return answer


def clean_answer_llm(answer):
    # TODO Maybe try later, but below mechanical clean works well so far.
    cln_instruction = "\n\nIf there is any non-code related text above, clean it. I only want the code back. \n\n"
    cln_prompt = (
        f"""{anthropic.HUMAN_PROMPT} {answer + cln_instruction} {anthropic.AI_PROMPT}"""
    )
    cln_answer = claude_gen(cln_prompt)

    return cln_answer


# ==== Experimental code extraction


def extract_code(response: str) -> str:
    tagged_block = re.search(r"<code>(?P<code>[\s\S]*)</code>", response)
    if tagged_block:
        return tagged_block["code"]
    backticked_block = re.search(r"```(rust)?(?P<code>[\s\S]*)```", response)
    if backticked_block:
        return backticked_block["code"]

    def legacy_clean(answer: str) -> str:
        answer = answer.replace("Here is the fixed code:", "")
        answer = answer.replace("Here is the code with the fix:", "")
        answer = re.sub(
            r"\*.*?\*", "", answer
        )  # as suggested at https://docs.anthropic.com/claude/docs/claude-outputs-asterisk-actions
        if "The key change" in answer:
            expln_idx = answer.index("The key change")
            answer = answer[:expln_idx]
        elif "The main change" in answer:
            expln_idx = answer.index("The main change")
            answer = answer[:expln_idx]
        elif "The key difference" in answer:
            expln_idx = answer.index("The key difference")
            answer = answer[:expln_idx]
        elif "The fix was" in answer:
            expln_idx = answer.index("The fix was")
            answer = answer[:expln_idx]
        elif "The key fix" in answer:
            expln_idx = answer.index("The key fix")
            answer = answer[:expln_idx]

        return answer

    return legacy_clean(response)


def clean_answer_mech(answer):
    tagged_block = re.search(r"<code>(?P<code>[\s\S]*)</code>", answer)
    if tagged_block:
        return tagged_block["code"]
    backticked_block = re.search(r"```(rust)?(?P<code>[\s\S]*)```", answer)
    if backticked_block:
        return backticked_block["code"]

    answer = answer.replace("```rust", "").replace("```", "")
    answer = answer.replace("Here is the fixed code:", "")
    answer = answer.replace("Here is the code with the fix:", "")
    answer = re.sub(
        r"\*.*?\*", "", answer
    )  # as suggested at https://docs.anthropic.com/claude/docs/claude-outputs-asterisk-actions

    # TODO watchout, might not be complete
    answer = "\n" + answer
    use_ind, fn_ind, unsafe_ind, struct_ind = (
        answer.find("\nuse "),
        answer.find("\nfn "),
        answer.find("\nunsafe "),
        answer.find("\nstruct "),
    )
    if fn_ind == -1:
        fn_ind = answer.find("\npub fn ")
    if struct_ind == -1:
        struct_ind = answer.find("\npub struct ")

    if use_ind == -1:
        use_ind = 2**32
    if fn_ind == -1:
        fn_ind = 2**32
    if unsafe_ind == -1:
        unsafe_ind = 2**32
    if struct_ind == -1:
        struct_ind = 2**32

    code_bgn_ind = min(use_ind, fn_ind, unsafe_ind, struct_ind)
    answer = answer[code_bgn_ind:]

    if "The key change" in answer:
        expln_idx = answer.index("The key change")
        answer = answer[:expln_idx]
    elif "The main change" in answer:
        expln_idx = answer.index("The main change")
        answer = answer[:expln_idx]
    elif "The key difference" in answer:
        expln_idx = answer.index("The key difference")
        answer = answer[:expln_idx]
    elif "The fix was" in answer:
        expln_idx = answer.index("The fix was")
        answer = answer[:expln_idx]
    elif "The key fix" in answer:
        expln_idx = answer.index("The key fix")
        answer = answer[:expln_idx]

    # TODO watchout, not complete
    answer = answer + "\n"
    close_ind = answer.rfind("}\n")
    answer = answer[: close_ind + 1]

    return answer


def compile_and_record_query(
    code: str, work_dir: str, prompt: str = "", log_id=0
) -> subprocess.CompletedProcess:
    crate_toml = Path(work_dir) / "Cargo.toml"
    if not crate_toml.exists():
        print("DEBUG: Initializing crate")
        if not Path(work_dir).exists():
            subprocess.run(f"cargo new --lib {work_dir}", capture_output=True, shell=True)
        else:
            subprocess.run(f"cargo init --lib {work_dir}", capture_output=True, shell=True)
        # Add default dependencies
        with open(crate_toml, "a", encoding="utf-8") as fw:
            fw.write("\n[dependencies]\n")
            fw.write('rand = "0.8.4"\n')
            fw.write('libc = "0.2"\n')
            fw.write('regex = "1.10.2"\n')
            fw.write('lazy_static = "1.4.0"\n')
            fw.write('once_cell = "1.19.0"\n')
    else:
        print("DEBUG: Crate exists, cleaning")
        with cd(work_dir):
            subprocess.run("cargo clean", capture_output=True, shell=True)

    os.makedirs(f"{work_dir}/logs", exist_ok=True)
    os.makedirs(f"{work_dir}/src", exist_ok=True)
    with open(f"{work_dir}/logs/prog_{log_id}.ans", "w") as f:
        f.write(f"{prompt}\n\n==========\n\n{code}")
    with open(f"{work_dir}/logs/prog_{log_id}.rs", "w") as f:
        f.write(code)  # for logging purpose
    with open(f"{work_dir}/src/lib.rs", "w", encoding="utf-8") as f:
        f.write(code)  # will be overwritten by feedback fixes

    with cd(f"{work_dir}"):
        comp_output = subprocess.run(
            f'RUSTFLAGS="-Z track-diagnostics -Z time-passes" cargo build --manifest-path Cargo.toml',
            capture_output=True,
            shell=True,
        )
    
    print("DEBUG: Called cargo build")

    # comp_output = subprocess.run(f"rustc --out-dir {work_dir} -Z track-diagnostics {work_dir}/{fname_wout_ext}.rs", capture_output=True, shell=True)
    with open(f"{work_dir}/logs/prog_{log_id}.err", "wb") as file:
        file.write(comp_output.stderr)

    return comp_output


def rudra_suggest(work_dir: str, log_id) -> str:
    """Generate rudra-like suggestions by explaining Rust error codes."""
    import re
    err_path = os.path.join(work_dir, "logs", f"prog_{log_id}.err")
    if not os.path.exists(err_path):
        return ""
    suggestions = []
    with open(err_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.search(r"error\[(E[0-9]+)\]", line)
            if m:
                code = m.group(1)
                proc = subprocess.run(
                    f"rustc --explain {code}",
                    capture_output=True, shell=True
                )
                suggestions.append(proc.stdout.decode("utf-8", errors="ignore"))
    return "\n".join(suggestions)


def postprocess(answer, work_dir, prompt="", log_id=0):
    answer_clean = clean_answer_mech(answer)
    # if "fn main" not in answer_clean:
    #     answer_clean += "\n\nfn main(){}\n"

    crate_toml = Path(work_dir) / "Cargo.toml"
    if not crate_toml.exists():
        print("DEBUG: Initializing crate for postprocess")
        if not Path(work_dir).exists():
            subprocess.run(f"cargo new --lib {work_dir}", capture_output=True, shell=True)
        else:
            subprocess.run(f"cargo init --lib {work_dir}", capture_output=True, shell=True)
        # Add default dependencies
        with open(crate_toml, "a", encoding="utf-8") as fw:
            fw.write('rand = "0.8.4"\n')
            fw.write('libc = "0.2"\n')
            fw.write('regex = "1.10.2"\n')
            fw.write('lazy_static = "1.4.0"\n')
            fw.write('once_cell = "1.19.0"\n')
    else:
        with cd(work_dir):
            subprocess.run("cargo clean", capture_output=True, shell=True)

    os.makedirs(f"{work_dir}/logs", exist_ok=True)
    with open(f"{work_dir}/logs/prog_{log_id}.ans", "w") as f:
        f.write(f"{prompt}\n\n==========\n\n{answer}")
    with open(f"{work_dir}/logs/prog_{log_id}.rs", "w") as f:
        f.write(answer_clean)  # for logging purpose
    with open(f"{work_dir}/src/lib.rs", "w", encoding="utf-8") as f:
        f.write(answer_clean)  # will be overwritten by feedback fixes

    with cd(f"{work_dir}"):
        comp_output = subprocess.run(
            f'RUSTFLAGS="-Z track-diagnostics -Z time-passes" cargo build --manifest-path Cargo.toml',
            capture_output=True,
            shell=True,
        )

    # comp_output = subprocess.run(f"rustc --out-dir {work_dir} -Z track-diagnostics {work_dir}/{fname_wout_ext}.rs", capture_output=True, shell=True)
    with open(f"{work_dir}/logs/prog_{log_id}.err", "wb") as file:
        file.write(comp_output.stderr)

    return answer_clean, comp_output


def plot_err(paths, data):
    def autopct_format(values):
        def my_format(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return "{:.1f}%\n({v:d})".format(pct, v=val)

        return my_format

    for pt, dt in zip(paths, data):
        fig, ax = plt.subplots()

        _, texts, _ = ax.pie(
            dt.values(),
            labels=dt.keys(),
            autopct=autopct_format(dt.values()),
            textprops={"color": "w"},
            shadow=True,
        )
        for tx in texts:
            tx.set_fontsize(12)
        fig.savefig(pt, transparent=True)
        plt.close()
        # fig.savefig(f"transpilations/{src_lang}/base/{out_folder}/error_dist_before_fix.pdf")

    # fig, ax = plt.subplots()
    # ax.pie(cum_fnl_err_c_num_dict.values(), labels=cum_fnl_err_c_num_dict.keys(), autopct='%1.1f%%', shadow=True)
    # fig.savefig(f"transpilations/{src_lang}/{bm_path}/base/{out_folder}/error_dist_after_fix.pdf")


def parse_error_timepass(stderr, fname):
    print("DEBUG: Parsing errors")
    lines = stderr.decode("utf-8").splitlines()
    ln_cnt = 0
    line = lines[ln_cnt]
    while (
        f"Compiling wspace" not in line
    ):  # WATCHOUT HERE: wspace is the name of the cargo project. Has to be updated if the path that we write transpiled rust code changes
        ln_cnt += 1
        line = lines[ln_cnt]

    relevant_lines = lines[ln_cnt + 1 :]

    errors, compilation_steps = [], []
    cur_err_body, err_block = "", False
    common_comp_steps = ["free_global_ctxt", "total"]
    for line in relevant_lines:
        if re.match(
            r"error: could not compile \`wspace\` \(lib\) due to \d+ previous errors?",
            line,
        ):
            break
        if line.startswith("time:"):
            if err_block:
                errors.append(Error(cur_err_body))
                cur_err_body = ""
                err_block = False
            comp_step = re.split(r"\s+", line)[-1]  # line.split(r"\s+")[-1]
            if comp_step not in common_comp_steps:
                compilation_steps.append(comp_step)
        elif re.match(r"error(\[E\d\d\d\d\])?:", line) is not None:
            if err_block:
                errors.append(Error(cur_err_body))
            cur_err_body = line + "\n"
            err_block = True
        elif err_block:
            cur_err_body = cur_err_body + line + "\n"
        else:
            pass

    err_code_num, err_diag_num = defaultdict(int), defaultdict(int)
    for err in errors:
        err_code_num[err.code] += 1
        err_diag_num[err.diagnostic] += 1

    print("DEBUG: Found errors:", len(errors))
    return errors, err_code_num, err_diag_num, compilation_steps, len(errors)


def parse_error_coarse(stderr):
    msg_blocks = stderr.decode("utf-8").split("\n\n")
    # err_blocks, err_codes = [], []
    errors = []
    err_c_num_dict = defaultdict(int)
    err_comp_phase_num_dict = defaultdict(int)
    for body in msg_blocks[:-1]:  # last two are not error msg block
        if (
            "Finished" not in body
            and "warning:" not in body
            and len(body.split("\n")) > 3
        ):  # TODO make this check more proper/robust, this is for Cargo build
            err_c_match = re.search(r"error\[E[0-9]+\]", body)
            # err_nc_match = re.search(r"error: ", body)
            diag_match = re.search(r"-Ztrack-diagnostics.*", body)

            # elif err_nc_match is not None and len(body.split("\n")) > 2:  # second part is needed because of error summary at the end of the file
            if err_c_match is not None:
                err_c = err_c_match.group(0)
            else:
                err_c = "E[NOCODE]"

            # precaution against some strange reason
            if diag_match is not None:
                compile_step = diag_match.group(0).split("/")[1]
            else:
                compile_step = "NotFound"

            body = re.sub(
                r"\s*(Compiling|Updating).*\n", "", body
            )  # the first block contains other logs, clean them

            err = Error(body)
            errors.append(err)

            err_c_num_dict[err_c] += 1
            err_comp_phase_num_dict[compile_step] += 1

    return errors, err_c_num_dict, err_comp_phase_num_dict


def track_fix(fix_state):
    fix_path = []
    while fix_state["parent"] is not None:
        fix_path.append(fix_state["fix"])
        fix_state = fix_state["parent"]

    fix_path.reverse()

    return fix_path


def get_coverage(test_suite_path):
    # cat counter_examples.json | RUSTFLAGS="-C instrument-coverage" cargo test --manifest-path PATH/TO/FUZZING_TARGET/Cargo.toml --features replay -- --nocapture

    counterexamples = json.load(open(test_suite_path))

    parent_dir = Path(test_suite_path).parent.absolute()
    all_cov, proc_lines = [], []
    cov_to_ce = defaultdict(list)
    for cnt, ce in enumerate(counterexamples):
        if cnt == 50:
            break  # TODO REMOVE THIS

        with open(parent_dir / "counter_examples.json", "w") as fw:
            json.dump([ce], fw)

        with cd(parent_dir):
            subprocess.run(
                'cat counter_examples.json | RUSTFLAGS="-C instrument-coverage" cargo test --manifest-path replay/Cargo.toml --features replay -- --nocapture &> /dev/null',
                shell=True,
            )

        with cd(parent_dir):

            test_bin_out = subprocess.run(
                f'RUSTFLAGS="-C instrument-coverage" cargo test --manifest-path replay/Cargo.toml --tests --no-run --message-format=json | jq -r "select(.profile.test == true) | .filenames[]" | grep -v dSYM -',
                capture_output=True,
                check=True,
                shell=True,
            )
            test_bin = test_bin_out.stdout.decode("utf-8").strip()
            cov_report = cov_report_out.stdout.decode("utf-8").strip()

            # clean before next ce
            subprocess.run("rm replay/*.profraw", shell=True)
            subprocess.run("rm cov.profdata", shell=True)

        l_cov, proc_lines = parse_coverage(
            cov_report
        )  # processed lines are the same for all counterexamples, so we ovrewrite
        all_cov.append(l_cov)
        cov_to_ce[str(l_cov)].append(ce)

    return cov_to_ce, all_cov, proc_lines


def parse_coverage(cov_report):
    cov_report_relevant = cov_report.split("/replay/src/lib.rs:\n")[1]
    cov_lines = cov_report_relevant.splitlines()
    line_coverage, processed_lines = [], []
    start = False
    for line_idx, line in enumerate(cov_lines):
        if "mod communication {" in line:
            break
        if 'extern "C" {' in line:
            start = True
        if not line.strip() or not start:
            continue

        cov_data = line.split("|")

        try:
            _ = int(cov_data[0].strip())

            processed_lines.append(cov_data[-1])

            if not cov_data[1].strip():
                line_coverage.append(-1)
            else:
                cvrg = 0
                if int(cov_data[1].strip()) >= 1:
                    cvrg = 1

                line_coverage.append(cvrg)

        except:
            pass

    return line_coverage, processed_lines


def dstar(num_cf, num_uf, num_cs, num_us, star=3):
    if num_cs + num_uf == 0:
        return 1
    return num_cf**star / (num_cs + num_uf)


def tarantula(num_cf, num_uf, num_cs, num_us):
    try:
        return num_cf / (num_cf + num_uf) / (num_cf / (num_cf + num_uf)) + (
            num_cs / (num_cs + num_us)
        )
    except ZeroDivisionError:
        return 0


def ochiai(num_cf, num_uf, num_cs, num_us):
    try:
        return num_cf / ((num_cf + num_uf) * (num_cf + num_cs)) ** (0.5)
    except ZeroDivisionError:
        return 0
