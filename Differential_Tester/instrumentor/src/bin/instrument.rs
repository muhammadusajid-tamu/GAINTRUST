use std::{
    fs::{self, File},
    io::Read,
};

use anyhow::Context;
use clap::Parser;
use instrumentor::InstrConfig;
use syn::{visit::Visit, visit_mut::VisitMut};

fn main() -> anyhow::Result<()> {
    let config = InstrConfig::parse();
    if !config.file.is_file() {
        anyhow::bail!("expect a rust file");
    }
    let mut file = File::open(&config.file).context("failed to open file")?;
    let mut src = String::new();
    file.read_to_string(&mut src)
        .context("unable to read file")?;
    let mut ast = syn::parse_file(&src).context("unable to parse file")?;
    let impls_code = prettyplease::unparse(&syn::parse2(instrumentor::impls::code(&ast, &config))?);
    instrumentor::syntax::lazy_static::Replace.visit_file_mut(&mut ast);
    let mut ast = instrumentor::mangle::mangle_associated_methods(ast);
    let mut function_symbols = instrumentor::syntax::FunctionSymbols::collect(&ast);
    instrumentor::syntax::MarkPure(&mut function_symbols).visit_file(&ast);
    let main_entry = (!config.modular)
        .then(|| instrumentor::main_entry::find_main_entry(&ast, &function_symbols));
    let declare_global_state = config.declare_global_state();
    config.instrument_calls(&mut ast, &function_symbols);
    instrumentor::syntax::DeriveSerde(&config).visit_file_mut(&mut ast);
    let extern_c_block = config.extern_c_block(&function_symbols, main_entry.as_deref());
    let counter_examples_replay =
        config.counter_examples_replay(&function_symbols, main_entry.as_deref());
    let harnesses = config.harnesses(&function_symbols, main_entry.as_deref());
    let harnesses = if let Some(counter_examples_replay) = counter_examples_replay {
        quote::quote!(
            #[cfg(feature = "replay")]
            #counter_examples_replay

            #[cfg(not(feature = "replay"))]
            #harnesses
        )
    } else {
        harnesses
    };
    let extern_wrappers = config.extern_wrappers(&function_symbols);
    let counter_examples_container = config.counter_examples_container();

    let communication = config.communication();

    let instrumented = quote::quote!(//! Instrumented version
    #![feature(min_specialization)]

    #[cfg(all(feature = "replay", feature = "fuzzing"))]
    std::compile_error!("feature \"replay\" and feature \"fuzzing\" cannot be enabled at the same time");

    use bolero::{TypeGenerator, ValueGenerator};
    use serde::{Deserialize, Serialize};
    use std::fmt::Write as _;
    use std::cell::RefCell;
    pub mod impls;
    use impls::*;

    #declare_global_state

    #[cfg(feature = "fuzzing")]
    #extern_c_block

    #ast

    #extern_wrappers

    #communication

    #[cfg(test)]
    mod test {
        use super::*;
        #counter_examples_container

        #harnesses
    }

    );
    let formatted = prettyplease::unparse(&syn::parse2(instrumented)?);

    if config.output.exists() {
        println!("{formatted}");
        anyhow::bail!("output path exists, instrumented program printed")
    }

    fs::create_dir(&config.output)?;
    let toml_file = config.output.join("Cargo.toml");
    fs::create_dir(config.output.join("src"))?;
    let target_file = config.output.join("src/lib.rs");
    let impls_file = config.output.join("src/impls.rs");

    fs::write(&toml_file, instrumentor::template::cargo_toml(&config))?;
    fs::write(&impls_file, impls_code)?;
    fs::write(&target_file, formatted)?;

    if config.check {
        use std::process::Command;
        Command::new("cargo")
            .arg("check")
            .arg("--tests")
            .arg("--manifest-path")
            .arg(&toml_file)
            .env("RUSTFLAGS", "-Awarnings")
            .status()?;
    }

    Ok(())
}
