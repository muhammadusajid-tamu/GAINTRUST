/*
   test_minunit.c

   Example tests using minunit_minunit.h (minunit) to verify that the framework’s
   assertion macros and suite runner work as expected.
*/

#include <stdio.h>
#include <string.h>
#include "minunit_minunit.h"  /* Ensure this header is in your include path */

/* --- Global variable for testing setup/teardown --- */
static int global_value = 0;

/* --- Setup and Teardown functions --- */
static void test_setup(void) {
    /* For example, initialize global_value */
    global_value = 42;
}

static void test_teardown(void) {
    /* Reset global_value */
    global_value = 0;
}

/* --- Tests --- */

/* Test integer addition using mu_assert_int_eq */
MU_TEST(test_addition) {
    mu_assert_int_eq(4, 2 + 2);
}

/* Test double equality using mu_assert_double_eq */
MU_TEST(test_double_equality) {
    double a = 3.141592653589793;
    double b = 3.141592653589792;  /* very close */
    mu_assert_double_eq(a, b);
}

/* Test string equality using mu_assert_string_eq */
MU_TEST(test_string_equality) {
    mu_assert_string_eq("minunit", "minunit");
}

/* Test simple boolean check using mu_check */
MU_TEST(test_boolean_check) {
    mu_check( (5 - 3) == 2 );
}

/* Test that setup properly initializes a global variable */
MU_TEST(test_setup_teardown) {
    /* Since setup was run, global_value should be 42 */
    mu_assert_int_eq(42, global_value);
}

/* --- Test Suite --- */
static void all_tests(void) {
    /* Configure suite to use setup/teardown functions */
    MU_SUITE_CONFIGURE(test_setup, test_teardown);

    /* Run tests */
    MU_RUN_TEST(test_setup_teardown);  /* uses setup: global_value == 42 */
    MU_RUN_TEST(test_addition);
    MU_RUN_TEST(test_double_equality);
    MU_RUN_TEST(test_string_equality);
    MU_RUN_TEST(test_boolean_check);
}

/* --- Main --- */
int main(void) {
    MU_RUN_SUITE(all_tests);
    MU_REPORT();
    return MU_EXIT_CODE;
}
