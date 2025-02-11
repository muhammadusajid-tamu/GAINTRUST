//! template `Cargo.toml`

use crate::InstrConfig;

pub fn cargo_toml(config: &InstrConfig) -> String {
    let arbitrary_precision = if config.arbitrary_precision {
        "\"arbitrary_precision\""
    } else {
        ""
    };
    format!(
        r#"[package]
name = "verification"
version = "0.1.0"
edition = "2021"

# See more keys and their definitions at https://doc.rust-lang.org/cargo/reference/manifest.html

[dependencies]
bolero = {{ version = "0.10.0", features = ["arbitrary"] }}
libc = "0.2.150"
serde = {{ version = "1.0.192", features = ["derive", "rc"] }}
serde_json = {{ version = "1.0.108", features = [{arbitrary_precision}] }}
serde_repr = "0.1"
typed-arena = "2.0.2"
rand = "0.8.5"
lazy_static = "1.4.0"
once_cell = "1.19.0"
crash-handler = "0.6"
cfg-if = "1.0"

[features]
fuzzing = []
replay = []
previous = ["replay"]

[profile.fuzz]
inherits = "dev"
opt-level = 3
incremental = false
codegen-units = 1"#
    )
}
