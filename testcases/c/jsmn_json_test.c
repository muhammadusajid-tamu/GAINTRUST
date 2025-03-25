#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "jsmn.h"  // Ensure this file is in your include path

#define NUM_TOKENS 128

// Helper function to extract a substring from a JSON string using token bounds.
void print_token(const char *js, const jsmntok_t *t) {
    int len = t->end - t->start;
    char *buf = malloc(len + 1);
    if (!buf) return;
    memcpy(buf, js + t->start, len);
    buf[len] = '\0';
    printf("Token: \"%s\"\n", buf);
    free(buf);
}

// Test 1: Parse an empty object: "{}"
void test_empty_object() {
    const char *json = "{}";
    jsmn_parser parser;
    jsmntok_t tokens[NUM_TOKENS];
    jsmn_init(&parser);
    int ret = jsmn_parse(&parser, json, strlen(json), tokens, NUM_TOKENS);
    // Expect 1 token: the object itself.
    assert(ret == 1);
    assert(tokens[0].type == JSMN_OBJECT);
    assert(tokens[0].size == 0);
    printf("test_empty_object passed.\n");
}

// Test 2: Parse an empty array: "[]"
void test_empty_array() {
    const char *json = "[]";
    jsmn_parser parser;
    jsmntok_t tokens[NUM_TOKENS];
    jsmn_init(&parser);
    int ret = jsmn_parse(&parser, json, strlen(json), tokens, NUM_TOKENS);
    // Expect 1 token: the array.
    assert(ret == 1);
    assert(tokens[0].type == JSMN_ARRAY);
    assert(tokens[0].size == 0);
    printf("test_empty_array passed.\n");
}

// Test 3: Parse a simple object: {"key":"value"}
void test_simple_object() {
    const char *json = "{\"key\":\"value\"}";
    jsmn_parser parser;
    jsmntok_t tokens[NUM_TOKENS];
    jsmn_init(&parser);
    int ret = jsmn_parse(&parser, json, strlen(json), tokens, NUM_TOKENS);
    // Expected tokens:
    //  0: Object
    //  1: Key (string)
    //  2: Value (string)
    assert(ret == 3);
    assert(tokens[0].type == JSMN_OBJECT);
    assert(tokens[0].size == 1);
    assert(tokens[1].type == JSMN_STRING);
    // Check key substring is "key"
    assert(tokens[1].start >= 0 && tokens[1].end - tokens[1].start == 3);
    char key[4];
    memcpy(key, json + tokens[1].start, 3);
    key[3] = '\0';
    assert(strcmp(key, "key") == 0);
    assert(tokens[2].type == JSMN_STRING);
    // Check value substring is "value"
    int len = tokens[2].end - tokens[2].start;
    char *value = malloc(len + 1);
    memcpy(value, json + tokens[2].start, len);
    value[len] = '\0';
    assert(strcmp(value, "value") == 0);
    free(value);
    printf("test_simple_object passed.\n");
}

// Test 4: Parse an array of primitives: [1,2,3,4]
void test_array_of_numbers() {
    const char *json = "[1,2,3,4]";
    jsmn_parser parser;
    jsmntok_t tokens[NUM_TOKENS];
    jsmn_init(&parser);
    int ret = jsmn_parse(&parser, json, strlen(json), tokens, NUM_TOKENS);
    // Expected:
    // 0: Array token (size == 4)
    // 1..4: Four primitives (numbers)
    assert(ret == 5);
    assert(tokens[0].type == JSMN_ARRAY);
    assert(tokens[0].size == 4);
    // Check each number's token boundaries.
    for (int i = 1; i <= 4; i++) {
        assert(tokens[i].type == JSMN_PRIMITIVE);
        int toklen = tokens[i].end - tokens[i].start;
        // Ensure the token string is non-empty.
        assert(toklen > 0);
    }
    printf("test_array_of_numbers passed.\n");
}

// Test 5: Parse nested JSON: {"a":{"b":[true,false,null]}}
void test_nested() {
    const char *json = "{\"a\":{\"b\":[true,false,null]}}";
    jsmn_parser parser;
    jsmntok_t tokens[NUM_TOKENS];
    jsmn_init(&parser);
    int ret = jsmn_parse(&parser, json, strlen(json), tokens, NUM_TOKENS);
    // Expected tokens:
    // 0: Object, size 1.
    // 1: Key "a"
    // 2: Object, size 1.
    // 3: Key "b"
    // 4: Array, size 3.
    // 5,6,7: Primitives true, false, null.
    assert(ret == 8);
    assert(tokens[0].type == JSMN_OBJECT);
    assert(tokens[0].size == 1);
    assert(tokens[2].type == JSMN_OBJECT);
    assert(tokens[2].size == 1);
    assert(tokens[4].type == JSMN_ARRAY);
    assert(tokens[4].size == 3);
    printf("test_nested passed.\n");
}

// Test 6: Parse a JSON string with escapes: "Hello \"world\"!"
void test_escaped_string() {
    const char *json = "\"Hello \\\"world\\\"!\"";
    jsmn_parser parser;
    jsmntok_t tokens[NUM_TOKENS];
    jsmn_init(&parser);
    int ret = jsmn_parse(&parser, json, strlen(json), tokens, NUM_TOKENS);
    // Expect one token: a string token
    assert(ret == 1);
    assert(tokens[0].type == JSMN_STRING);
    // The token should span the text without the quotes.
    int len = tokens[0].end - tokens[0].start;
    char *buf = malloc(len + 1);
    memcpy(buf, json + tokens[0].start, len);
    buf[len] = '\0';
    // Expected result: Hello \"world\"!  (the parser does not unescape, so the text remains as in the JSON)
    // For our test, we simply check the length.
    assert(len == 16);
    free(buf);
    printf("test_escaped_string passed.\n");
}

// Test 7: Incomplete JSON (error: JSMN_ERROR_PART)
void test_incomplete_json() {
    const char *json = "{\"a\": \"b\"";  // Missing closing brace.
    jsmn_parser parser;
    jsmntok_t tokens[NUM_TOKENS];
    jsmn_init(&parser);
    int ret = jsmn_parse(&parser, json, strlen(json), tokens, NUM_TOKENS);
    // Expect error code JSMN_ERROR_PART (-3)
    assert(ret == JSMN_ERROR_PART);
    printf("test_incomplete_json passed.\n");
}

// Test 8: Insufficient tokens (simulate by using a small token array)
void test_insufficient_tokens() {
    const char *json = "{\"a\":\"b\",\"c\":\"d\"}";
    jsmn_parser parser;
    // Provide only 3 tokens
    jsmntok_t tokens[3];
    jsmn_init(&parser);
    int ret = jsmn_parse(&parser, json, strlen(json), tokens, 3);
    // Expect error code for not enough tokens: JSMN_ERROR_NOMEM (-1)
    assert(ret == JSMN_ERROR_NOMEM);
    printf("test_insufficient_tokens passed.\n");
}

int main(void) {
    test_empty_object();
    test_empty_array();
    test_simple_object();
    test_array_of_numbers();
    test_nested();
    test_escaped_string();
    test_incomplete_json();
    test_insufficient_tokens();
    printf("All JSMN tests passed.\n");
    return 0;
}
