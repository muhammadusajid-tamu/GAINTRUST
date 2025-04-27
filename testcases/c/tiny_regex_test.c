#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "re.h"  // This header should declare re_match, re_matchp, re_compile, re_print, etc.

// Helper: a macro to print the result of a test.
#define TEST_MSG(msg)  printf("%s passed.\n", msg)

// Test 1: Literal match
void test_literal_match() {
    int mlen = 0;
    // "hello" should match at offset 0 in "hello world" and match length 5.
    int ret = re_match("hello", "hello world", &mlen);
    assert(ret == 0);
    assert(mlen == 5);
    TEST_MSG("test_literal_match");
}

// Test 2: Literal no-match
void test_literal_no_match() {
    int mlen = 0;
    // "hello" is not found in "world"
    int ret = re_match("hello", "world", &mlen);
    assert(ret == -1);
    TEST_MSG("test_literal_no_match");
}

// Test 3: Beginning anchor
void test_anchor_begin_success() {
    int mlen = 0;
    // "^hello" must match only if string starts with hello.
    int ret = re_match("^hello", "hello world", &mlen);
    assert(ret == 0);
    assert(mlen == 5);
    TEST_MSG("test_anchor_begin_success");
}

void test_anchor_begin_failure() {
    int mlen = 0;
    // Should fail because "hello" is not at the beginning.
    int ret = re_match("^hello", "say hello", &mlen);
    assert(ret == -1);
    TEST_MSG("test_anchor_begin_failure");
}

// Test 4: End anchor
void test_anchor_end_success() {
    int mlen = 0;
    // "world$" should match if the string ends with "world"
    int ret = re_match("world$", "hello world", &mlen);
    // Since the pattern is not anchored at the beginning, the matcher
    // will return the offset of the first character where a match occurs.
    // Here "world" begins at offset 6.
    assert(ret == 6);
    assert(mlen == 5);
    TEST_MSG("test_anchor_end_success");
}

void test_anchor_end_failure() {
    int mlen = 0;
    // "world$" should not match "world hello"
    int ret = re_match("world$", "world hello", &mlen);
    assert(ret == -1);
    TEST_MSG("test_anchor_end_failure");
}

// Test 5: Dot (.) meta-character
void test_dot() {
    int mlen = 0;
    // "h.llo" should match "hello"
    int ret = re_match("h.llo", "hello", &mlen);
    assert(ret == 0);
    assert(mlen == 5);
    TEST_MSG("test_dot");
}

// Test 6: STAR quantifier
void test_star() {
    int mlen = 0;
    // "a*" should match at offset 0 in "aaa". Since '*' can match zero or more,
    // the greedy match here should match all consecutive 'a's.
    int ret = re_match("a*", "aaa", &mlen);
    assert(ret == 0);
    // Depending on implementation details, it should match the entire "aaa"
    // (i.e. mlen == 3) rather than a zero-length match.
    assert(mlen == 3);
    TEST_MSG("test_star");
}

// Test 7: PLUS quantifier
void test_plus() {
    int mlen = 0;
    // "a+" requires at least one 'a'. In "baaab", the first occurrence is at offset 1.
    int ret = re_match("a+", "baaab", &mlen);
    assert(ret == 1);
    assert(mlen == 3);
    TEST_MSG("test_plus");
}

// Test 8: QUESTION quantifier
void test_question() {
    int mlen = 0;
    // "a?" means zero or one 'a'. In a string without 'a', it may match a zero-length string.
    int ret = re_match("a?", "bbb", &mlen);
    // For non-anchored patterns, a zero-length match at offset 0 is acceptable.
    assert(ret == 0);
    // Our implementation may return matchlength 0.
    TEST_MSG("test_question");
}

// Test 9: Character class (simple)
void test_char_class() {
    int mlen = 0;
    // "[abc]+" should match a sequence of a, b, or c.
    // In "xabcx", it should match "abc" starting at offset 1.
    int ret = re_match("[abc]+", "xabcx", &mlen);
    assert(ret == 1);
    assert(mlen == 3);
    TEST_MSG("test_char_class");
}

// Test 10: Range in character class
void test_range() {
    int mlen = 0;
    // "[a-z]+" should match lowercase letters.
    // "HELLO" (all uppercase) should fail.
    int ret = re_match("[a-z]+", "HELLO", &mlen);
    assert(ret == -1);
    TEST_MSG("test_range");
}

// Test 11: Escaped digit (\d)
void test_escaped_digit() {
    int mlen = 0;
    // "\\d+" should match one or more digits.
    // In "abc123xyz", the digits "123" start at offset 3.
    int ret = re_match("\\d+", "abc123xyz", &mlen);
    assert(ret == 3);
    assert(mlen == 3);
    TEST_MSG("test_escaped_digit");
}

// Test 12: Escaped word (\w)
void test_escaped_word() {
    int mlen = 0;
    // "\\w+" should match alphanumeric plus underscore.
    // In "!!!", there are no word characters, so no match.
    int ret = re_match("\\w+", "!!!", &mlen);
    assert(ret == -1);
    TEST_MSG("test_escaped_word");
}

// Test 13: Escaped whitespace (\s)
void test_escaped_whitespace() {
    int mlen = 0;
    // "\\s+" should match one or more whitespace characters.
    // In "abc def", there is a space at offset 3.
    int ret = re_match("\\s+", "abc def", &mlen);
    assert(ret == 3);
    // The match should be the space (" ") so matchlength should be 1.
    assert(mlen == 1);
    TEST_MSG("test_escaped_whitespace");
}

// Test 14: Invalid pattern (unmatched '[')
void test_invalid_pattern() {
    // re_compile should return 0 for an invalid pattern.
    re_t pat = re_compile("[abc");
    assert(pat == 0);
    TEST_MSG("test_invalid_pattern");
}

int main(void) {
    test_literal_match();
    test_literal_no_match();
    test_anchor_begin_success();
    test_anchor_begin_failure();
    test_anchor_end_success();
    test_anchor_end_failure();
    test_dot();
    test_star();
    test_plus();
    test_question();
    test_char_class();
    test_range();
    test_escaped_digit();
    test_escaped_word();
    test_escaped_whitespace();
    test_invalid_pattern();
    printf("All mini regex tests passed.\n");
    return 0;
}
