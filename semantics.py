from dataclasses import dataclass
from typing import Any, Optional, List, Tuple, Union
import anthropic
import logging
import json
import random
import tempfile
import functools
from overrides import override
from itertools import starmap
from subprocess import CalledProcessError
from enum import Enum
import llms
from llms import Prompt, QueryEngine

from utils import (
    compile_and_record_query,
    parse_error_coarse,
    tag,
    make_prompt,
    make_instruction,
    tag,
)
from settings import Options
import oracle


class ConversationFeedback(Enum):
    NEGATIVE = (-1,)
    NEUTRAL = (0,)
    POSITIVE = (1,)
    NO_FEEDBACK = (2,)


def feedback_description(reward: ConversationFeedback) -> str:
    if reward == ConversationFeedback.POSITIVE:
        return "Progress has been made with more testcases passed."
    elif (
        reward == ConversationFeedback.NEUTRAL
        or reward == ConversationFeedback.NEGATIVE
    ):
        return "You did not make any progress."
    elif reward == ConversationFeedback.NO_FEEDBACK:
        return ""
    else:
        raise ValueError(f"Expect reward, found {reward}.")


class Enhancement:
    def __init__(self, replay_dir: str, positive_examples: str, negative_examples: str):
        # TODO remove this constant?
        N_EXAMPLES = 10
        cov_to_ce = oracle.group_examples_by_coverage(
            replay_dir, negative_examples, N_EXAMPLES
        )
        _, ce_group = random.choice(list(cov_to_ce.items()))
        if len(ce_group) > N_EXAMPLES:
            ce_group = random.sample(ce_group, N_EXAMPLES)
        else:
            ce_group = ce_group

        self.ce_group = ce_group

    def enhancement(
        self, context: str, textual_examples: str, query_engine: QueryEngine
    ) -> str:
        return ""


class LLMExplain(Enhancement):
    def __init__(self, replay_dir: str, positive_examples: str, negative_examples: str):
        super().__init__(replay_dir, positive_examples, negative_examples)

    @override
    def enhancement(
        self, context: str, textual_examples: str, query_engine: QueryEngine
    ) -> str:
        logging.info("Enhancing prompt with LLM-Based root cause explanations.")

        explain_prompt = Prompt(
            context=context,
            instruction="Tell me the root cause of the issue and how to fix it in the Rust code.",
            extra_information=(
                "A set of input/output example(s) contained in <testcases> tag is given below.\n"
                + tag(textual_examples, "testcases")
            ),
        )
        answer = query_engine.query(explain_prompt)

        enhancement = (
            "\nBelow is an explanation and one possible way to solve the issue. Consider taking this information into account when fixing the problem.\n\n"
            + answer
        )

        return enhancement


@functools.total_ordering
class Candidate:
    def __init__(
        self,
        rust_code: str,
        positive_examples: str,
        negative_examples: str,
        extra: Union[None, Enhancement, Tuple[str, List[Tuple[str, str]]]],
    ) -> None:
        self.rust_code = rust_code
        self.positive_examples = positive_examples
        self.negative_examples = negative_examples
        ne = json.loads(self.negative_examples)
        pe = json.loads(self.positive_examples)
        self.score = len(pe) / (len(pe) + len(ne))
        self.extra = extra

    def hint(self, n_examples: int) -> str:
        n_positives = int(n_examples / 2)
        n_negatives = n_examples - n_positives
        logging.info(
            f"Hinted with {n_positives} positive examples and {n_negatives} negative examples"
        )
        positive_examples = json.loads(self.positive_examples)
        negative_examples = json.loads(self.negative_examples)
        if len(positive_examples) > n_positives:
            positive_examples = random.sample(positive_examples, n_positives)
        if len(negative_examples) > n_negatives:
            negative_examples = random.sample(negative_examples, n_negatives)
        examples = list(
            starmap(
                lambda idx, example: f"Example {idx}:\n" + textual_example(example),
                enumerate(positive_examples + negative_examples),
            )
        )

        preamble = "Take the following input/output examples contained in <testcases> tag into consideration:\n"

        hint = preamble + tag("\n".join(examples), "testcases")

        return hint

    def prompt(
        self,
        query_engine: QueryEngine,
        src_code: str,
        src_lang: str,
        n_examples: int,
        history: List[Tuple[str, str]] = [],
    ) -> Prompt:
        if self.ok:
            assert not self.extra
            raise RuntimeError("Ok candidate should not have this.")
        
        if n_examples == 0:
            assert len(history) == 0, "CAPR requires counter examples"

        # Counter examples enhancement
        if len(self.extra.ce_group) > n_examples:
            ce_group = random.sample(self.extra.ce_group, n_examples)
        else:
            ce_group = self.extra.ce_group
        textual_examples = list_examples(ce_group)

        if len(history) > 0:
            return Prompt(
                context="That is incorrect on the following inputs:\n" + tag(textual_examples, "testcases"),
                instruction="Make changes in the given code to obtain expected outputs for given test inputs.",
                constraints=[
                    "Use only safe Rust.",
                    "Don't use raw pointers.",
                    "Use box pointer whenever possible. Box pointers are preferable to other alternatives.",
                    "Try not to use Traits if possible. I would not like to have Traits in resulting Rust code.",
                    "Try not to use custom Generics if possible.",
                ],
                history=history
            )

        context = (
            f"\n\nYou are given a {src_lang} code contained in the following <code> tag\n"
            + tag(src_code, "code")
            + "\n"
            + "You are also given a plausible Rust translation contained in <code> tag that does not provide expected outputs for certain inputs. "
            + tag(self.rust_code, "code")
            + "\n"
        )

        extra_information: str
        if n_examples > 0:
            enhancement = self.extra.enhancement(context, textual_examples, query_engine)
            extra_information = (
                "A set of input/output example(s) contained in <testcases> tag is given below.\n"
                + tag(textual_examples, "testcases")
                + "\n"
                + enhancement
            )
        else:
            extra_information = ""

        prompt = Prompt(
            context=context,
            instruction="Make changes in the given code to obtain expected outputs for given test inputs.",
            constraints=[
                "Use only safe Rust.",
                "Don't use raw pointers.",
                "Use box pointer whenever possible. Box pointers are preferable to other alternatives.",
                "Try not to use Traits if possible. I would not like to have Traits in resulting Rust code.",
                "Try not to use custom Generics if possible.",
            ],
            extra_information=extra_information,
        )

        return prompt

    @property
    def ok(self) -> bool:
        return self.score == 1

    def __eq__(self, other):
        if not isinstance(other, Candidate):
            raise NotImplementedError
        return self.score == other.score

    def __lt__(self, other):
        if not isinstance(other, Candidate):
            raise NotImplementedError
        return self.score < other.score


class CandidateFactory:
    def __init__(
        self,
        src_code: str,
        src_code_json: str,
        language: str,
        submodule_name: str,
        sem_fix: str,
    ) -> None:
        self.src_code = src_code
        self.src_code_json = src_code_json
        self.language = language
        self.submodule_name = submodule_name
        if sem_fix == "base":
            Extra = Enhancement
        elif sem_fix == "llm-explain":
            Extra = LLMExplain
        else:
            raise NotImplementedError
        self.Extra = Extra

    @property
    def preamble(self) -> str:
        ret = (
            f"\n\nYou are given a {self.language} code contained in the following <code> tag\n"
            + tag(self.src_code, "code")
            + "\n"
            "You are also given a plausible Rust translation contained in <code> tag that does not provide expected outputs for certain inputs. "
            "A set of example(s) contained in <testcases> tag is given after the code.\n"
        )
        return ret

    def debug_candidate(self, candidate: Candidate) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
            src_dir = tmp_dir
            with open(
                src_dir + f"/{self.submodule_name}.{self.language}",
                "w",
            ) as f:
                f.write(self.src_code)
            with open(
                src_dir + f"/{self.submodule_name}.json",
                "w",
            ) as f:
                f.write(self.src_code_json)
            with open(src_dir + f"/{self.submodule_name}.rs", "w") as f:
                f.write(candidate.rust_code)

            workspace = tmp_dir + "/replay"
            try:
                oracle.instrument(
                    self.language, src_dir, self.submodule_name, workspace
                )
            except:
                raise AssertionError("Instrumentation should succeed")
            validation_result = oracle.soft_verify(
                workspace,
                self.submodule_name,
                candidate.positive_examples,
                candidate.negative_examples,
            )
            # should produce result
            assert validation_result, "Soft verification should succeed"

            positive_examples, negative_examples = validation_result

            assert (
                positive_examples == candidate.positive_examples
            ), "Incorrect positive examples"
            assert (
                negative_examples == candidate.negative_examples
            ), "Incorrect negative examples"

    def construct_candidate(
        self,
        rust_code: str,
        positive_examples: Optional[str] = None,
        negative_examples: Optional[str] = None,
    ) -> Optional[Candidate]:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
            src_dir = tmp_dir
            with open(
                src_dir + f"/{self.submodule_name}.{self.language}",
                "w",
            ) as f:
                f.write(self.src_code)
            with open(
                src_dir + f"/{self.submodule_name}.json",
                "w",
            ) as f:
                f.write(self.src_code_json)
            with open(src_dir + f"/{self.submodule_name}.rs", "w") as f:
                f.write(rust_code)

            workspace = tmp_dir + "/replay"
            try:
                oracle.instrument(
                    self.language, src_dir, self.submodule_name, workspace
                )
            except CalledProcessError:
                logging.info("Failed to instrument candidate.")
                return None

            requires_verification: bool = not positive_examples or not negative_examples
            validation_result: Optional[Tuple[str, str]]
            if requires_verification:
                # validation_result = oracle.verify_llm(self.language, self.src_code, rust_code, positive_examples)
                validation_result = oracle.verify(workspace, self.submodule_name)
            else:
                validation_result = oracle.soft_verify(
                    workspace, self.submodule_name, positive_examples, negative_examples
                )

            if not validation_result:
                logging.info("Failed to generate oracle.")
                return None

            positive_examples, negative_examples = validation_result

            candidate: Candidate
            try:
                candidate = Candidate(
                    rust_code, positive_examples, negative_examples, None
                )
            except json.decoder.JSONDecodeError:
                # occasionally our instrumentor cannot handle some json data
                return None
            if not candidate.ok:
                candidate.extra = self.Extra(
                    workspace, positive_examples, negative_examples
                )
            elif requires_verification:
                candidate.extra = oracle.compute_coverage_by_libfuzzer_corpus(workspace)
            return candidate


@dataclass(eq=False, repr=False)
class SemanticsStrategy:
    restart_idx: int
    factory: CandidateFactory
    options: Options
    query_engine: QueryEngine
    beam_width: int
    n_fix_peers: int
    budget: int

    def optimize(self, candidate: Candidate) -> Candidate:
        round_idx = 0
        history: List[Tuple[str, str]] = []
        while self.budget > 0:
            logging.info(f"Starting the {round_idx}-th round of fixing. Beam size = 1.")
            print(f"history length = {len(history)}")
            new_candidates = self.fix(candidate, history)
            new_candidates.sort(reverse=True)
            logging.info(
                f"{len(new_candidates)} many (potentially new) candidates expanded. Highest score = {new_candidates[0].score}"
            )

            assert len(new_candidates) > 0
            candidate = new_candidates[0]
            if candidate.ok:
                return candidate

            self.budget -= 1
            round_idx += 1

        return candidate

    def fix(self, candidate: Candidate, history: List[Tuple[str, str]]) -> List[Candidate]:
        prompt = candidate.prompt(
            self.query_engine,
            self.factory.src_code,
            self.factory.language,
            self.options.n_prompt_examples,
            history=history[:(self.options.conversation_window_size * 2)],
        )
        REP_THOLD = 5
        trial = 0
        new_rust_code: str
        while trial < REP_THOLD:
            new_rust_code = self.query_engine.generate_code(prompt)
            comp_out = compile_and_record_query(
                new_rust_code,
                self.src_dir,
                self.query_engine.stringify_prompt(prompt),
                log_id=f"{self.restart_idx}_{self.budget}_{0}",
            )
            comp_out = parse_error_coarse(
                comp_out.stderr
            )  # parse_error_timepass(, work_dir.split("/")[-1])
            if not len(comp_out[0]):
                break
            logging.info("Fixed code does not compile. Giving it another try.")
            trial += 1

        if len(comp_out[0]):
            # TODO
            logging.info("Could not find a fix that compiles. Giving up.")
            return [candidate]

        new_candidate = self.factory.construct_candidate(
            new_rust_code, candidate.positive_examples, candidate.negative_examples
        )

        if not new_candidate or (self.options.pruning and new_candidate <= candidate):
            logging.info("Found candidate of bad quality. Giving up.")
            return [candidate]
        
        if self.options.conversation:
            history.append((llms.USER, str(prompt)))
            history.append((llms.ASSISTANT, new_rust_code))

        return [new_candidate]

    @property
    def src_dir(self) -> str:
        return f"{self.options.work_dir}/wspace"


def list_examples(negative_examples: List[Any]) -> str:
    examples_list = ""
    for ce_idx, s_ce in enumerate(negative_examples):
        if s_ce["actual"] == "ExecutionFailure":
            # act_out = "Execution Failure"
            act_out = "Runtime crash"
        else:
            act_out = s_ce["actual"]["ExecutionSuccess"]
            act_out = simplify_data(json.loads(act_out))

        if s_ce["expected"] == "ExecutionFailure":
            # exp_out = "Execution Failure"
            exp_out = "Input is invalid, crash gracefully"
        else:
            exp_out = s_ce["expected"]["ExecutionSuccess"]
            exp_out = simplify_data(json.loads(exp_out))

        arguments = "Arguments:\n"
        for arg_idx, arg in enumerate(s_ce["args"]):
            arg = json.loads(arg)
            arg = simplify_data(arg)
            arguments = arguments + f"  Argument {arg_idx}: {arg}\n"

        examples_list = (
            examples_list + f"\n Example {ce_idx} \n {arguments} Expected Output: "
            f"{exp_out} \n Actual Output: {act_out}\n"
        )

    return examples_list


def simplify_data(json_data):
    MAX_ARRAY_LENGTH = 5
    if isinstance(json_data, dict):
        return {key: simplify_data(value) for key, value in json_data.items()}
    elif isinstance(json_data, list):
        if len(json_data) > MAX_ARRAY_LENGTH:
            n_removed = len(json_data) - MAX_ARRAY_LENGTH
            return [simplify_data(value) for value in json_data[:MAX_ARRAY_LENGTH]] + [
                f"... and {n_removed} other elements"
            ]
        else:
            return [simplify_data(value) for value in json_data]

    return json_data


# fault_preamble = (
#     "\n\nYou are given a Rust code contained in <code> tag that does not provide expected outputs for certain inputs. "
#     "A set of example(s) contained in <testcases> tag is given after the code.\n"
# )

instruction_preamble = "Please make necessary changes in the given code to obtain expected outputs for given inputs. Here are some constraints contained in <list> tags that you should care"
instruction_constraints = [
    "Give me the whole fixed code back, dont add explanation, comment or anything else.",
    "Use only safe Rust.",
    "Don't use raw pointers.",
    "Use box pointer whenever possible. Box pointers are preferable to other alternatives.",
    "Try not to use Traits if possible. I would not like to have Traits in resulting Rust code.",
    "Try not to use custom Generics if possible.",
]

fix_instruction = make_instruction(instruction_preamble, instruction_constraints)


def query_fix(
    rust_code: str,
    examples_list: str,
    enhancement: str,
    preamble: str,
    # preamble: str = fault_preamble,
    instruction: str = fix_instruction,
) -> str:
    prompt = make_prompt(preamble, rust_code, examples_list, enhancement, instruction)

    return prompt


def textual_example(example: Any) -> str:
    output: str
    try:
        if example["expected"] == "ExecutionFailure":
            # output = "Execution Failure"
            output = "Input is invalid, crash gracefully"
        else:
            output = example["expected"]["ExecutionSuccess"]
            output = simplify_data(json.loads(output))
    except KeyError:
        if example["actual"] == "ExecutionFailure":
            # output = "Execution Failure"
            output = "Input is invalid, crash gracefully"
        else:
            output = example["actual"]["ExecutionSuccess"]
            output = simplify_data(json.loads(output))

    arguments = " Arguments:\n"
    for arg_idx, arg in enumerate(example["args"]):
        arg = json.loads(arg)
        arg = simplify_data(arg)
        arguments = arguments + f"  Argument {arg_idx}: {arg}\n"

    return f"{arguments} Expected Output: {output}\n"
