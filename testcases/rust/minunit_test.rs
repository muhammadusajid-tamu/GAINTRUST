// In Cargo.toml, add:
// [dependencies]
// lazy_static = "1.4"

#[cfg(test)]
mod tests {
    use std::sync::Mutex;

    // We'll simulate a global variable that our setup() and teardown() modify.
    lazy_static::lazy_static! {
        static ref GLOBAL_VALUE: Mutex<i32> = Mutex::new(0);
    }

    /// Setup function: set the global value to 42.
    fn setup() {
        let mut val = GLOBAL_VALUE.lock().unwrap();
        *val = 42;
    }

    /// Teardown function: reset the global value to 0.
    fn teardown() {
        let mut val = GLOBAL_VALUE.lock().unwrap();
        *val = 0;
    }

    #[test]
    fn test_addition() {
        // Equivalent to: mu_assert_int_eq(4, 2 + 2);
        assert_eq!(2 + 2, 4);
    }

    #[test]
    fn test_double_equality() {
        // Equivalent to: mu_assert_double_eq(expected, result);
        let a = 3.141592653589793;
        let b = 3.141592653589792; // Very close value.
        let epsilon = 1e-12;
        assert!((a - b).abs() < epsilon, "Expected {} to be approximately equal to {}", a, b);
    }

    #[test]
    fn test_string_equality() {
        // Equivalent to: mu_assert_string_eq("minunit", "minunit");
        assert_eq!("minunit", "minunit");
    }

    #[test]
    fn test_boolean_check() {
        // Equivalent to: mu_check((5 - 3) == 2);
        assert!((5 - 3) == 2);
    }

    #[test]
    fn test_setup_teardown() {
        // Simulate running a test with setup and teardown.
        setup();
        {
            let val = GLOBAL_VALUE.lock().unwrap();
            assert_eq!(*val, 42, "Setup did not set GLOBAL_VALUE to 42");
        }
        teardown();
        {
            let val = GLOBAL_VALUE.lock().unwrap();
            assert_eq!(*val, 0, "Teardown did not reset GLOBAL_VALUE to 0");
        }
    }
}
