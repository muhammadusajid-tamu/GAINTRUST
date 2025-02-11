pub mod parser;
pub mod template;

use std::path::Path;

use anyhow::Context;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct Input {
    #[serde(rename = "Includes")]
    pub includes: Vec<String>,
    #[serde(rename = "Defines", default)]
    pub defines: Vec<String>,
    #[serde(rename = "TypeDefs", default)]
    pub type_defs: Vec<String>,
    #[serde(rename = "Globals", default)]
    pub globals: Vec<String>,
    #[serde(rename = "Structs")]
    pub structs: Vec<String>,
    #[serde(rename = "Function Declarations")]
    pub func_decls: Vec<String>,
    #[serde(rename = "Function Implementations")]
    pub func_defs: Vec<String>,
    #[serde(rename = "Enums", default)]
    pub enums: Vec<String>,
}

impl Input {
    pub fn expose_everything(&mut self) {
        for func_decl in &mut self.func_decls {
            *func_decl = func_decl
                .trim_start_matches("static")
                .trim_start()
                .trim_start_matches("inline")
                .trim_start()
                .to_owned();
        }
        for func_def in &mut self.func_defs {
            *func_def = func_def
                .trim_start_matches("static")
                .trim_start()
                .trim_start_matches("inline")
                .trim_start()
                .to_owned();
        }
    }

    pub fn create_header(&self) -> String {
        self.includes.to_owned().join("\n")
            + "\n"
            + Self::INLINE_HACK
            + "\n"
            + &self.defines.to_owned().join("\n")
            + "\n"
            + &self.type_defs.to_owned().join("\n")
            + "\n"
            + &self.enums.to_owned().join("\n")
            + "\n"
            + &self
                .structs
                .iter()
                .map(|s| s.replace("const ", ""))
                .collect::<Vec<_>>()
                .join("\n")
            + "\n"
            + &self.func_decls.to_owned().join("\n")
    }

    const REDEFINE_ALLOC: &'static str = r#"#include <runtime.h>
#define malloc(x) context_alloc((x))
void ignore(void* _ptr) {}
#define free(x) ignore((x))
"#;

    const INLINE_HACK: &'static str = "#define inline";

    pub fn into_c(self) -> String {
        self.includes.join("\n")
            + "\n"
            + Self::REDEFINE_ALLOC
            + "\n"
            + Self::INLINE_HACK
            + "\n"
            + &self.defines.join("\n")
            + "\n"
            + &self.type_defs.join("\n")
            + "\n"
            + &self.globals.join("\n")
            + "\n"
            + &self.enums.to_owned().join("\n")
            + "\n"
            + &self.structs.join("\n")
            + "\n"
            + &self.func_decls.join("\n")
            + "\n"
            + &self.func_defs.join("\n")
            + "\n"
    }
}

#[derive(Serialize, Deserialize, Debug)]
pub struct CStruct {
    pub ident: String,
    pub fields: Vec<(String, String, Vec<String>)>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct CFnSig {
    pub ident: String,
    pub args: Vec<(String, Vec<String>)>,
    pub ret: String,
}

pub fn cmake_lists<P: AsRef<Path>>(filename: P) -> anyhow::Result<String> {
    Ok(format!(
        "cmake_minimum_required(VERSION 3.27.7)

project(ground_truth)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED True)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED True)

add_library(
    ground_truth SHARED instrumented.h instrumented.cpp
    {} {} include/runtime.c
)

include_directories(include)

FIND_PACKAGE(Boost)
IF (Boost_FOUND)
    INCLUDE_DIRECTORIES(${{Boost_INCLUDE_DIR}})
    ADD_DEFINITIONS( \"-DHAS_BOOST\" )
    target_link_libraries(ground_truth PRIVATE ${{CMAKE_THREAD_LIBS_INIT}} Boost::boost)
ENDIF()",
        filename
            .as_ref()
            .with_extension("c")
            .to_str()
            .context("cmakelists")?,
        filename
            .as_ref()
            .with_extension("h")
            .to_str()
            .context("cmakelists")?
    ))
}

pub fn instrumented_h(c_fn_sigs: &[CFnSig]) -> anyhow::Result<String> {
    Ok(c_fn_sigs
        .iter()
        .map(|c_fn_sig| extern_prototype(c_fn_sig))
        .collect::<anyhow::Result<Vec<_>>>()?
        .join("\n"))
}

pub fn instrumented_cpp<P: AsRef<Path>>(
    filename: P,
    c_structs: &[CStruct],
    c_fn_sigs: &[CFnSig],
) -> anyhow::Result<String> {
    Ok(format!(
        r#"#include <iostream>
#include <string.h>
#include "fuser.hpp"
#include "json.hpp"
extern "C" {{
    #include "runtime.h"
    #include "{}"
}}

char* string2cstr(std::string string, void* (*alloc)(size_t)) {{
    auto ptr = static_cast<char*>(alloc(string.length() + 1));
    strcpy(ptr, string.c_str());
    return ptr;
}}

{}

{}

template <>
struct fuser::serializer<char*>
{{
    static nlohmann::ordered_json serialize(char* const& val)
    {{
        if (val) {{
            return serializer<std::string>::serialize(val);
        }} else {{
            return nullptr;
        }}
    }}
}};

template <>
struct fuser::deserializer<char*>
{{
    static char* deserialize(nlohmann::ordered_json const& json)
    {{
        if (json.is_null())
            return nullptr;
        else 
            return string2cstr(deserializer<std::string>::deserialize(json), context_alloc);
    }}
}};

template <typename T>
struct fuser::serializer<T*>
{{
    static nlohmann::ordered_json serialize(T* const& val)
    {{
        if (val) {{
            return serializer<T>::serialize(*val);
        }} else {{
            return nullptr;
        }}
    }}
}};

template <typename T>
struct fuser::deserializer<T*>
{{
    static T* deserialize(nlohmann::ordered_json const& json)
    {{
        if (json.is_null())
            return nullptr;
        else {{
            auto obj = deserializer<T>::deserialize(json);
            auto ptr = static_cast<T*>(context_alloc(sizeof(T)));
            *ptr = obj;
            return ptr;
        }}
    }}
}};

template <typename T>
struct fuser::serializer<
    T,
    typename std::enable_if<
        std::is_enum<T>::value
    >::type
> 
{{
    static nlohmann::ordered_json serialize(T const& val)
    {{
        return fuser::serialize<std::uint32_t>(static_cast<int>(val));
    }}
}};

template <typename T>
struct fuser::deserializer<
    T,
    typename std::enable_if<
        std::is_enum<T>::value
    >::type
> 
{{
    static T deserialize(nlohmann::ordered_json const& json)
    {{
        return static_cast<T>(fuser::deserialize<std::uint32_t>(json));
    }}
}};

// template <>
// struct fuser::serializer<unsigned long> : numeric_serializer<unsigned long, std::uintmax_t> {{}};

// template <>
// struct fuser::deserializer<unsigned long> : numeric_deserializer<unsigned long, std::uintmax_t> {{}};

// template <>
// struct fuser::serializer<char> : numeric_serializer<std::int8_t, std::uintmax_t> {{}};

// template <>
// struct fuser::deserializer<char> : numeric_deserializer<std::int8_t, std::uintmax_t> {{}};
    "#,
        filename
            .as_ref()
            .with_extension("h")
            .to_str()
            .context("instrumented.cpp")?,
        c_structs
            .iter()
            .map(|c_struct| fuse_struct(c_struct))
            .collect::<Vec<_>>()
            .join("\n"),
        c_fn_sigs
            .iter()
            .map(|c_fn_sig| extern_wrapper(c_fn_sig))
            .collect::<anyhow::Result<Vec<_>>>()?
            .join("\n")
    ))
}

fn c_type_is_primitive(type_name: &str) -> bool {
    let type_name = type_name.trim_start_matches("const ");
    match type_name {
        "uint8_t" | "uint16_t" | "uint32_t" | "uint64_t" | "int8_t" | "int16_t" | "int32_t"
        | "int64_t" | "void" | "bool" | "int" | "float" | "double" | "long" | "long long"
        | "char" | "size_t" | "unsigned long" | "unsigned int" | "unsigned" => true,
        _ => false,
    }
}

fn map_c_type_to_extern_type(type_name: &str) -> &str {
    if c_type_is_primitive(type_name) {
        type_name
    } else {
        "char*"
    }
}

fn extern_prototype(c_fn_sig: &CFnSig) -> anyhow::Result<String> {
    use std::fmt::Write;
    let mut w = String::new();
    let output_ty = map_c_type_to_extern_type(&c_fn_sig.ret);
    write!(&mut w, "{output_ty} {}__C", &c_fn_sig.ident)?;
    let args = c_fn_sig.args.iter().map(|(ty, array_decls)| {
        let ty = map_c_type_to_extern_type(ty);
        if array_decls.is_empty() {
            format!("{ty}")
        } else {
            format!("char*")
        }
    });
    writeln!(&mut w, "({});", args.collect::<Vec<_>>().join(", "))?;

    Ok(w)
}

fn extern_wrapper(c_fn_sig: &CFnSig) -> anyhow::Result<String> {
    use std::fmt::Write;
    let mut w = String::new();

    // write signature
    write!(&mut w, r#"extern "C" "#)?;
    let output_ty = map_c_type_to_extern_type(&c_fn_sig.ret);
    write!(&mut w, "{output_ty} {}__C", &c_fn_sig.ident)?;
    let args = c_fn_sig
        .args
        .iter()
        .enumerate()
        .map(|(index, (ty, array_decls))| {
            let ty = map_c_type_to_extern_type(ty);
            if !array_decls.is_empty() {
                format!("char* extern_input{index}")
            } else {
                let array_decls = array_decls
                    .iter()
                    .map(|s| format!("[{s}]"))
                    .collect::<Vec<_>>()
                    .join("");
                format!("{ty} extern_input{index}{array_decls}")
            }
        });
    writeln!(&mut w, "({}) {{", args.collect::<Vec<_>>().join(", "))?;

    // // start try block
    // writeln!(&mut w, "try {{")?;

    // prepare input
    for (index, (ty, array_decls)) in c_fn_sig.args.iter().enumerate() {
        if array_decls.is_empty() {
            if c_type_is_primitive(ty) {
                writeln!(&mut w, "auto input{index} = extern_input{index};")?;
            } else {
                writeln!(&mut w, "auto input{index} = fuser::deserialize<{ty}>(nlohmann::ordered_json::parse(extern_input{index}));")?;
            }
        } else {
            let array_decls = array_decls
                .iter()
                .map(|s| format!("[{s}]"))
                .collect::<Vec<_>>()
                .join("");
            writeln!(&mut w, "{ty} input{index}{array_decls};")?;
            writeln!(&mut w, "fuser::array_deserialize<{ty}{array_decls}>(nlohmann::ordered_json::parse(extern_input{index}), input{index});")?;
        }
    }
    let inputs = (0..c_fn_sig.args.len())
        .map(|index| format!("input{index}"))
        .collect::<Vec<_>>()
        .join(", ");

    // run function
    if c_fn_sig.ret == "void" {
        writeln!(&mut w, "{}({inputs});", c_fn_sig.ident)?;
    } else {
        writeln!(&mut w, "auto output = {}({inputs});", c_fn_sig.ident)?;
        if !c_type_is_primitive(&c_fn_sig.ret) {
            writeln!(
                &mut w,
                "std::string output_repr = fuser::serialize(&output).dump();"
            )?;
            writeln!(
                &mut w,
                "auto extern_output = string2cstr(output_repr, malloc);"
            )?;
        } else {
            writeln!(&mut w, "auto extern_output = output;")?;
        }
    }
    // modify input
    for (index, (ty, array_decls)) in c_fn_sig.args.iter().enumerate() {
        if !array_decls.is_empty() {
            let array_decls = array_decls
                .iter()
                .map(|s| format!("[{s}]"))
                .collect::<Vec<_>>()
                .join("");
            writeln!(
                &mut w,
                "strcpy(extern_input{index}, fuser::array_serialize<{ty}{array_decls}>(input{index}).dump().c_str());"
            )?;
        } else if !c_type_is_primitive(ty) {
            writeln!(
                &mut w,
                "strcpy(extern_input{index}, fuser::serialize(&input{index}).dump().c_str());"
            )?;
        }
    }

    // reset arena
    writeln!(&mut w, "context_reset();")?;

    // return
    if c_fn_sig.ret == "void" {
        writeln!(&mut w, "return;")?;
    } else {
        writeln!(&mut w, "return extern_output;")?;
    }

    // // end try block
    // writeln!(&mut w, "}} catch (std::exception &e) {{")?;
    // writeln!(&mut w, "std::abort();")?;
    // writeln!(&mut w, "}}")?;

    writeln!(&mut w, "}}")?;

    Ok(w)
}

fn fuse_struct(c_struct: &CStruct) -> String {
    let field_names = c_struct
        .fields
        .iter()
        .map(|(name, _, _)| name.to_owned())
        .collect::<Vec<_>>()
        .join(", ");
    format!(
        "BOOST_FUSION_ADAPT_STRUCT({}, {})",
        &c_struct.ident, field_names
    )
}
