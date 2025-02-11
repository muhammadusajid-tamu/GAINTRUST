use std::{fs, path::PathBuf};

use anyhow::Context;
use c_instrumentor::{
    cmake_lists, instrumented_cpp, instrumented_h,
    parser::{fn_sig, struct_def},
    template::{ARENA_H, FUSER_HPP, JSON_HPP, RUNTIME_C, RUNTIME_H},
    Input,
};
use clap::Parser;

#[derive(Parser)]
struct Cli {
    #[clap(long, short)]
    /// Input file path
    file: PathBuf,
    #[clap(long, short)]
    /// Output dir path
    output: PathBuf,
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    fs::create_dir(&cli.output)?;
    fs::create_dir(cli.output.join("include"))?;
    fs::write(cli.output.join("include/arena.h"), ARENA_H)?;
    fs::write(cli.output.join("include/fuser.hpp"), FUSER_HPP)?;
    fs::write(cli.output.join("include/json.hpp"), JSON_HPP)?;
    fs::write(cli.output.join("include/runtime.h"), RUNTIME_H)?;
    fs::write(cli.output.join("include/runtime.c"), RUNTIME_C)?;

    let mut c_data: Input = serde_json::from_str(&fs::read_to_string(&cli.file)?)?;
    // c_data
    //     .type_defs
    //     .is_empty()
    //     .then_some(())
    //     .context("type defs not handled")?;
    // remove static designators of fucntions
    c_data.expose_everything();
    let benchmark_name = cli.file.file_name().context("basename failed")?;
    fs::write(
        cli.output.join("CMakeLists.txt"),
        cmake_lists(benchmark_name)?,
    )?;

    let c_structs = c_data
        .structs
        .iter()
        .map(|item| {
            struct_def(&item[..])
                .map(|(_, parsed)| parsed)
                .ok()
                .context("failed to parse struct definitions")
        })
        .collect::<Result<Vec<_>, _>>()?;

    let c_fn_sigs = c_data
        .func_decls
        .iter()
        .map(|item| {
            fn_sig(&item[..])
                .map(|(_, parsed)| parsed)
                .ok()
                .context("failed to parse function signatures")
        })
        .collect::<Result<Vec<_>, _>>()?;

    fs::write(
        cli.output.join("instrumented.cpp"),
        instrumented_cpp(benchmark_name, &c_structs, &c_fn_sigs)?,
    )?;
    fs::write(
        cli.output.join("instrumented.h"),
        instrumented_h(&c_fn_sigs)?,
    )?;

    fs::write(
        cli.output.join(benchmark_name).with_extension("h"),
        c_data.create_header(),
    )?;
    fs::write(
        cli.output.join(benchmark_name).with_extension("c"),
        c_data.into_c(),
    )?;
    Ok(())
}
