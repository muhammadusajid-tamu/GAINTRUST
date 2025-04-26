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
from collections import defaultdict, Counter
from contextlib import contextmanager
from tenacity import retry, wait_random_exponential


#for maintainability
CLIPPY_LINT_CATEOGIRES = {
    "complexity": [
        "bind_instead_of_map",
        "bool_comparison",
        "borrow_deref_ref",
        "borrowed_box",
        "bytes_count_to_len",
        "char_lit_as_u8",
        "clone_on_copy",
        "crosspointer_transmute",
        "default_constructed_unit_structs",
        "deprecated_cfg_attr",
        "deref_addrof",
        "derivable_impls",
        "diverging_sub_expression",
        "double_comparisons",
        "double_parens",
        "duration_subsec",
        "excessive_nesting",
        "explicit_auto_deref",
        "explicit_counter_loop",
        "explicit_write",
        "extra_unused_lifetimes",
        "extra_unused_type_parameters",
        "filter_map_identity",
        "filter_next",
        "flat_map_identity",
        "get_last_with_len",
        "identity_op",
        "implied_bounds_in_impls",
        "inspect_for_each",
        "int_plus_one",
        "iter_count",
        "iter_kv_map",
        "let_with_type_underscore",
        "manual_abs_diff",
        "manual_c_str_literals",
        "manual_clamp",
        "manual_div_ceil",
        "manual_filter",
        "manual_filter_map",
        "manual_find",
        "manual_find_map",
        "manual_flatten",
        "manual_hash_one",
        "manual_inspect",
        "manual_main_separator_str",
        "manual_ok_err",
        "manual_option_as_slice",
        "manual_range_patterns",
        "manual_rem_euclid",
        "manual_slice_size_calculation",
        "manual_split_once",
        "manual_strip",
        "manual_swap",
        "manual_unwrap_or",
        "map_all_any_identity",
        "map_flatten",
        "map_identity",
        "match_as_ref",
        "match_single_binding",
        "needless_arbitrary_self_type",
        "needless_as_bytes",
        "needless_bool",
        "needless_bool_assign",
        "needless_borrowed_reference",
        "needless_if",
        "needless_lifetimes",
        "needless_match",
        "needless_option_as_deref",
        "needless_option_take",
        "needless_question_mark",
        "needless_splitn",
        "needless_update",
        "neg_cmp_op_on_partial_ord",
        "no_effect",
        "nonminimal_bool",
        "only_used_in_recursion",
        "option_as_ref_deref",
        "option_filter_map",
        "option_map_unit_fn",
        "or_then_unwrap",
        "partialeq_ne_impl",
        "precedence",
        "ptr_offset_with_cast",
        "range_zip_with_len",
        "redundant_as_str",
        "redundant_async_block",
        "redundant_at_rest_pattern",
        "redundant_closure_call",
        "redundant_guards",
        "redundant_slicing",
        "repeat_once",
        "reserve_after_initialization",
        "result_filter_map",
        "result_map_unit_fn",
        "search_is_some",
        "seek_from_current",
        "seek_to_start_instead_of_rewind",
        "short_circuit_statement",
        "single_element_loop",
        "skip_while_next",
        "string_from_utf8_as_bytes",
        "strlen_on_c_strings",
        "swap_with_temporary",
        "temporary_assignment",
        "too_many_arguments",
        "transmute_bytes_to_str",
        "transmute_float_to_int",
        "transmute_int_to_bool",
        "transmute_int_to_char",
        "transmute_int_to_float",
        "transmute_int_to_non_zero",
        "transmute_num_to_bytes",
        "transmute_ptr_to_ref",
        "transmutes_expressible_as_ptr_casts",
        "type_complexity",
        "unit_arg",
        "unnecessary_cast",
        "unnecessary_filter_map",
        "unnecessary_find_map",
        "unnecessary_first_then_check",
        "unnecessary_literal_unwrap",
        "unnecessary_map_on_constructor",
        "unnecessary_min_or_max",
        "unnecessary_operation",
        "unnecessary_sort_by",
        "unnecessary_unwrap",
        "unneeded_wildcard_pattern",
        "unused_format_specs",
        "useless_asref",
        "useless_conversion",
        "useless_format",
        "useless_nonzero_new_unchecked",
        "useless_transmute",
        "vec_box",
        "while_let_loop",
        "wildcard_in_or_patterns",
        "zero_divided_by_zero",
        "zero_prefixed_literal",
    ],
    "correctness": [
        "absurd_extreme_comparisons",
        "almost_swapped",
        "approx_constant",
        "assertions_on_constants",
        "absurd_extreme_comparisons",
        "almost_swapped",
        "approx_constant", 
        "async_yields_async", 
        "bad_bit_mask",
        "cast_slice_different_sizes",
        "char_indices_as_byte_indices",
        "deprecated_semver",
        "derive_ord_xor_partial_ord",
        "derived_hash_with_manual_eq",
        "eager_transmute",
        "enum_clike_unportable_variant",
        "eq_op",
        "erasing_op",
        "if_let_mutex",
        "ifs_same_cond",
        "impl_hash_borrow_with_str_and_bytes",
        "impossible_comparisons",
        "ineffective_bit_mask",
        "infinite_iter",
        "inherent_to_string_shadow_display",
        "inline_fn_without_body",
        "invalid_regex",
        "inverted_saturating_sub",
        "invisible_characters",
        "iter_next_loop",
        "iter_skip_zero",
        "iterator_step_by_zero",
        "let_underscore_lock",
        "lint_groups_priority",
        "match_str_case_mismatch",
        "mem_replace_with_uninit",
        "min_max",
        "mistyped_literal_suffixes",
        "modulo_one",
        "mut_from_ref",
        "never_loop",
        "non_octal_unix_permissions",
        "nonsensical_open_options",
        "not_unsafe_ptr_arg_deref",
        "option_env_unwrap",
        "out_of_bounds_indexing",
        "overly_complex_bool_expr",
        "panicking_overflow_checks",
        "panicking_unwrap",
        "possible_missing_comma",
        "read_line_without_trim",
        "recursive_format_impl",
        "redundant_comparisons",
        "reversed_empty_ranges",
        "self_assignment",
        "serde_api_misuse",
        "size_of_in_element_count",
        "suspicious_splitn",
        "transmute_null_to_fn",
        "transmuting_null",
        "uninit_assumed_init",
        "uninit_vec",
        "unit_cmp",
        "unit_hash",
        "unit_return_expecting_ord",
        "unsound_collection_transmute",
        "unused_io_amount",
        "useless_attribute",
        "vec_resize_to_zero",
        "while_immutable_condition",
        "wrong_transmute",
        "zst_offset"
    ],
    "perf": [
        "box_collection",
        "boxed_local",
        "cmp_owned",
        "collapsible_str_replace",
        "double_ended_iterator_last",
        "drain_collect",
        "expect_fun_call",
        "extend_with_drain",
        "format_in_format_args",
        "iter_overeager_cloned",
        "large_const_arrays",
        "large_enum_variant",
        "manual_contains",
        "manual_ignore_case_cmp",
        "manual_memcpy",
        "manual_retain",
        "manual_str_repeat",
        "manual_try_fold",
        "map_entry",
        "missing_const_for_thread_local",
        "missing_spin_loop",
        "readonly_write_lock",
        "redundant_allocation",
        "regex_creation_in_loops",
        "result_large_err",
        "sliced_string_as_bytes",
        "slow_vector_initialization",
        "to_string_in_format_args",
        "unbuffered_bytes",
        "unnecessary_to_owned",
        "useless_vec",
        "vec_init_then_push",
        "waker_clone_wake",
    ],
    "style": [
        "assertions_on_constants",
        "assign_op_pattern",
        "blocks_in_conditions",
        "bool_assert_comparison",
        "borrow_interior_mutable_const",
        "box_default",
        "builtin_type_shadow",
        "byte_char_slices",
        "bytes_nth",
        "chars_last_cmp",
        "chars_next_cmp",
        "cmp_null",
        "collapsible_else_if",
        "collapsible_if",
        "collapsible_match",
        "comparison_to_empty",
        "declare_interior_mutable_const",
        "default_instead_of_iter_empty",
        "disallowed_macros",
        "disallowed_methods",
        "disallowed_names",
        "disallowed_types",
        "doc_lazy_continuation",
        "doc_overindented_list_items",
        "double_must_use",
        "duplicate_underscore_argument",
        "enum_variant_names",
        "err_expect",
        "excessive_precision",
        "field_reassign_with_default",
        "filter_map_bool_then",
        "fn_to_numeric_cast",
        "fn_to_numeric_cast_with_truncation",
        "for_kv_map",
        "from_over_into",
        "from_str_radix_10",
        "get_first",
        "if_same_then_else",
        "implicit_saturating_add",
        "implicit_saturating_sub",
        "inconsistent_digit_grouping",
        "infallible_destructuring_match",
        "inherent_to_string",
        "init_numbered_fields",
        "into_iter_on_ref",
        "io_other_error",
        "is_digit_ascii_radix",
        "items_after_test_module",
        "iter_cloned_collect",
        "iter_next_slice",
        "iter_nth",
        "iter_nth_zero",
        "iter_skip_next",
        "just_underscores_and_digits",
        "legacy_numeric_constants",
        "len_without_is_empty",
        "len_zero",
        "let_and_return",
        "let_unit_value",
        "main_recursion",
        "manual_async_fn",
        "manual_bits",
        "manual_dangling_ptr",
        "manual_is_ascii_check",
        "manual_is_finite",
        "manual_is_infinite",
        "manual_map",
        "manual_next_back",
        "manual_non_exhaustive",
        "manual_ok_or",
        "manual_pattern_char_comparison",
        "manual_range_contains",
        "manual_repeat_n",
        "manual_rotate",
        "manual_saturating_arithmetic",
        "manual_slice_fill",
        "manual_while_let_some",
        "map_clone",
        "map_collect_result_unit",
        "match_like_matches_macro",
        "match_overlapping_arm",
        "match_ref_pats",
        "match_result_ok",
        "mem_replace_option_with_none",
        "mem_replace_option_with_some",
        "mem_replace_with_default",
        "missing_enforced_import_renames",
        "missing_safety_doc",
        "mixed_attributes_style",
        "mixed_case_hex_literals",
        "module_inception",
        "must_use_unit",
        "mut_mutex_lock",
        "needless_borrow",
        "needless_borrows_for_generic_args",
        "needless_doctest_main",
        "needless_else",
        "needless_late_init",
        "needless_parens_on_range_literals",
        "needless_pub_self",
        "needless_range_loop",
        "needless_return",
        "needless_return_with_question_mark",
        "neg_multiply",
        "new_ret_no_self",
        "new_without_default",
        "non_minimal_cfg",
        "obfuscated_if_else",
        "ok_expect",
        "op_ref",
        "option_map_or_none",
        "owned_cow",
        "partialeq_to_none",
        "print_literal",
        "print_with_newline",
        "println_empty_string",
        "ptr_arg",
        "ptr_eq",
        "question_mark",
        "redundant_closure",
        "redundant_field_names",
        "redundant_pattern",
        "redundant_pattern_matching",
        "redundant_static_lifetimes",
        "result_map_or_into_option",
        "result_unit_err",
        "same_item_push",
        "self_named_constructors",
        "should_implement_trait",
        "single_char_add_str",
        "single_component_path_imports",
        "single_match",
        "string_extend_chars",
        "tabs_in_doc_comments",
        "to_digit_is_some",
        "to_string_trait_impl",
        "toplevel_ref_arg",
        "trim_split_whitespace",
        "uninlined_format_args",
        "unnecessary_fallible_conversions",
        "unnecessary_fold",
        "unnecessary_lazy_evaluations",
        "unnecessary_map_or",
        "unnecessary_mut_passed",
        "unnecessary_owned_empty_strings",
        "unneeded_struct_pattern",
        "unsafe_removed_from_name",
        "unused_enumerate_index",
        "unused_unit",
        "unusual_byte_groupings",
        "unwrap_or_default",
        "upper_case_acronyms",
        "while_let_on_iterator",
        "write_literal",
        "write_with_newline",
        "writeln_empty_string",
        "wrong_self_convention",
        "zero_ptr",
    ],
}
LINT_CATEGORY_MAP = {
    lint: category
    for category, lints in CLIPPY_LINT_CATEOGIRES.items()
    for lint in lints
}

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

    # modelId = "anthropic.claude-v2:1"  # TODO compare anthropic.claude-v2 and anthropic.claude-v2:1 later
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
    if Path(f"{work_dir}").is_dir():
        with cd(f"{work_dir}"):
            print("DEBUG: Directory exists, cleaning")
            subprocess.run(f"cargo clean", capture_output=True, shell=True)
    else:
        print("DEBUG: Directory doesn't exist, initializing")
        # subprocess.run(f"cargo new {work_dir}", capture_output=True, shell=True)
        subprocess.run(f"cargo new --lib {work_dir}", capture_output=True, shell=True)
        os.makedirs(f"{work_dir}/logs", exist_ok=True)
        with open(
            f"{work_dir}/Cargo.toml", "a"
        ) as fw:  # add some dependencies by default
            fw.write('rand = "0.8.4"\n')
            fw.write('libc = "0.2"\n')
            fw.write('regex = "1.10.2"\n')  # c urlparser benchmark
            #fw.write('lazy_static = "1.4.0"\n')  # go ACH benchmark
            #fw.write('once_cell = "1.19.0"\n')  # go ACH benchmark
            #fw.write('\n')
            #fw.write('[source.crates-io]\n')
            #fw.write('replace-with = "vendored-sources"\n')
            #fw.write('\n')
            #fw.write('[source.vendored-sources]\n')
            #fw.write('directory = "vendor"\n')

    os.makedirs(f"{work_dir}/logs", exist_ok=True)
    with open(f"{work_dir}/logs/prog_{log_id}.ans", "w") as f:
        f.write(f"{prompt}\n\n==========\n\n{code}")
    with open(f"{work_dir}/logs/prog_{log_id}.rs", "w") as f:
        f.write(code)  # for logging purpose
    # with open(f"{work_dir}/src/main.rs", "w") as f:
    with open(f"{work_dir}/src/lib.rs", "w") as f:
        f.write(code)  # has to be written in main, this will be over-written with fixes

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

def extract_category(clippy_code):
    if clippy_code and clippy_code.startswith("clippy::"):
        parts = clippy_code.split("::")
        if len(parts) >= 2:
            return parts[1]
    return None

def clippy_linter_stats(code, work_dir):
    print("DEBUG: Starting linting")
    categories = ["style", "complexity", "correctness", "performance"]
 
    work_path = Path(work_dir).resolve()
    cargo_file = work_path / "Cargo.toml"
    lib_rs = work_path / "src" / "lib.rs"
    assert cargo_file.exists(), f"Missing Cargo.toml in {work_dir}"
    assert lib_rs.exists(), f"Missing src/lib.rs in {work_dir}"

    print(f"DEBUG: Using work_dir = {work_path}")

    with cd(work_path):
        print("DEBUG: Cleaning cargo project...")
        subprocess.run("cargo clean", capture_output=True, shell=True)

        print("DEBUG: Writing new code to src/lib.rs...")
        lib_rs.write_text(code)

        print("DEBUG: Running cargo clippy...")
        result = subprocess.run(
            "cargo clippy --message-format=json",
            shell=True,
            check=False,
            capture_output=True,
            text=True
        )
        print("DEBUG: Clippy exited with code:", result.returncode)

        output_lines = result.stdout.splitlines()
        if result.returncode != 0:
            print("DEBUG: Clippy failed, adding stderr")
            output_lines += result.stderr.splitlines()

        else:
            print("DEBUG: Clippy completed successfully")

        category_counts = Counter()
        print(category_counts)
        # Combine stdout and stderr for parsing
        # output_lines = result.stdout.splitlines() + result.stderr.splitlines()
        for line in output_lines:
            line = line.strip()
            if not line.startswith("{"):
                continue  # skip malformed or irrelevant lines
            try:
                msg = json.loads(line)
                if msg.get("reason") == "compiler-message":
                    message = msg.get("message")
                    if not isinstance(message, dict):
                        continue
                    code_info = message.get("code") or {}
                    lint_code = code_info.get("code", "")
                    if lint_code.startswith("clippy::"):
                        lint_name = extract_category(lint_code)
                        category = LINT_CATEGORY_MAP.get(lint_name)
                        if category in categories:
                            category_counts[category] += 1
            except Exception as e:
                print("Unhandled exception:", e)
                continue

        print("Final counts:", category_counts)
        return tuple(category_counts[cat] for cat in categories)


def postprocess(answer, work_dir, prompt="", log_id=0):
    answer_clean = clean_answer_mech(answer)
    # if "fn main" not in answer_clean:
    #     answer_clean += "\n\nfn main(){}\n"

    if Path(f"{work_dir}").is_dir():
        with cd(f"{work_dir}"):
            subprocess.run(f"cargo clean", capture_output=True, shell=True)
    else:
        # subprocess.run(f"cargo new {work_dir}", capture_output=True, shell=True)
        subprocess.run(f"cargo new --lib {work_dir}", capture_output=True, shell=True)
        os.makedirs(f"{work_dir}/logs", exist_ok=True)
        with open(
            f"{work_dir}/Cargo.toml", "a"
        ) as fw:  # add some dependencies by default
            fw.write('rand = "0.8.4"\n')
            fw.write('libc = "0.2"\n')
            fw.write('regex = "1.10.2"\n')  # c urlparser benchmark
            fw.write('lazy_static = "1.4.0"\n')  # go ACH benchmark
            fw.write('once_cell = "1.19.0"\n')  # go ACH benchmark

    os.makedirs(f"{work_dir}/logs", exist_ok=True)
    with open(f"{work_dir}/logs/prog_{log_id}.ans", "w") as f:
        f.write(f"{prompt}\n\n==========\n\n{answer}")
    with open(f"{work_dir}/logs/prog_{log_id}.rs", "w") as f:
        f.write(answer_clean)  # for logging purpose
    # with open(f"{work_dir}/src/main.rs", "w") as f:
    with open(f"{work_dir}/src/lib.rs", "w") as f:
        f.write(
            answer_clean
        )  # has to be written in main, this will be over-written with fixes

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

