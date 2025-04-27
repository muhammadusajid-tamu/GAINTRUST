#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "namegen.h"  /* Must declare:
                        - int namegen(char *dst, unsigned long len, const char *pattern, unsigned long *seed);
                        - Return codes: NAMEGEN_SUCCESS, NAMEGEN_TRUNCATED, NAMEGEN_INVALID, NAMEGEN_TOO_DEEP
                        - NAMEGEN_MAX_DEPTH */

#define BUF_SIZE 256

static void test_literal(void) {
    char output[BUF_SIZE];
    unsigned long seed = 12345;
    int ret = namegen(output, BUF_SIZE, "Hello", &seed);
    assert(ret == NAMEGEN_SUCCESS);
    assert(strcmp(output, "Hello") == 0);
    printf("test_literal passed: \"%s\"\n", output);
}

static void test_group_literal(void) {
    char output[BUF_SIZE];
    unsigned long seed = 54321;
    int ret = namegen(output, BUF_SIZE, "(Hello)", &seed);
    assert(ret == NAMEGEN_SUCCESS);
    assert(strcmp(output, "Hello") == 0);
    printf("test_group_literal passed: \"%s\"\n", output);
}

static void test_capitalization(void) {
    char output[BUF_SIZE];
    unsigned long seed = 11111;
    int ret = namegen(output, BUF_SIZE, "!(hello)", &seed);
    assert(ret == NAMEGEN_SUCCESS);
    assert(strcmp(output, "Hello") == 0);
    printf("test_capitalization passed: \"%s\"\n", output);
}

static void test_substitution_repeatability(void) {
    char output1[BUF_SIZE], output2[BUF_SIZE];
    unsigned long seed1 = 1, seed2 = 1;
    int ret1 = namegen(output1, BUF_SIZE, "s", &seed1);
    int ret2 = namegen(output2, BUF_SIZE, "s", &seed2);
    assert(ret1 == NAMEGEN_SUCCESS);
    assert(ret2 == NAMEGEN_SUCCESS);
    assert(strcmp(output1, output2) == 0);
    printf("test_substitution_repeatability passed: \"%s\"\n", output1);
}

static void test_choice(void) {
    char output[BUF_SIZE];
    unsigned long seed = 98765;
    int ret = namegen(output, BUF_SIZE, "(foo|bar)", &seed);
    assert(ret == NAMEGEN_SUCCESS);
    int isFoo = (strcmp(output, "foo") == 0);
    int isBar = (strcmp(output, "bar") == 0);
    assert(isFoo || isBar);
    printf("test_choice passed: \"%s\"\n", output);
}

static void test_invalid(void) {
    char output[BUF_SIZE];
    unsigned long seed = 123;
    int ret = namegen(output, BUF_SIZE, "(", &seed);
    assert(ret == NAMEGEN_INVALID);
    printf("test_invalid passed\n");
}

static void test_too_deep(void) {
    char pattern[512];
    int i;
    for (i = 0; i < NAMEGEN_MAX_DEPTH + 1; i++) {
        pattern[i] = '(';
    }
    pattern[i] = '\0';
    char output[BUF_SIZE];
    unsigned long seed = 555;
    int ret = namegen(output, BUF_SIZE, pattern, &seed);
    assert(ret == NAMEGEN_TOO_DEEP);
    printf("test_too_deep passed\n");
}

static void test_truncation(void) {
    char output[6]; // Very small buffer.
    unsigned long seed = 777;
    int ret = namegen(output, sizeof(output), "HelloWorld", &seed);
    assert(ret == NAMEGEN_TRUNCATED);
    printf("test_truncation passed: output = \"%s\"\n", output);
}



int main(void) {
    test_literal();
    test_group_literal();
    test_capitalization();
    test_substitution_repeatability();
    test_choice();
    test_invalid();
    test_too_deep();
    test_truncation();
    printf("All namegen tests passed.\n");
    return 0;
}
