import os

# import boto3
import logging

# import botocore
import numpy as np

from dataclasses import dataclass
from argparse_dataclass import ArgumentParser
from typing import List, Tuple, Optional
import tempfile
import sys
import shutil

from fixer import Fixer
from llms import QueryEngineFactory
from transpiler import Transpiler
from settings import Options
import oracle
from semantics import Candidate, CandidateFactory, SemanticsStrategy
from configurator import Config
import csv

def record_cov_data(report: str, show: List[Tuple[str, str]], work_dir: str):
    with open(f"{work_dir}/cov_report.txt", "w") as f:
        f.write(report)

    with open(f"{work_dir}/cov_show.txt", "w") as f:
        for exec_count, line in show:
            print(exec_count + "|" + line, file=f)


def construct_factory(options: Options) -> CandidateFactory:
    src_code: str
    with open(
        f"{options.res_dir}/{options.submodule_name}.{options.language}",
        "r",
    ) as f:
        src_code = f.read()
    src_code_json: str
    with open(
        f"{options.res_dir}/{options.submodule_name}.json",
        "r",
    ) as f:
        src_code_json = f.read()

    factory = CandidateFactory(
        src_code,
        src_code_json,
        options.language,
        options.submodule_name,
        options.sem_fix,
    )

    return factory


def latest_rust_code(options: Options) -> str:
    rust_code: str
    with open(f"{options.res_dir}/{options.submodule_name}.rs", "r") as f:
        rust_code = f.read()
    return rust_code


def test():
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = tmp_dir + "/workspace"
        src_dir = "Differential_Tester/benchmarks/ach/moov_io_ach_Addenda05_EntryDetailSequenceNumberField"
        submodule_name = "moov_io_ach_Addenda05_EntryDetailSequenceNumberField"
        oracle.instrument("go", src_dir, submodule_name, workspace)

        positives, negatives = oracle.verify(workspace, submodule_name, workspace)

        new_positives, _ = oracle.soft_verify(
            workspace, submodule_name, positives, negatives
        )

        assert positives == new_positives


def initial_transpilation(
    transpiler: Transpiler, options: Options
) -> Optional[Tuple[Candidate, CandidateFactory]]:
    INIT_ATTEMPT_BUDGTE = 5
    for _ in range(INIT_ATTEMPT_BUDGTE):
        compiles = transpiler.transpile()
        if compiles:
            logging.info(
                "Found a compiling transpilation. Checking semantic equivalence..."
            )
            factory = construct_factory(options)
            rust_code = latest_rust_code(options)
            candidate = factory.construct_candidate(rust_code)

            if not candidate:
                continue

            return candidate, factory
        else:
            logging.info("Candidate does not compile. Retrying.")

    return None


def main():
    # test()
    parser = ArgumentParser(Options)
    options = parser.parse_args()

    #options = Config.from_json_file("config.json")
    # config = botocore.config.Config(
    #     read_timeout=900, connect_timeout=900, retries={"max_attempts": 0}
    # )
    # session = boto3.Session()
    # query_engine = session.client("bedrock-runtime", config=config)

    global_constraints = []
    if options.language == "c":
        global_constraints.append("Consider using functions like `wrapping_add` to simulate C semantics.")

    if options.language == "go" and options.benchmark_name != "ach":
        global_constraints.append("If possible, use free standing functions instead of associated methods/functions.")

    if options.benchmark_name == "triangolatte":
        global_constraints.append("Unless necessary, don't generate `new` method for structs.")

    if options.benchmark_name == "go-edlib":
        global_constraints.append("Note that `int` in Golang is platform dependent, which should be mapped to `isize` in Rust.")

    query_engine = QueryEngineFactory.create_engine(options.model, global_constraints)

    if os.path.exists(options.work_dir):
        # os.rmdir(options.work_dir)
        shutil.rmtree(options.work_dir)
    os.makedirs(options.work_dir)

    Config.to_json_file(options.work_dir + "config.json", options)

    crash_report = open(f"{options.work_dir}/crash_report.txt", "w")
    sys.stderr.write = crash_report.write

    # file to record first-time compile rate, compile rate, and testcase pass rate
    if not os.path.exists('measurements.csv'):
        with open('measurements.csv', 'w') as csvfile:
            fieldnames = ['initial_translation', 'initial_translation_attempts', "initital_translation_errors", "compiles", "compiles_attempts", "final_translation_errors"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    logging.basicConfig(
        filename="%s/transpilation.log" % options.work_dir,
        level=logging.INFO,
        filemode="w",
        format="%(name)s - %(levelname)s - %(message)s",
    )
    logging.info("%s transpilation has started." % options.benchmark_name)

    rng = np.random.default_rng(123)

    if options.comp_fix_m == "comp-no-fix":
        comp_fixer = None
    else:
        comp_fixer = Fixer(
            options.comp_fix_m, query_engine, options.comp_fix_attempt_budget
        )
    eq_fixer = None

    fallback = options.fallback_opt
    restart_budget = options.restart_budget
    fix_budget = options.fix_budget

    transpiler = Transpiler(
        "base",
        comp_fixer,
        eq_fixer,
        options.language,
        options.benchmark_name,
        options.submodule_name,
        query_engine,
        options.transpl_attempt_budget,
        options.work_dir,
        model_params={"temperature": options.initial_temperature},
    )



    # INITIAL ATTEMPT
    transpilation = initial_transpilation(transpiler, options)
    if not transpilation:
        logging.info("Failed to find compilable/checkable candidate. Return Code: 0.")
        return

    candidate, factory = transpilation
    if candidate.ok:
        record_cov_data(*candidate.extra, options.work_dir)
        logging.info(
            "Transpilation finished. Equivalent transpilation has been found at initial attempt. Return Code: 1."
        )
        return

    # FALLBACK
    num_oracle_oos = 0
    fixed_once = False
    logging.info(
        f"Transpilation is not equivalent: candidate score = {candidate.score}."
    )
    for restart_idx in range(restart_budget):
        # if options.hinted: transpiler.hint = candidate.hint(options.n_prompt_examples)
        if options.hinted and candidate:
            transpiler.hint = candidate.hint(options.n_prompt_examples)

        if fallback == "fix":
            logging.info("Now attempting LLM-based semantics fixing.")
            semantics_strategy = SemanticsStrategy(
                restart_idx,
                factory,
                options,
                query_engine,
                beam_width=options.beam_width,
                n_fix_peers=options.n_fix_peers,
                budget=fix_budget,
            )
            candidate = semantics_strategy.optimize(candidate)

            if candidate.ok:
                fixed_once = True
                logging.info("Current errors has been cleaned. Verifying again.")
                candidate = factory.construct_candidate(candidate.rust_code)
                assert candidate
                if candidate.ok:
                    record_cov_data(*candidate.extra, options.work_dir)
                    logging.info(
                        f"Equivalent transpilation has been found by {fallback} strategy. Return Code: 2"
                    )
                    return
                else:
                    pass  # TODO: will think about later. At the moment restart budget always set to 1 for fix.
        else:
            if fallback == "restart":
                pass
            elif fallback == "param-search":

                def mutate_temperature(cur_temp, rng):
                    mu, sigma = 0, 0.1
                    dev = rng.normal(mu, sigma)
                    new_temp = max(0, min(1, cur_temp + dev))

                    return new_temp

                temperature = transpiler.model_params["temperature"]
                new_temperature = mutate_temperature(temperature, rng)
                transpiler.model_params["temperature"] = new_temperature
                logging.info(f"Temperature is set to: {new_temperature}")
            elif fallback == "prompt-search":
                transpiler.prompt = "mutate"
            elif fallback == "simplify":
                transpiler.prompt = "decomp-iter"

            compiles = transpiler.transpile()
            if not compiles:
                continue
            logging.info(
                "Found a compiling transpilation. Checking semantic equivalence..."
            )
            # candidate, factory = check(options)
            rust_code = latest_rust_code(options)
            candidate = factory.construct_candidate(rust_code)
            if not candidate:
                num_oracle_oos += 1
            elif candidate.ok:
                record_cov_data(*candidate.extra, options.work_dir)
                logging.info(
                    f"Equivalent transpilation has been found by {fallback} strategy. Restart id: {restart_idx}. Return Code: 2"
                )
                return

    if fixed_once:
        logging.info(
            "Fallback process failed cleaning semantic errors. Return Code: 3"
        )  # special failure case
    elif num_oracle_oos > 5:
        logging.info(
            "Fallback process failed cleaning semantic errors. Return Code: 4"
        )  # Oracle OOS
    elif num_oracle_oos > 0:
        logging.info(
            "Fallback process failed cleaning semantic errors. Return Code: 5"
        )  # Oracle Partially OOS
    else:
        logging.info("Fallback process failed cleaning semantic errors. Return Code: 6")


if __name__ == "__main__":
    main()
