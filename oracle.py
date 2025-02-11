import logging
import os
import subprocess
import tempfile
import shutil
import json
from dataclasses import dataclass
from collections import defaultdict
from typing import Any, Optional, Tuple, List, Dict


def get_path(path: str) -> str:
    if not os.path.exists(path):
        raise RuntimeError(f"{path} not found")
    return path


if not os.path.exists("Differential_Tester"):
    raise RuntimeError("Expect verifier")

instrumentors = {
    "go": "Differential_Tester/.bin/instrument-go/instrument",
    "rust": "Differential_Tester/.bin/instrument-rust/release/instrument",
    "c": "Differential_Tester/.bin/instrument-c/release/instrument",
}

for language, path in instrumentors.items():
    if not os.path.exists(path):
        raise RuntimeError(f"Missing instrumentor for {language}")

n_counter_examples = 1000


def instrument_go(src_file: str, tmp_dir: str) -> None:
    shutil.copy(src_file, tmp_dir + "/ground_truth.go")
    subprocess.check_call([instrumentors["go"], tmp_dir + "/ground_truth.go"])
    subprocess.check_call(["go", "fmt", tmp_dir + "/ground_truth.go"])
    subprocess.check_call(
        [
            "go",
            "build",
            "-buildmode",
            "c-shared",
            "-o",
            tmp_dir + "/libground_truth.so",
            tmp_dir + "/ground_truth.go",
        ]
    )


# requires installing the following: sudo yum install -y gcc10.x86_64 gcc10-c++.x86_64
def instrument_c(src_file: str, tmp_dir: str) -> None:
    subprocess.check_call(
        [instrumentors["c"], "-f", src_file, "-o", tmp_dir + "/ground_truth"]
    )
    subprocess.check_call(
        [
            "cmake",
            "-DCMAKE_CXX_COMPILER=gcc10-c++",
            "-S",
            tmp_dir + "/ground_truth",
            "-B",
            tmp_dir + "/ground_truth/_build",
        ]
    )
    subprocess.check_call(["cmake", "--build", tmp_dir + "/ground_truth/_build"])
    subprocess.check_call(
        ["mv", tmp_dir + "/ground_truth/_build/libground_truth.so", tmp_dir]
    )


def instrument(
    language: str, res_dir: str, submodule_name: str, output_dir: str
) -> None:
    """
    Instrument the source directory

    Args:
        language (str): The language of concern.
        res_dir (str): Path to the results directory where original and traspiled code can be found.
        submodule_name (str): Name of the submodule.
        output_dir (str): Path to the output directory.

    Returns:
        None.

    Raises:
        FileExistsError: If output_dir already exists.
        CalledProcessError: If instrumentation fails.
    """
    logging.info(f"Instrumenting {submodule_name}")
    rs_file: str = get_path(f"{res_dir}/{submodule_name}.rs")
    if os.path.exists(output_dir):
        raise FileExistsError(
            f"output directory {output_dir} exists, cannot instrument {submodule_name}"
        )
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_file: str
        if language == "go":
            src_file = get_path(f"{res_dir}/{submodule_name}.go")
            instrument_go(src_file, tmp_dir)
        elif language == "c":
            src_file = get_path(f"{res_dir}/{submodule_name}.json")
            instrument_c(src_file, tmp_dir)
        else:
            raise NotImplementedError

        subprocess.check_call(
            [
                instrumentors["rust"],
                "-f",
                rs_file,
                "-o",
                output_dir,
                "--capture-stdout",
                "--wrapper-structs",
                "--arbitrary-precision",
                "--ground-truth",
                tmp_dir + "/libground_truth.so",
                "--multi-examples",
                str(n_counter_examples),
            ]
        )
        subprocess.check_call(["mv", tmp_dir + "/libground_truth.so", output_dir])


def verify_llm(
    # fuzz_target: str,
    language,
    src_code,
    rust_code,
    #    result_path: Optional[str] = None
) -> Optional[Tuple[str, str]]:
    import anthropic
    import boto3
    import botocore
    from utils import claude_gen

    config = botocore.config.Config(
        read_timeout=900, connect_timeout=900, retries={"max_attempts": 0}
    )
    session = boto3.Session()
    bedrock = session.client("bedrock-runtime", config=config)

    code = f"\n\n{language.capitalize()} Code:\n\n {src_code} \n\n Rust Code:\n\n {rust_code}\n\n"
    instruction = f"Above, you are given a {language} program and a Rust program. Tell me if they return the exact same outputs for all possible inputs. If yes, just type \"YES\" with capital letters. However, if no, type \"NO\" with capital letters and give me a few test inputs for which two programs return different values. Test inputs should be in a the following form: {{}} 'args': ['arg1', 'arg2', 'arg3']"
    prompt = f"""{anthropic.HUMAN_PROMPT} {code + instruction} {anthropic.AI_PROMPT}"""
    answer = claude_gen(bedrock, prompt)


def verify(
    fuzz_target: str, submodule_name: str, result_path: Optional[str] = None
) -> Optional[Tuple[str, str]]:
    """
    Verify the fuzzing target

    Args:
        fuzz_target (str): Path to the fuzz target.
        submoduel_name (str): Name of the submodule.
        result_path (Optional[str]): Optional result path.

    Returns:
        None: If fails to generate oracle.
        Tuple[str, str]: A pair of positive/negative examples.
    """
    fuzz_target: str = get_path(os.path.abspath(fuzz_target))
    logging.info(f"Start verifying {submodule_name}")

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = fuzz_target
    env["RUSTFLAGS"] = f"-L {fuzz_target}"

    main_entry = (
        subprocess.run(
            "cargo bolero list --manifest-path "
            f"{fuzz_target}/Cargo.toml | jq '.test' | head -n 1 | xargs echo ",
            shell=True,
            capture_output=True,
            env=env,
        )
        .stdout.decode("utf-8")
        .strip()
    )

    if len(main_entry) == 0:
        return None

    VERIFICATION_TIMEOUT = 420
    RETRY_LIMIT = 0
    # exponential backoff...
    init_max_len = 32768
    retry_cnt = 0
    timeout = VERIFICATION_TIMEOUT
    while True:
        verification = subprocess.Popen(
            f"cargo bolero test --manifest-path {fuzz_target}/Cargo.toml "
            f"--features fuzzing {main_entry} --target-dir {fuzz_target}/target/__fuzz__ "
            "--sanitizer NONE "
            f'--engine-args="-rss_limit_mb=8096 -max_len={init_max_len}" ',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        try:
            _, errs = verification.communicate(timeout=timeout)
            crash_report = errs.decode("utf-8").strip()
            break
        except subprocess.TimeoutExpired:
            verification.kill()
            if retry_cnt == RETRY_LIMIT:
                return None
            logging.info("Verification timeout. Increasing max input size.")
            retry_cnt += 1
            init_max_len *= 4
            timeout *= 2
            continue

    positive_examples: Optional[str] = None
    counter_examples: Optional[str] = None
    for line in crash_report.splitlines():
        if line.startswith("positive examples: "):
            positive_examples = line[len("positive examples: ") :]
        elif line.startswith("counter examples: "):
            counter_examples = line[len("counter examples: ") :]

    if not positive_examples or not counter_examples:
        return None

    # report, _ = compute_coverage_by_libfuzzer_corpus(fuzz_target)

    if result_path:
        with open(result_path + "/verify.log", "w") as f:
            f.write(crash_report)
        with open(result_path + "/counter_examples.json", "w") as f:
            f.write(counter_examples)
        with open(result_path + "/positive_examples.json", "w") as f:
            f.write(positive_examples)

    return positive_examples, counter_examples


rust_sysroot = (
    subprocess.run("rustc --print sysroot", capture_output=True, shell=True, check=True)
    .stdout.decode("utf-8")
    .strip()
)
llvm_cov = (
    subprocess.run(
        f'find {rust_sysroot} -name "llvm-cov" | head -n 1',
        capture_output=True,
        shell=True,
        check=True,
    )
    .stdout.decode("utf-8")
    .strip()
)
llvm_profdata = (
    subprocess.run(
        f'find {rust_sysroot} -name "llvm-profdata" | head -n 1',
        capture_output=True,
        shell=True,
        check=True,
    )
    .stdout.decode("utf-8")
    .strip()
)


def parse_llvm_cov_show(target_dir: str, show: str) -> List[Tuple[str, str]]:
    """
    Parse llvm-cov show results.

    Args:
        target_dir (str): Path to target directory. This is used to locate relevent parts.
        show (str): Original show results.

    Returns:
        List[Tuple[str, str]]: A mapping from line numbers to exec_count and the program part.
    """

    # This is a hack.
    show = show.split(f"{target_dir}/src/lib.rs:\n")[1]
    parts = []
    start = False
    for line in show.splitlines():
        if not line.strip():
            continue
        if line.strip()[0].isdigit():
            if "mod communication {" in line:
                break
            if 'extern "C" {' in line:
                start = True
            if not start:
                continue
            _, exec_count, program_part = line.split("|", 2)
            parts.append((exec_count, program_part))

    return parts


def test_cases_cov_info(replay_dir: str, io_examples: str) -> List[int]:
    """
    Return coverage info for a set of I/O examples

    Args:
        replay_target (str): Path to the replay target.
        io_examples (str): A list of examples.

    Returns:
        List[int]: A mapping from line number to the number of examples that cover it
        List[str]: A list of processed lines. We need this since line numbers in original code and coverage report might not match.
    """
    io_examples = json.loads(io_examples)
    cov_mat = []
    processed_lines: List[str] = []
    for io_example in io_examples:
        _, show = compute_coverage(replay_dir, json.dumps([io_example]))

        def parse_exec_count(s: str) -> int:
            try:
                return int(s)
            except ValueError:
                return 0

        cov: List[int] = list(
            map(lambda line_info: parse_exec_count(line_info[0]), show)
        )
        cov_mat.append(cov)

        processed_lines = list(
            map(lambda line_info: line_info[1], show)
        )  # same for every loop iteration

    # transpose cov matrix: line -> io_example -> int
    cov_mat = [list(l) for l in zip(*cov_mat)]

    cov_data = [sum(1 for cnt in line_info if cnt > 0) for line_info in cov_mat]

    return cov_data, processed_lines


def compute_sbfl_scores(
    replay_dir: str,
    positive_examples: str,
    counter_examples: str,
    sbfl_technique: str = "ochiai",
):
    totalp = len(json.loads(positive_examples))
    totalf = len(json.loads(counter_examples))

    covp, processed_lines = test_cases_cov_info(replay_dir, positive_examples)
    covf, processed_lines = test_cases_cov_info(replay_dir, counter_examples)

    def ochiai(totalp, totalf, ep, ef):
        try:
            return (ef * ef) / ((totalp + totalf) * (ef + ep))
        except ZeroDivisionError:
            return 0

    def tarantula(totalp, totalf, ep, ef):
        np = totalp - ep
        nf = totalf - ef
        try:
            return (ef / ef + nf) / ((ef / ef + nf) + (ep / ep + np))
        except ZeroDivisionError:
            return 0

    if sbfl_technique == "ochiai":
        scores = [ochiai(totalp, totalf, ep, ef) for ep, ef in zip(covp, covf)]
    else:
        scores = [tarantula(totalp, totalf, ep, ef) for ep, ef in zip(covp, covf)]

    return scores, processed_lines


def group_examples_by_coverage(
    replay_dir: str, negative_examples: str, N_EXAMPLES: int, early_stop: bool = True
) -> Dict[List[int], Any]:
    negative_examples = json.loads(negative_examples)
    cov_to_ce = defaultdict(list)
    for example in negative_examples:
        l_cov = []
        _, ex_data = compute_coverage(replay_dir, str([example]))
        for ex_d in ex_data:
            try:
                ex_cnt = int(ex_d[0])
                if ex_cnt > 0:
                    l_cov.append(1)
                else:
                    l_cov.append(0)
            except:
                l_cov.append(0)
        cov_to_ce[str(l_cov)].append(example)
        if early_stop and len(cov_to_ce[str(l_cov)]) == N_EXAMPLES:
            return {str(l_cov): cov_to_ce[str(l_cov)]}

    return cov_to_ce


def group_inp_by_coverage(ces, lang, res_dir, submodule_name):
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = tmp_dir + "/workspace"
        try:
            instrument(
                lang, res_dir, submodule_name, workspace
            )  # creates workspace for computing coverages
        except subprocess.CalledProcessError:
            logging.info("Failed to instrument candidate.")
            return None
        cov_to_ce = defaultdict(list)
        for ce in ces:
            l_cov = []
            _, ex_data = compute_coverage(workspace, str([ce]))
            for ex_d in ex_data:
                try:
                    ex_cnt = int(ex_d[0])
                    if ex_cnt > 0:
                        l_cov.append(1)
                    else:
                        l_cov.append(0)
                except:
                    l_cov.append(0)
            cov_to_ce[str(l_cov)].append(ce)
        # except subprocess.CalledProcessError:
        #     logging.info("Failed to instrument candidate.")
        #     return None

    return cov_to_ce


def compute_coverage_by_libfuzzer_corpus(
    fuzz_target: str,
) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Compute coverage by corpus

    Args:
        fuzz_target (str): Path to the fuzz target.

    Returns:
        Tuple[str, List[Tuple[str, str]]]: A pair of report/show.
    """
    instrument_flags = (
        "-Zunstable-options -C instrument-coverage=except-unused-functions"
    )
    env = os.environ.copy()
    env["RUSTFLAGS"] = instrument_flags

    test_bin = (
        subprocess.run(
            f"cargo test --manifest-path {fuzz_target}/Cargo.toml "
            '--tests --no-run --message-format=json | jq -r "select(.profile.test == true) '
            '| .filenames[]" | grep -v dSYM -',
            capture_output=True,
            shell=True,
            check=True,
            env=env,
        )
        .stdout.decode("utf-8")
        .strip()
    )

    subprocess.run(
        f"cargo test --manifest-path {fuzz_target}/Cargo.toml",
        shell=True,
        capture_output=True,
        env=env,
    )

    subprocess.call(
        f"{llvm_profdata} merge -sparse {fuzz_target}/*.profraw -o {fuzz_target}/cov.profdata",
        shell=True,
    )

    report = (
        subprocess.run(
            f"{llvm_cov} report -instr-profile={fuzz_target}/cov.profdata {test_bin}",
            shell=True,
            capture_output=True,
        )
        .stdout.decode("utf-8")
        .strip()
    )
    show = (
        subprocess.run(
            f"{llvm_cov} show -instr-profile={fuzz_target}/cov.profdata {test_bin} "
            "--show-instantiations --show-line-counts-or-regions",
            shell=True,
            capture_output=True,
        )
        .stdout.decode("utf-8")
        .strip()
    )

    return report, parse_llvm_cov_show(fuzz_target, show)


def compute_coverage(
    replay_dir: str, io_examples: str
) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Compute coverage by I/O examples

    Args:
        fuzz_target (str): Path to the fuzz target.
        io_examples (str): A list of examples.

    Returns:
        Tuple[str, List[Tuple[str, str]]]: A pair of report/show.
    """
    instrument_flags = (
        "-Zunstable-options -C instrument-coverage=except-unused-functions"
    )
    env = os.environ.copy()
    env["RUSTFLAGS"] = instrument_flags

    # remove possible previous data
    subprocess.run(f"rm -f {replay_dir}/*.profraw", shell=True)
    subprocess.run(f"rm -f {replay_dir}/cov.profdata", shell=True)

    test_bin = (
        subprocess.run(
            f"cargo test --manifest-path {replay_dir}/Cargo.toml --features replay "
            '--tests --no-run --message-format=json | jq -r "select(.profile.test == true) '
            '| .filenames[]" | grep -v dSYM -',
            capture_output=True,
            shell=True,
            check=True,
            env=env,
        )
        .stdout.decode("utf-8")
        .strip()
    )

    subprocess.run(
        f"cargo test --manifest-path {replay_dir}/Cargo.toml --features replay",
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        input=io_examples.encode(),
        shell=True,
        env=env,
    )

    subprocess.call(
        f"{llvm_profdata} merge -sparse {replay_dir}/*.profraw -o {replay_dir}/cov.profdata",
        shell=True,
    )

    report = (
        subprocess.run(
            f"{llvm_cov} report -instr-profile={replay_dir}/cov.profdata {test_bin}",
            shell=True,
            capture_output=True,
        )
        .stdout.decode("utf-8")
        .strip()
    )
    show = (
        subprocess.run(
            f"{llvm_cov} show -instr-profile={replay_dir}/cov.profdata {test_bin} "
            "--show-instantiations --show-line-counts-or-regions",
            shell=True,
            capture_output=True,
        )
        .stdout.decode("utf-8")
        .strip()
    )

    return report, parse_llvm_cov_show(replay_dir, show)


def soft_verify(
    replay_target: str,
    submodule_name: str,
    positive_examples: str,
    counter_examples: str,
) -> Optional[Tuple[str, str]]:
    """
    Verify the replay target by a given set of I/O examples.

    Args:
        replay_target (str): Path to the replay target.
        submoduel_name (str): Name of the submodule.
        positive_examples (str): A set of positive examples.
        counter_examples (str):  A set of counter examples.

    Returns:
        None: If fails to generate oracle.
        Tuple[str, str]: A pair of positive/negative examples.
    """
    replay_target: str = get_path(os.path.abspath(replay_target))
    logging.info(f"Start soft-verifying {submodule_name}")

    pe_typck: list = json.loads(positive_examples)
    ce_typck: list = json.loads(counter_examples)

    io_examples = json.dumps(pe_typck + ce_typck)

    VERIFICATION_TIMEOUT = 300
    timeout = VERIFICATION_TIMEOUT
    crash_report: str
    verification = subprocess.Popen(
        f"cargo test --manifest-path {replay_target}/Cargo.toml --features replay -- --nocapture",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    try:
        _, errs = verification.communicate(input=io_examples.encode(), timeout=timeout)
        crash_report = errs.decode("utf-8").strip()
    except subprocess.TimeoutExpired:
        verification.kill()
        return None

    new_positive_examples: Optional[str] = None
    new_counter_examples: Optional[str] = None
    for line in crash_report.splitlines():
        if line.startswith("positive examples: "):
            new_positive_examples = line[len("positive examples: ") :]
        elif line.startswith("counter examples: "):
            new_counter_examples = line[len("counter examples: ") :]

    if not new_positive_examples or not new_counter_examples:
        return None

    if len(json.loads(io_examples)) != len(
        json.loads(new_counter_examples) + json.loads(new_positive_examples)
    ):
        raise RuntimeError("Mismatched I/O examples. How?")

    return new_positive_examples, new_counter_examples
