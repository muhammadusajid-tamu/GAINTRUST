// Assume these definitions in your Rust port:
#[derive(Debug, PartialEq)]
pub enum NamegenResult {
    Success,
    Truncated,
    Invalid,
    TooDeep,
}

pub const NAMEGEN_MAX_DEPTH: usize = 32;

// The namegen function signature:
pub fn namegen(dst: &mut [u8], pattern: &str, seed: &mut u64) -> NamegenResult {
    // Your implementation goes here...
    unimplemented!()
}

// Helper: Convert a null-terminated buffer to a &str.
fn buffer_to_str(buf: &[u8]) -> &str {
    let len = buf.iter().position(|&c| c == 0).unwrap_or(buf.len());
    std::str::from_utf8(&buf[..len]).unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_literal() {
        let mut buf = [0u8; 256];
        let mut seed = 12345u64;
        let res = namegen(&mut buf, "Hello", &mut seed);
        assert_eq!(res, NamegenResult::Success);
        assert_eq!(buffer_to_str(&buf), "Hello");
        println!("test_literal passed: output = \"{}\"", buffer_to_str(&buf));
    }

    #[test]
    fn test_group_literal() {
        let mut buf = [0u8; 256];
        let mut seed = 54321u64;
        let res = namegen(&mut buf, "(Hello)", &mut seed);
        assert_eq!(res, NamegenResult::Success);
        assert_eq!(buffer_to_str(&buf), "Hello");
        println!("test_group_literal passed: output = \"{}\"", buffer_to_str(&buf));
    }

    #[test]
    fn test_capitalization() {
        let mut buf = [0u8; 256];
        let mut seed = 11111u64;
        let res = namegen(&mut buf, "!(hello)", &mut seed);
        assert_eq!(res, NamegenResult::Success);
        assert_eq!(buffer_to_str(&buf), "Hello");
        println!("test_capitalization passed: output = \"{}\"", buffer_to_str(&buf));
    }

    #[test]
    fn test_substitution_repeatability() {
        let mut buf1 = [0u8; 256];
        let mut buf2 = [0u8; 256];
        let mut seed1 = 1u64;
        let mut seed2 = 1u64;
        let res1 = namegen(&mut buf1, "s", &mut seed1);
        let res2 = namegen(&mut buf2, "s", &mut seed2);
        assert_eq!(res1, NamegenResult::Success);
        assert_eq!(res2, NamegenResult::Success);
        let out1 = buffer_to_str(&buf1);
        let out2 = buffer_to_str(&buf2);
        assert_eq!(out1, out2);
        println!("test_substitution_repeatability passed: output = \"{}\"", out1);
    }

    #[test]
    fn test_choice() {
        let mut buf = [0u8; 256];
        let mut seed = 98765u64;
        let res = namegen(&mut buf, "(foo|bar)", &mut seed);
        assert_eq!(res, NamegenResult::Success);
        let out = buffer_to_str(&buf);
        assert!(out == "foo" || out == "bar");
        println!("test_choice passed: output = \"{}\"", out);
    }

    #[test]
    fn test_invalid() {
        let mut buf = [0u8; 256];
        let mut seed = 123u64;
        let res = namegen(&mut buf, "(", &mut seed);
        assert_eq!(res, NamegenResult::Invalid);
        println!("test_invalid passed");
    }

    #[test]
    fn test_too_deep() {
        let pattern: String = std::iter::repeat("(")
            .take(NAMEGEN_MAX_DEPTH + 1)
            .collect();
        let mut buf = [0u8; 256];
        let mut seed = 555u64;
        let res = namegen(&mut buf, &pattern, &mut seed);
        assert_eq!(res, NamegenResult::TooDeep);
        println!("test_too_deep passed");
    }

    #[test]
    fn test_truncation() {
        let mut buf = [0u8; 6];
        let mut seed = 777u64;
        let res = namegen(&mut buf, "HelloWorld", &mut seed);
        assert_eq!(res, NamegenResult::Truncated);
        println!("test_truncation passed: output = \"{}\"", buffer_to_str(&buf));
    }

    #[test]
    fn test_complex_pattern() {
        let mut buf = [0u8; 256];
        let mut seed = 24680u64;
        // Use updated pattern "!(c)ast (m)onster"
        let res = namegen(&mut buf, "!(c)ast (m)onster", &mut seed);
        assert_eq!(res, NamegenResult::Success);
        let out = buffer_to_str(&buf);
        // Expected output is "Cast monster"
        assert_eq!(out, "Cast monster");
        println!("test_complex_pattern passed: output = \"{}\"", out);
    }
}
