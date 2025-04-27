#[cfg(test)]
mod tests {
    use super::*; // Assumes your module provides JsmnParser, JsmnToken, jsmn_parse, etc.
    use std::str;

    const NUM_TOKENS: usize = 128;

    // Helper to extract a token string from the original JSON.
    fn token_str(js: &str, token: &JsmnToken) -> &str {
        &js[token.start as usize .. token.end as usize]
    }

    #[test]
    fn test_empty_object() {
        let json = "{}";
        let mut parser = JsmnParser::new();
        let mut tokens = vec![JsmnToken::default(); NUM_TOKENS];
        let ret = jsmn_parse(&mut parser, json, &mut tokens);
        // Expect one token of type OBJECT.
        assert_eq!(ret, 1);
        assert_eq!(tokens[0].token_type, JsmnType::Object);
        assert_eq!(tokens[0].size, 0);
    }

    #[test]
    fn test_empty_array() {
        let json = "[]";
        let mut parser = JsmnParser::new();
        let mut tokens = vec![JsmnToken::default(); NUM_TOKENS];
        let ret = jsmn_parse(&mut parser, json, &mut tokens);
        assert_eq!(ret, 1);
        assert_eq!(tokens[0].token_type, JsmnType::Array);
        assert_eq!(tokens[0].size, 0);
    }

    #[test]
    fn test_simple_object() {
        let json = "{\"key\":\"value\"}";
        let mut parser = JsmnParser::new();
        let mut tokens = vec![JsmnToken::default(); NUM_TOKENS];
        let ret = jsmn_parse(&mut parser, json, &mut tokens);
        assert_eq!(ret, 3);
        // tokens[0] should be an object with one key.
        assert_eq!(tokens[0].token_type, JsmnType::Object);
        assert_eq!(tokens[0].size, 1);
        // tokens[1] is the key.
        assert_eq!(tokens[1].token_type, JsmnType::String);
        assert_eq!(token_str(json, &tokens[1]), "key");
        // tokens[2] is the value.
        assert_eq!(tokens[2].token_type, JsmnType::String);
        assert_eq!(token_str(json, &tokens[2]), "value");
    }

    #[test]
    fn test_array_of_numbers() {
        let json = "[1,2,3,4]";
        let mut parser = JsmnParser::new();
        let mut tokens = vec![JsmnToken::default(); NUM_TOKENS];
        let ret = jsmn_parse(&mut parser, json, &mut tokens);
        // tokens[0] should be an array of 4 elements.
        assert_eq!(ret, 5);
        assert_eq!(tokens[0].token_type, JsmnType::Array);
        assert_eq!(tokens[0].size, 4);
        // Each element should be a primitive.
        for i in 1..=4 {
            assert_eq!(tokens[i].token_type, JsmnType::Primitive);
            let s = token_str(json, &tokens[i]);
            assert!(!s.is_empty());
        }
    }

    #[test]
    fn test_nested() {
        let json = "{\"a\":{\"b\":[true,false,null]}}";
        let mut parser = JsmnParser::new();
        let mut tokens = vec![JsmnToken::default(); NUM_TOKENS];
        let ret = jsmn_parse(&mut parser, json, &mut tokens);
        // Expect 8 tokens.
        assert_eq!(ret, 8);
        assert_eq!(tokens[0].token_type, JsmnType::Object);
        assert_eq!(tokens[4].token_type, JsmnType::Array);
        assert_eq!(tokens[4].size, 3);
    }

    #[test]
    fn test_escaped_string() {
        let json = "\"Hello \\\"world\\\"!\"";
        let mut parser = JsmnParser::new();
        let mut tokens = vec![JsmnToken::default(); NUM_TOKENS];
        let ret = jsmn_parse(&mut parser, json, &mut tokens);
        assert_eq!(ret, 1);
        assert_eq!(tokens[0].token_type, JsmnType::String);
        // Note: the parser does not unescape, so the token text remains as in the JSON literal.
        let s = token_str(json, &tokens[0]);
        // The raw token should be: Hello \"world\"!
        assert_eq!(s, "Hello \\\"world\\\"!");
    }

    #[test]
    fn test_incomplete_json() {
        let json = "{\"a\": \"b\""; // Missing closing brace.
        let mut parser = JsmnParser::new();
        let mut tokens = vec![JsmnToken::default(); NUM_TOKENS];
        let ret = jsmn_parse(&mut parser, json, &mut tokens);
        assert_eq!(ret, JsmnError::Part as i32);
    }

    #[test]
    fn test_insufficient_tokens() {
        let json = "{\"a\":\"b\",\"c\":\"d\"}";
        let mut parser = JsmnParser::new();
        // Provide a very small token array.
        let mut tokens = vec![JsmnToken::default(); 3];
        let ret = jsmn_parse(&mut parser, json, &mut tokens);
        assert_eq!(ret, JsmnError::NOMEM as i32);
    }
}
