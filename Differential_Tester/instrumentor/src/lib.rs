use std::path::PathBuf;

use clap::Parser;

pub mod communication;
pub mod impls;
pub mod main_entry;
pub mod mangle;
pub mod syntax;
pub mod template;

#[derive(Parser)]
pub struct InstrConfig {
    #[clap(long, short)]
    /// Input file path
    pub file: PathBuf,
    #[clap(long, short)]
    /// Output dir path
    pub output: PathBuf,
    #[clap(long, short)]
    /// Enable modular test harnesses
    pub modular: bool,
    #[clap(long, short)]
    /// Cargo check the output dir
    pub check: bool,
    #[clap(long)]
    /// Record multiple counter examples when test fails
    pub multi_examples: Option<usize>,
    #[clap(long)]
    pub capture_stdout: bool,
    /// Optional path to the ground truth dylib. This is used
    /// to match extern symbols
    #[clap(long)]
    pub ground_truth: Option<PathBuf>,
    /// Support arbitrary precision when serde floating point numbers (WIP)
    #[clap(long)]
    pub arbitrary_precision: bool,
    /// Generate wrappers for structs to enable customized serde behaviors
    #[clap(long)]
    pub wrapper_structs: bool,
    #[clap(long, default_value_t = 300)]
    pub timeout: u64,
}

fn handled_macros(path: &str) -> bool {
    matches!(
        path,
        "println" | "format" | "print" | "panic" | "write" | "writeln"
    )
}
