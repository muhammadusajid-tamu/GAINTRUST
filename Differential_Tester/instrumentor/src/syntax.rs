//! Purely syntactic instrumentation

// pub mod associated;

pub mod lazy_static;
pub mod match_symbol;

use std::collections::HashMap;

use quote::format_ident;
use syn::{parse_quote, visit::Visit, visit_mut::VisitMut, File};

use crate::handled_macros;
use crate::InstrConfig;

use self::match_symbol::symbol_list;

fn require_global_state(data: &SignatureData) -> bool {
    !data.pure
}

impl InstrConfig {
    pub fn declare_global_state(&self) -> proc_macro2::TokenStream {
        let fields = self.global_state_fields();
        let fields_create = self.global_state_fields_create();
        let fields_reset = self.global_state_fields_reset();
        quote::quote!(
            struct GlobalState {
                #fields
            }
            impl GlobalState {
                fn new() -> Self {
                    GlobalState {
                        #fields_create
                    }
                }

                fn reset(&mut self) {
                    #fields_reset
                }
            }
        )
    }

    fn global_state_fields(&self) -> proc_macro2::TokenStream {
        if self.capture_stdout {
            quote::quote!(captured_stdout: RefCell<String>, arena: typed_arena::Arena<u8>)
        } else {
            quote::quote!(arena: typed_arena::Arena<u8>)
        }
    }

    fn global_state_fields_create(&self) -> proc_macro2::TokenStream {
        if self.capture_stdout {
            quote::quote!(captured_stdout: RefCell::new(String::default()), arena: typed_arena::Arena::default())
        } else {
            quote::quote!(arena: typed_arena::Arena::default())
        }
    }

    fn global_state_fields_reset(&self) -> proc_macro2::TokenStream {
        if self.capture_stdout {
            quote::quote!(self.captured_stdout.borrow_mut().clear(); self.arena = typed_arena::Arena::default();)
        } else {
            quote::quote!(self.arena = typed_arena::Arena::default();)
        }
    }

    pub fn instrument_calls(
        &self,
        ast: &mut File,
        function_symbols: &HashMap<String, SignatureData>,
    ) {
        InstrumentCalls {
            config: self,
            function_symbols,
        }
        .visit_file_mut(ast);
    }

    pub fn counter_examples_container(&self) -> Option<proc_macro2::TokenStream> {
        self.multi_examples.map(|max_num_examples| {
            quote::quote!(
                use std::sync::Mutex;
                // type ExecutionResult = Option<String>;
                #[derive(PartialEq, Debug, Clone, serde::Serialize, serde::Deserialize)]
                enum ExecutionResult {
                    ExecutionSuccess(String),
                    ExecutionFailure,
                }
                use ExecutionResult::*;
                impl std::convert::From<Option<String>> for ExecutionResult {
                    fn from(value: Option<String>) -> Self {
                        match value {
                            Some(result) => ExecutionSuccess(result),
                            None => ExecutionFailure,
                        }
                    }
                }
                #[derive(PartialEq, Debug, serde::Serialize, serde::Deserialize)]
                struct CounterExample {
                    args: std::vec::Vec<String>,
                    actual: ExecutionResult,
                    expected: ExecutionResult,
                }
                #[derive(PartialEq, Debug, serde::Serialize, serde::Deserialize)]
                struct PositiveExample {
                    args: std::vec::Vec<String>,
                    actual: ExecutionResult,
                }
                static COUNTER_EXAMPLES: Mutex<std::vec::Vec<CounterExample>> = Mutex::new(vec![]);
                static POSITIVE_EXAMPLES: Mutex<std::vec::Vec<PositiveExample>> = Mutex::new(vec![]);
                const MAX_NUM_EXAMPLES: usize = #max_num_examples;
            )
        })
    }

    pub fn counter_examples_replay(
        &self,
        function_symbols: &HashMap<String, SignatureData>,
        main_entry: Option<&str>,
    ) -> Option<proc_macro2::TokenStream> {
        if !self.multi_examples.is_some() || !main_entry.is_some() {
            return None;
        }
        let main_entry = main_entry.unwrap();
        let data = function_symbols.get(main_entry).unwrap();
        let rust_symbol = quote::format_ident!("{main_entry}__Rust");
        let counstruct_args = data.inputs.iter().enumerate().map(|(index, ty)| {
            let ty = match ty {
                &TypeKind::Primitive(ty_str) => {
                    let ident = quote::format_ident!("{ty_str}");
                    quote::quote!(#ident)
                }
                // generate `Box` instead so that `TypeGenerator` generates
                TypeKind::RefMut(_, ty_str) => quote::quote!(Box<#ty_str>),
                TypeKind::Ref(_, ty_str) => quote::quote!(Box<#ty_str>),
                TypeKind::Complex(ty_str) => quote::quote!(#ty_str),
                TypeKind::OutofScope => unreachable!(),
            };
            let ident = quote::format_ident!("input{index}");
            quote::quote!(
                let mut #ident: #ty = serde_json::from_str(args.next().unwrap()).unwrap();
            )
        });
        let rust_args = data.inputs.iter().enumerate().map(|(index, kind)| {
            let ident = quote::format_ident!("input{index}");
            match kind {
                TypeKind::RefMut(..) => quote::quote!(&mut *#ident),
                TypeKind::Ref(..) => quote::quote!(&*#ident),
                _ => quote::quote!(#ident),
            }
        });
        let rust_args = if require_global_state(data) {
            let rust_args = std::iter::once(quote::quote!(&mut global_state)).chain(rust_args);
            quote::quote!(#( #rust_args ),*)
        } else {
            quote::quote!(#( #rust_args ),*)
        };
        let create_global_state = require_global_state(data).then(|| quote::quote!(let mut global_state = std::panic::AssertUnwindSafe(GlobalState::new());));
        let reset_global_state =
            require_global_state(data).then(|| quote::quote!(global_state.reset();));
        let unwrap_result = data.output.as_ref().and_then(|output_ty| {
            if let TypeKind::Complex(tokens) = output_ty {
                if let Ok(syn::TypePath { path, .. }) = syn::parse2(tokens.clone()) {
                    if let Some(segment) = path.segments.last() {
                        if segment.ident == "Result" {
                            return Some(quote::quote!(.unwrap()))
                        }
                    }
                }
            }
            None
        });
        Some(quote::quote!(
            #[test] fn replay() {
                #create_global_state
                use std::io::{stdin, Read};
                let mut json = String::new();
                stdin().read_to_string(&mut json);
                let io_examples: std::vec::Vec<serde_json::Value> = serde_json::from_str(&json).unwrap();
                let io_examples: std::vec::Vec<PositiveExample> = io_examples.into_iter()
                    .map(|value| {
                        serde_json::from_value::<CounterExample>(value.clone())
                            .map(|CounterExample { args, expected, ..}| PositiveExample { args, actual: expected })
                            .or(serde_json::from_value::<PositiveExample>(value))
                            .unwrap()
                    })
                    .collect();

                let mut counter_examples = vec![];
                let mut positive_examples = vec![];
                for io_example in io_examples {
                    let mut args = io_example.args.iter();
                    #( #counstruct_args )*
                    let execution_result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(||
                        #rust_symbol(#rust_args)#unwrap_result
                    )).ok().map(|result| serialize__Rust(&result));
                    #reset_global_state
                    let execution_result = ExecutionResult::from(execution_result);
                    let results_are_equal = match (&execution_result, &io_example.actual) {
                        (ExecutionFailure, ExecutionFailure) => true,
                        (ExecutionSuccess(result1), ExecutionSuccess(result2)) => {
                            structural_eq(
                                &serde_json::from_str::<serde_json::Value>(result1).unwrap(),
                                &serde_json::from_str::<serde_json::Value>(result2).unwrap(),
                            )
                        }
                        _ => false
                    };
                    if !results_are_equal {
                        counter_examples.push(CounterExample {
                            args: io_example.args,
                            actual: execution_result,
                            expected: io_example.actual,
                        });
                    } else {
                        positive_examples.push(io_example);
                    }
                }

                panic!(
                    "counter examples: {}\npositive examples: {}\n",
                    serde_json::to_string(&counter_examples).unwrap(),
                    serde_json::to_string(&positive_examples).unwrap(),
                );
            }
        ))
    }

    pub fn extern_c_block(
        &self,
        function_symbols: &HashMap<String, SignatureData>,
        main_entry: Option<&str>,
    ) -> proc_macro2::TokenStream {
        let symbol_list = self.ground_truth.as_deref().map(|path| symbol_list(path));
        extern_c_block(function_symbols, symbol_list, main_entry)
    }

    pub fn harnesses(
        &self,
        function_symbols: &HashMap<String, SignatureData>,
        main_entry: Option<&str>,
    ) -> proc_macro2::TokenStream {
        harnesses(
            function_symbols,
            self.multi_examples.is_some(),
            self.timeout,
            ComparisonKind::Structural,
            main_entry,
        )
    }

    /// Generate wrapper functions for non-pure ones
    pub fn extern_wrappers(
        &self,
        function_symbols: &HashMap<String, SignatureData>,
    ) -> Option<proc_macro2::TokenStream> {
        if !self.modular {
            return None;
        }

        let iter = function_symbols
            .iter()
            .filter(|(_, data)| {
                !data.is_out_of_scope()
                    && !data
                        .output
                        .as_ref()
                        .is_some_and(|output| output.is_mutable_ref())
            })
            .filter(|(_, data)| require_global_state(data))
            .map(|(symbol, data)| {
                let extern_fn = quote::format_ident!("{symbol}__C");
                let wrapper = quote::format_ident!("{symbol}__C__wrapper");
                // TODO handle all lifetimes
                let mut lifetime_generics: syn::Generics = parse_quote!(<>);
                if require_global_state(data) {
                    lifetime_generics.params.push(parse_quote!('state))
                }
                if data.is_elided() {
                    lifetime_generics.params.push(parse_quote!('elided))
                }
                let where_clause = (lifetime_generics.params.len() > 1).then(|| quote::quote!(where 'state: 'elided));
                let lifetime_generics =
                    (!lifetime_generics.params.is_empty()).then(|| lifetime_generics);
                let params = data.params();
                let arg_types = data.inputs.iter().map(|ty| match ty {
                    &TypeKind::Primitive(ty_str) => {
                        let ident = quote::format_ident!("{ty_str}");
                        quote::quote!(#ident)
                    }
                    TypeKind::RefMut(lifetime, ty_str) => quote::quote!(&#lifetime mut #ty_str),
                    TypeKind::Ref(lifetime, ty_str) => quote::quote!(&#lifetime #ty_str),
                    TypeKind::Complex(ty_str) => quote::quote!(#ty_str),
                    TypeKind::OutofScope => unreachable!(),
                });
                let input_signature = if require_global_state(data) {
                    let params = std::iter::once(quote::quote!(global_state)).chain(params);
                    let arg_types =
                        std::iter::once(quote::quote!(&'state GlobalState)).chain(arg_types);
                    quote::quote!(#( #params: #arg_types ),*)
                } else {
                    quote::quote!(#( #params: #arg_types ),*)
                };
                let output_ty = data.output.as_ref().map(|output| match output {
                    TypeKind::Primitive(ty_str) => {
                        let ident = quote::format_ident!("{ty_str}");
                        quote::quote!(-> #ident)
                    }
                    TypeKind::Ref(lifetime, ty_str) => quote::quote!(-> &#lifetime #ty_str),
                    TypeKind::Complex(ty_str) => quote::quote!(-> #ty_str),
                    TypeKind::OutofScope | TypeKind::RefMut(..) => unreachable!(),
                });
                let prepare_extern_args = data.prepare_extern_args();
                let extern_args = data.extern_args();
                let extern_args_cleanup = data.extern_args_cleanup();

                let set_args = data
                    .inputs
                    .iter()
                    .enumerate()
                    .filter(|(_, data)| data.is_mutable_ref())
                    .map(|(index, _)| {
                        let ident = quote::format_ident!("input{index}");
                        let extern_ident = quote::format_ident!("extern_input{index}");
                        quote::quote!(*#ident = deserialize__Rust(&*global_state, #extern_ident);)
                    });

                let produce_output = data.output.as_ref().map(|data| match data {
                    TypeKind::Primitive(_) => quote::quote!(let rust_output = extern_output;),
                    TypeKind::Complex(_) => {
                        quote::quote!(let rust_output = deserialize__Rust(&*global_state, extern_output);)
                    }
                    TypeKind::Ref(..) => unimplemented!(),
                    TypeKind::RefMut(..) => unreachable!(),
                    TypeKind::OutofScope => unreachable!(),
                });
                let extern_output_cleanup = data.extern_output_cleanup();
                let yield_output = data.output.as_ref().map(|_| quote::quote!(rust_output));

                quote::quote!(fn #wrapper #lifetime_generics(#input_signature) #output_ty #where_clause {
                    unsafe {
                        #( #prepare_extern_args )*
                        let extern_output = #extern_fn(#( #extern_args ),*);
                        #( #set_args )*
                        #( #extern_args_cleanup )*
                        #produce_output
                        #extern_output_cleanup
                        #yield_output
                    }
                })
            });

        Some(quote::quote!(#( #iter )*))
    }
}

pub struct DeriveSerde<'me>(pub &'me InstrConfig);

impl VisitMut for DeriveSerde<'_> {
    fn visit_item_enum_mut(&mut self, item_enum: &mut syn::ItemEnum) {
        let traits: Vec<syn::Path> = vec![
            parse_quote!(serde_repr::Serialize_repr),
            parse_quote!(serde_repr::Deserialize_repr),
            parse_quote!(TypeGenerator),
            parse_quote!(Debug),
            parse_quote!(Clone),
        ];

        let mut derived: Vec<String> = vec![];
        let mut repred = false;

        for attr in item_enum.attrs.iter_mut() {
            if attr.path().is_ident("derive") {
                let nested = attr
                    .parse_args_with(
                        syn::punctuated::Punctuated::<syn::Meta, syn::Token![,]>::parse_terminated,
                    )
                    .unwrap();
                for item in nested {
                    derived.push(quote::quote!(#item).to_string());
                }
            } else if attr.path().is_ident("repr") {
                repred = true;
            }
        }
        for trait_ in traits {
            let path = quote::quote!(#trait_).to_string();
            if !derived.iter().any(|derived| derived == &path) {
                item_enum.attrs.push(parse_quote!(#[derive(#trait_)]));
            }
        }
        if !repred {
            item_enum.attrs.push(parse_quote!(#[repr(u32)]));
        }
        syn::visit_mut::visit_item_enum_mut(self, item_enum)
    }

    fn visit_item_struct_mut(&mut self, item_struct: &mut syn::ItemStruct) {
        let traits: Vec<syn::Path> = vec![
            parse_quote!(Serialize),
            parse_quote!(Deserialize),
            parse_quote!(TypeGenerator),
            parse_quote!(Debug),
            parse_quote!(Clone),
        ];
        let mut derived: Vec<String> = vec![];
        let mut repred = false;

        for attr in item_struct.attrs.iter_mut() {
            if attr.path().is_ident("derive") {
                let nested = attr
                    .parse_args_with(
                        syn::punctuated::Punctuated::<syn::Meta, syn::Token![,]>::parse_terminated,
                    )
                    .unwrap();
                for item in nested {
                    derived.push(quote::quote!(#item).to_string());
                }
            } else if attr.path().is_ident("repr") {
                if self.0.wrapper_structs {
                    let nested = attr
                        .parse_args_with(
                            syn::punctuated::Punctuated::<syn::Meta, syn::Token![,]>::parse_terminated,
                        )
                        .unwrap();
                    assert_eq!(nested.len(), 1);
                    let item = &nested[0];
                    if &quote::quote!(#item).to_string() != "C" {
                        unimplemented!("Struct has repr other than \"C\", which is not supported");
                    }
                }
                repred = true;
            }
        }
        for trait_ in traits {
            let path = quote::quote!(#trait_).to_string();
            if !derived.iter().any(|derived| derived == &path) {
                item_struct.attrs.push(parse_quote!(#[derive(#trait_)]));
            }
        }
        if self.0.wrapper_structs {
            if !repred {
                item_struct.attrs.push(parse_quote!(#[repr(C)]));
            }
            let ident = &item_struct.ident;
            let wrapper_ident = &format!("{ident}Wrapper");
            item_struct
                .attrs
                .push(parse_quote!(#[serde(from = #wrapper_ident, into = #wrapper_ident)]));
        }
        syn::visit_mut::visit_item_struct_mut(self, item_struct)
    }

    fn visit_field_mut(&mut self, field: &mut syn::Field) {
        // if field type contains reference
        let field_ty = &field.ty;
        let field_ty_str = quote::quote!(#field_ty).to_string();
        if field_ty_str == "String" {
            field
                .attrs
                .push(parse_quote!(#[generator(string_generator())]))
        } else if field_ty_str == "Box<str>" {
            field
                .attrs
                .push(parse_quote!(#[generator(boxed_str_generator())]))
        } else if field_ty_str == "f32" {
            field
                .attrs
                .push(parse_quote!(#[generator(f32_generator())]))
        } else if field_ty_str == "f64" {
            field
                .attrs
                .push(parse_quote!(#[generator(f64_generator())]))
        }

        if let syn::Type::Reference(syn::TypeReference { mutability, .. }) = &field_ty {
            if mutability.is_some() {
                field
                    .attrs
                    .push(parse_quote!(#[generator(ref_mut_generator())]))
            } else {
                field
                    .attrs
                    .push(parse_quote!(#[generator(ref_generator())]))
            }
        }

        // if let syn::Type::Array(..) = &field_ty {
        //     field.attrs.push(parse_quote!(#[serde(with = "arrays")]))
        // }

        syn::visit_mut::visit_field_mut(self, field)
    }
}

#[derive(Clone, Debug)]
pub enum LifetimeInfo {
    Explicit(proc_macro2::TokenStream),
    Elided(proc_macro2::TokenStream),
}

impl quote::ToTokens for LifetimeInfo {
    fn to_tokens(&self, tokens: &mut proc_macro2::TokenStream) {
        match self {
            LifetimeInfo::Explicit(lifetime) => lifetime.to_tokens(tokens),
            LifetimeInfo::Elided(lifetime) => lifetime.to_tokens(tokens),
        }
    }
}

#[derive(Clone, Debug)]
pub enum TypeKind {
    /// Primitive types like `i32`
    Primitive(&'static str),
    /// `&mut T`
    RefMut(LifetimeInfo, proc_macro2::TokenStream),
    /// `&T`
    Ref(LifetimeInfo, proc_macro2::TokenStream),
    /// `Box<T>`, `T` where `T` is a struct, etc.
    Complex(proc_macro2::TokenStream),
    OutofScope,
}

impl TypeKind {
    fn is_primitive(&self) -> bool {
        match self {
            Self::Primitive(..) => true,
            _ => false,
        }
    }

    fn is_mutable_ref(&self) -> bool {
        match self {
            Self::RefMut(..) => true,
            _ => false,
        }
    }
}

pub trait CheckOutofScope<'a> {
    fn is_out_of_scope(&'a self) -> bool;
}

impl CheckOutofScope<'_> for TypeKind {
    fn is_out_of_scope(&self) -> bool {
        match self {
            Self::OutofScope => true,
            _ => false,
        }
    }
}

impl<'a, I: 'a> CheckOutofScope<'a> for I
where
    &'a I: IntoIterator<Item = &'a TypeKind>,
{
    fn is_out_of_scope(&'a self) -> bool {
        self.into_iter().any(|ty| ty.is_out_of_scope())
    }
}

impl CheckOutofScope<'_> for SignatureData {
    fn is_out_of_scope(&self) -> bool {
        self.inputs.is_out_of_scope() || self.output.is_out_of_scope()
    }
}

pub trait CheckisElided<'a> {
    fn is_elided(&'a self) -> bool;
}

impl CheckisElided<'_> for LifetimeInfo {
    fn is_elided(&self) -> bool {
        matches!(self, LifetimeInfo::Elided(..))
    }
}

impl CheckisElided<'_> for TypeKind {
    fn is_elided(&self) -> bool {
        match self {
            Self::Ref(lifetime, _) | Self::RefMut(lifetime, _) => lifetime.is_elided(),
            _ => false,
        }
    }
}

impl<'a, I: 'a> CheckisElided<'a> for I
where
    &'a I: IntoIterator<Item = &'a TypeKind>,
{
    fn is_elided(&'a self) -> bool {
        self.into_iter().any(|ty| ty.is_elided())
    }
}

impl CheckisElided<'_> for SignatureData {
    fn is_elided(&self) -> bool {
        self.inputs.is_elided() || self.output.is_elided()
    }
}

pub struct FunctionSymbols(HashMap<String, SignatureData>);

pub struct SignatureData {
    output: Option<TypeKind>,
    inputs: Vec<TypeKind>,
    pub pure: bool,
}

impl FunctionSymbols {
    pub fn collect(file: &File) -> HashMap<String, SignatureData> {
        let mut vis = Self(HashMap::new());
        vis.visit_file(file);
        vis.0
    }
}

/// Resolve elided lifetimes at the same time.
/// TODO remove `TypeKind` later
fn syn_type_to_type_kind(ty: &syn::Type) -> TypeKind {
    match ty {
        syn::Type::Array(_) => {
            let mut ty = ty.clone();
            ApplyLifetime(quote::quote!('elided)).visit_type_mut(&mut ty);
            TypeKind::Complex(quote::quote!(#ty))
        }
        syn::Type::BareFn(_) => TypeKind::OutofScope,
        syn::Type::Group(_) => TypeKind::OutofScope,
        syn::Type::ImplTrait(_) => TypeKind::OutofScope,
        syn::Type::Infer(_) => TypeKind::OutofScope,
        syn::Type::Macro(_) => TypeKind::OutofScope,
        syn::Type::Never(_) => TypeKind::OutofScope,
        syn::Type::Paren(_) => TypeKind::OutofScope,
        syn::Type::Path(type_path) => {
            let path = &type_path.path;
            let type_string = quote::quote!(#path).to_string();

            if type_string.ends_with("c_int") || type_string.ends_with("i32") {
                TypeKind::Primitive("i32")
            } else if type_string.ends_with("i64") {
                TypeKind::Primitive("i64")
            } else if type_string.ends_with("u32") {
                TypeKind::Primitive("u32")
            } else if type_string.ends_with("u64") {
                TypeKind::Primitive("u64")
            } else if type_string.ends_with("usize") {
                TypeKind::Primitive("usize")
            } else if type_string.ends_with("isize") {
                TypeKind::Primitive("isize")
            } else if type_string.ends_with("f32") {
                TypeKind::Primitive("f32")
            } else if type_string.ends_with("f64") {
                TypeKind::Primitive("f64")
            } else if type_string.ends_with("bool") {
                TypeKind::Primitive("bool")
            } else if type_string.ends_with("char") {
                TypeKind::Primitive("char")
            } else if type_string.ends_with("u8") {
                TypeKind::Primitive("u8")
            } else if type_string.ends_with("i8") || type_string.ends_with("c_char") {
                TypeKind::Primitive("i8")
            } else {
                let mut ty = ty.clone();
                ApplyLifetime(quote::quote!('elided)).visit_type_mut(&mut ty);
                TypeKind::Complex(quote::quote!(#ty))
            }
        }
        syn::Type::Ptr(_) => TypeKind::OutofScope,
        syn::Type::Reference(reference) => {
            let lifetime_info = match &reference.lifetime {
                Some(lifetime) => LifetimeInfo::Explicit(quote::quote!(#lifetime)),
                None => LifetimeInfo::Elided(quote::quote!('elided)),
            };
            let mut inner_ty = reference.elem.as_ref().clone();
            ApplyLifetime(quote::quote!('elided)).visit_type_mut(&mut inner_ty);
            match reference.mutability {
                Some(_) => TypeKind::RefMut(lifetime_info, quote::quote!(#inner_ty)),
                None => TypeKind::Ref(lifetime_info, quote::quote!(#inner_ty)),
            }
        }
        syn::Type::Slice(_) => TypeKind::OutofScope,
        syn::Type::TraitObject(_) => TypeKind::OutofScope,
        syn::Type::Tuple(_) => {
            let mut ty = ty.clone();
            ApplyLifetime(quote::quote!('elided)).visit_type_mut(&mut ty);
            TypeKind::Complex(quote::quote!(#ty))
        }
        syn::Type::Verbatim(_) => TypeKind::OutofScope,
        _ => unreachable!(),
    }
}

impl Visit<'_> for FunctionSymbols {
    fn visit_item_fn(&mut self, item_fn: &syn::ItemFn) {
        let fn_name = item_fn.sig.ident.to_string();
        if fn_name == "main" {
            return;
        }
        let output = match &item_fn.sig.output {
            syn::ReturnType::Default => None,
            syn::ReturnType::Type(_, ty) => Some(syn_type_to_type_kind(ty.as_ref())),
        };
        let inputs = item_fn.sig.inputs.iter().map(|arg| match arg {
            syn::FnArg::Typed(pat_type) => syn_type_to_type_kind(pat_type.ty.as_ref()),
            _ => panic!("free standing function item should not contain self type"),
        });
        self.0.insert(
            fn_name,
            SignatureData {
                output,
                inputs: inputs.collect(),
                pure: false,
            },
        );
    }
}

/// Mark which functions must be pure, and therefore is not threaded with
/// a `GlobalState`.
///
/// Currently, functions mentioned in a static item/main function are forced to be pure.
pub struct MarkPure<'me>(pub &'me mut HashMap<String, SignatureData>);
struct MarkPureInner<'me>(&'me mut HashMap<String, SignatureData>);
impl Visit<'_> for MarkPureInner<'_> {
    fn visit_expr_call(&mut self, expr_call: &'_ syn::ExprCall) {
        match &*expr_call.func {
            syn::Expr::Path(ref path) => {
                let path = &path.path;
                if let Some(symbol) = path.get_ident() {
                    let symbol = symbol.to_string();
                    if let Some(data) = self.0.get_mut(&symbol) {
                        data.pure = true;
                    }
                }
            }
            _ => {}
        }
        syn::visit::visit_expr_call(self, expr_call);
    }
}

impl Visit<'_> for MarkPure<'_> {
    fn visit_item_static(&mut self, item_static: &'_ syn::ItemStatic) {
        MarkPureInner(&mut *self.0).visit_expr(&item_static.expr);
    }

    fn visit_item_fn(&mut self, item_fn: &'_ syn::ItemFn) {
        if item_fn.sig.ident == "main" {
            MarkPureInner(&mut *self.0).visit_block(&item_fn.block);
        }
    }
}

fn extern_c_block(
    function_symbols: &HashMap<String, SignatureData>,
    symbol_list: Option<Vec<String>>,
    main_entry: Option<&str>,
) -> proc_macro2::TokenStream {
    let iter = function_symbols
        .iter()
        .filter(|(_, data)| !data.is_out_of_scope())
        .filter(|(name, _)| match main_entry {
            Some(main_entry) => &name[..] == main_entry,
            None => true,
        })
        .map(|(symbol, data)| {
            let link_name = symbol_list
                .as_ref()
                .map(|symbol_list| {
                    let symbol = format!("{symbol}__C");
                    symbol_list.iter().max_by_key(|&given_symbol| {
                        lcs::LcsTable::new(symbol.as_bytes(), given_symbol.as_bytes())
                            .longest_common_subsequence()
                            .len()
                    })
                })
                .flatten()
                .map(|name| quote::quote!(#[link_name = #name]));
            let symbol = quote::format_ident!("{}__C", symbol);
            let args = data.inputs.iter().map(|data| match data {
                &TypeKind::Primitive(type_str) => {
                    let type_id = quote::format_ident!("{type_str}");
                    quote::quote!(#type_id)
                }
                _ => quote::quote!(*mut i8),
            });
            match data.output {
                Some(TypeKind::Primitive(type_str)) => {
                    let type_id = quote::format_ident!("{type_str}");
                    quote::quote!(#link_name fn #symbol( #(_: #args),* ) -> #type_id;)
                }
                Some(_) => quote::quote!(#link_name fn #symbol( #(_: #args),* ) -> *mut i8;),
                None => quote::quote!(#link_name fn #symbol( #(_: #args),* );),
            }
        });

    quote::quote!(#[link(name = "ground_truth")]
    extern "C" {
        #( #iter )*
    })
}

fn harnesses(
    function_symbols: &HashMap<String, SignatureData>,
    multi_examples: bool,
    timeout: u64,
    comparison_kind: ComparisonKind,
    main_entry: Option<&str>,
) -> proc_macro2::TokenStream {
    let comparison_kind = match comparison_kind {
        ComparisonKind::Bultin => ComparisonKind::String,
        _ => comparison_kind,
    };
    let iter = function_symbols
        .iter()
        .filter(|(_, data)| !data.is_out_of_scope())
        .filter(|(name, _)| {
            match main_entry {
                Some(main_entry) => &name[..] == main_entry,
                None => true,
            }
        })
        .map(|(symbol, data)| {
            let fuzz = quote::format_ident!("fuzz_{symbol}");
            let rust_symbol = quote::format_ident!("{symbol}__Rust");
            let extern_symbol = quote::format_ident!("{symbol}__C");
            let create_global_state = require_global_state(data).then(|| quote::quote!(let mut global_state = std::panic::AssertUnwindSafe(GlobalState::new());));
            let reset_global_state = require_global_state(data).then(|| quote::quote!(global_state.reset();));
            let params = data.params();
            let arg_types = data.inputs.iter().map(|ty| match ty {
                &TypeKind::Primitive(ty_str) => {
                    let ident = quote::format_ident!("{ty_str}");
                    quote::quote!(#ident)
                }
                // generate `Box` instead so that `TypeGenerator` generates
                TypeKind::RefMut(_, ty_str) => quote::quote!(Box<#ty_str>),
                TypeKind::Ref(_, ty_str) => quote::quote!(Box<#ty_str>),
                TypeKind::Complex(ty_str) => quote::quote!(#ty_str),
                TypeKind::OutofScope => unreachable!(),
            });
            let input_filter = data.input_filter();
            let prepare_extern_args = data.prepare_extern_args();
            let rust_args = data.inputs.iter().enumerate().map(|(index, kind)| {
                let ident = quote::format_ident!("input{index}");
                match kind {
                    TypeKind::RefMut(..) => quote::quote!(&mut *#ident),
                    TypeKind::Ref(..) => quote::quote!(&*#ident),
                    _ => quote::quote!(#ident),
                }
            });
            let rust_args = if require_global_state(data) {
                let rust_args = std::iter::once(quote::quote!(&mut global_state))
                    .chain(rust_args);
                quote::quote!(#( #rust_args ),*)
            } else {
                quote::quote!(#( #rust_args ),*)
            };
            let unwrap_result = data.output.as_ref().and_then(|output_ty| {
                if let TypeKind::Complex(tokens) = output_ty {
                    if let Ok(syn::TypePath { path, .. }) = syn::parse2(tokens.clone()) {
                        if let Some(segment) = path.segments.last() {
                            if segment.ident == "Result" {
                                return Some(quote::quote!(.unwrap()))
                            }
                        }
                    }
                }
                None
            });
            let extern_args = data.extern_args();
            let compare_input = data.inputs
                .iter()
                .enumerate()
                .filter(|(_, data)| data.is_mutable_ref())
                .map(|(index, _)| {
                    let ident = quote::format_ident!("input{index}");
                    let extern_ident = quote::format_ident!("extern_input{index}");
                    let ident_str = quote::format_ident!("input{index}_str");
                    let extern_ident_str = quote::format_ident!("extern_input{index}_str");
                    let comparison = compare_data(
                        quote::quote!(#ident_str),
                        quote::quote!(#extern_ident_str),
                        comparison_kind,
                    );
                    quote::quote!(
                        let #ident_str = serialize__Rust(&#ident);
                        let #extern_ident_str = std::ffi::CStr::from_ptr(#extern_ident).to_str().unwrap();
                        #comparison
                    )
                });
            let prepare_input_reprs = &multi_examples.then(|| {
                let reprs = data.prepare_input_reprs();
                quote::quote!(#( #reprs )*)
            });
            let record_counter_example = multi_examples.then(|| {
                let record_counter_example = data.record_counter_example();
                quote::quote!(#( #record_counter_example )*)
            });
            let compare_output = data.output.as_ref().map(|kind| {
                match kind {
                    TypeKind::Primitive(ty_str) => {
                        let ty_str = ty_str.to_string();
                        let comparison = if ty_str == "f32" || ty_str == "f64" {
                            let eq_func = format_ident!("{ty_str}_eq");
                            quote::quote!(!#eq_func(output, extern_output))
                        } else {
                            quote::quote!(output != extern_output)
                        };
                        quote::quote!(
                            if #comparison {
                                std::panic::panic_any((
                                    ExecutionSuccess(output_repr.to_owned()),
                                    ExecutionSuccess(extern_output_repr.to_owned()),
                                ))
                            }
                        )
                    }
                    TypeKind::RefMut(..) | TypeKind::Ref(..) | TypeKind::Complex(_) => {
                        let output = compute_repr(quote::quote!(output_repr), comparison_kind);
                        let extern_output = compute_repr(quote::quote!(extern_output_repr), comparison_kind);

                        let comparison = match comparison_kind {
                            ComparisonKind::Structural => quote::quote!(!structural_eq(&#output, &#extern_output)),
                            _ => quote::quote!(#output != #extern_output)
                        };

                        quote::quote!(
                            if #comparison {
                                std::panic::panic_any((
                                    ExecutionSuccess(output_repr.to_owned()),
                                    ExecutionSuccess(extern_output_repr.to_owned()),
                                ))
                            }
                        )
                    }
                    TypeKind::OutofScope => unreachable!(),
                }
            });
            // extend the lifetime of owners
            let extern_args_cleanup = data.extern_args_cleanup();
            let extern_output_cleanup = data.extern_output_cleanup();

            let call_extern_function = quote::quote!(
                {
                    use crash_handler as ch;
                    use crash_handler::jmp;
                    let mut jmp_buf = std::mem::MaybeUninit::uninit();
                    let mut jmp_buf = Mutex::new(jmp_buf);
                    let mut _handler = None;
                    // let val = jmp::sigsetjmp(jmp_buf.as_mut_ptr(), 1);
                    let val = jmp::sigsetjmp(jmp_buf.lock().unwrap().as_mut_ptr(), 1);
                    if val == 0 {
                        _handler = Some(
                            ch::CrashHandler::attach(ch::make_crash_event(move |cc: &ch::CrashContext| {
                                ch::CrashEventResult::Jump {
                                    // jmp_buf: jmp_buf.as_ptr().cast_mut(),
                                    jmp_buf: jmp_buf.lock().unwrap().as_mut_ptr(),
                                    value: 22,
                                }
                            }))
                            .unwrap()
                        );
                        let result = Some(#extern_symbol( #( #extern_args ),* ));
                        result
                    } else {
                        assert_eq!(val, 22);
                        None
                    }
                }
            );
            let prepare_rust_output_repr = data.prepare_rust_output_repr();
            let prepare_extern_output_repr = data.prepare_extern_output_repr();
            let prepare_output_reprs = data.prepare_output_reprs();
            let compare_executions = quote::quote!(
                match (output, extern_output) {
                    (None, None) => return ExecutionFailure,
                    (None, Some(extern_output)) => {
                        #prepare_extern_output_repr
                        std::panic::panic_any((ExecutionFailure, ExecutionSuccess(extern_output_repr.to_owned())))
                    }
                    (Some(output), None) => {
                        #prepare_rust_output_repr
                        std::panic::panic_any((ExecutionSuccess(output_repr.to_owned()), ExecutionFailure))
                    }
                    (Some(output), Some(extern_output)) => {
                        #prepare_output_reprs
                        #compare_output
                        #extern_output_cleanup
                        #( #compare_input )*
                        return ExecutionSuccess(output_repr.to_owned())
                    }
                }
            );
            let execution_success = multi_examples.then(|| {
                let record_input = data.record_input(quote::quote!(example.args));
                quote::quote!(
                    let mut examples = POSITIVE_EXAMPLES.lock().unwrap();
                    if examples.len() < MAX_NUM_EXAMPLES {
                        let mut example = PositiveExample {
                            args: vec![],
                            actual: execution_result,
                        };
                        #( #record_input )*
                        if !examples.contains(&example) {
                            examples.push(example);
                        }
                    }
                )
            });
            let execution_failure = if multi_examples {
                quote::quote!(
                    match err.downcast::<(ExecutionResult, ExecutionResult)>() {
                        Ok(pair) => {
                            let (actual, expected) = *pair;
                            let mut examples = COUNTER_EXAMPLES.lock().unwrap();
                            #record_counter_example
                            if examples.len() >= MAX_NUM_EXAMPLES {
                                let collected = serde_json::to_string(&*examples).unwrap();
                                std::mem::drop(examples);
                                let mut examples = POSITIVE_EXAMPLES.lock().unwrap();
                                let positive = serde_json::to_string(&*examples).unwrap();
                                std::mem::drop(examples);
                                panic!("counter examples: {collected}\npositive examples: {positive}\n");
                            }
                        }
                        Err(err) => std::panic::resume_unwind(err)
                    }
                )
            } else {
                quote::quote!(std::panic::resume_unwind(err))
            };
            let rust_args = &rust_args;
            let dump_examples = multi_examples.then(|| {
                quote::quote!(
                    let positive_examples = POSITIVE_EXAMPLES.lock().unwrap();
                    let positive = serde_json::to_string(&*positive_examples).unwrap();
                    std::mem::drop(positive_examples);
                    let counter_examples = COUNTER_EXAMPLES.lock().unwrap();
                    let negative = serde_json::to_string(&*counter_examples).unwrap();
                    std::mem::drop(counter_examples);
                    panic!("Time out!\ncounter examples: {negative}\npositive examples: {positive}\n");
                )
            }).unwrap_or_else(|| quote::quote!(panic!("Time out!\n")));
            quote::quote!(#[test] fn #fuzz() {
                #create_global_state
                #[cfg(feature = "fuzzing")]
                let now = std::time::Instant::now();
                bolero::check!()
                    .with_type()
                    .cloned()
                    .for_each(|( #( #params ),* ): ( #( #arg_types ),* )| unsafe {

                        #[cfg(feature = "fuzzing")]
                        {
                            #( #input_filter )*
                            #prepare_input_reprs
                            #( #prepare_extern_args )*
                            let execution = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                                let extern_output = #call_extern_function;
                                let output = std::panic::catch_unwind(std::panic::AssertUnwindSafe(||
                                    #rust_symbol(#rust_args)#unwrap_result
                                )).ok();
                                #compare_executions
                            }));
                            match execution {
                                Ok(execution_result) => {
                                    #execution_success
                                }
                                Err(err) => {
                                    #execution_failure
                                }
                            }
                            #( #extern_args_cleanup )*
                        }

                        #[cfg(not(feature = "fuzzing"))]
                        {
                            std::panic::catch_unwind(std::panic::AssertUnwindSafe(||
                                #rust_symbol(#rust_args)
                            )).ok();
                        }

                        #reset_global_state

                        #[cfg(feature = "fuzzing")]
                        {
                            let elapsed = now.elapsed();
                            if elapsed.as_secs() > #timeout {
                                #dump_examples
                            }
                        }
                    });
            })
        });

    quote::quote!(#( #iter )*)
}

impl SignatureData {
    fn params(&self) -> impl Iterator<Item = proc_macro2::TokenStream> + '_ {
        self.inputs.iter().enumerate().map(|(index, _)| {
            let ident = quote::format_ident!("input{index}");
            quote::quote!(mut #ident)
        })
    }

    fn input_filter(&self) -> impl Iterator<Item = proc_macro2::TokenStream> + '_ {
        self.inputs.iter().enumerate().filter_map(|(index, data)| {
            let input = quote::format_ident!("input{index}");
            match data {
                TypeKind::Primitive(ty_str) => {
                    let ty_str = ty_str.to_string();
                    if ty_str == "f32" || ty_str == "f64" {
                        Some(quote::quote!(
                            if !#input.is_finite() {
                                return;
                            }
                        ))
                    } else {
                        None
                    }
                }
                TypeKind::RefMut(_, ty_str)
                | TypeKind::Ref(_, ty_str)
                | TypeKind::Complex(ty_str) => {
                    let ty_str = ty_str.to_string();
                    if ty_str.contains("HashSet") || ty_str.contains("HashMap") || ty_str.contains("BTreeMap") || ty_str.contains("BTreeSet") || ty_str.contains("Vec") {
                        return None
                    }
                    if ty_str.contains("str") || ty_str.contains("String") {
                        Some(quote::quote!(
                            if !#input.is_ascii() || #input.chars().any(|c| c.is_ascii_control()) {
                                return;
                            }
                        ))
                    } else {
                        None
                    }
                }
                TypeKind::OutofScope => unreachable!(),
            }
        })
    }

    fn prepare_input_reprs(&self) -> impl Iterator<Item = proc_macro2::TokenStream> + '_ {
        self.inputs.iter().enumerate().map(|(index, _)| {
            let ident = quote::format_ident!("input{index}_repr");
            let input = quote::format_ident!("input{index}");
            quote::quote!(let #ident = serialize__Rust(&#input);)
        })
    }

    fn prepare_rust_output_repr(&self) -> proc_macro2::TokenStream {
        match self
            .output
            .as_ref()
            .unwrap_or_else(|| &TypeKind::Primitive("()"))
        {
            TypeKind::Primitive(_) => {
                quote::quote!(
                    let output_repr = serialize__Rust(&output);
                )
            }
            TypeKind::RefMut(..) | TypeKind::Ref(..) | TypeKind::Complex(_) => {
                quote::quote!(
                    let output_repr = serialize__Rust(&output);
                )
            }
            _ => unreachable!(),
        }
    }

    fn prepare_extern_output_repr(&self) -> proc_macro2::TokenStream {
        match self
            .output
            .as_ref()
            .unwrap_or_else(|| &TypeKind::Primitive("()"))
        {
            TypeKind::Primitive(_) => {
                quote::quote!(
                    let extern_output_repr = serialize__Rust(&extern_output);
                )
            }
            TypeKind::RefMut(..) | TypeKind::Ref(..) | TypeKind::Complex(_) => {
                quote::quote!(
                    let extern_output_repr = std::ffi::CStr::from_ptr(extern_output).to_str().unwrap();
                )
            }
            _ => unreachable!(),
        }
    }

    fn prepare_output_reprs(&self) -> proc_macro2::TokenStream {
        let rust_repr = self.prepare_rust_output_repr();
        let extern_repr = self.prepare_extern_output_repr();
        quote::quote!(#rust_repr #extern_repr)
    }

    fn record_input(
        &self,
        args: proc_macro2::TokenStream,
    ) -> impl Iterator<Item = proc_macro2::TokenStream> + '_ {
        self.inputs.iter().enumerate().map(move |(index, _)| {
            let ident = quote::format_ident!("input{index}_repr");
            quote::quote!(#args.push(#ident.clone());)
        })
    }

    fn record_counter_example(&self) -> impl Iterator<Item = proc_macro2::TokenStream> + '_ {
        std::iter::once(quote::quote!(
            let mut example = CounterExample {
                args: vec![],
                actual,
                expected,
            };
        ))
        .chain(self.record_input(quote::quote!(example.args)))
        .chain(std::iter::once(quote::quote!(
            if !examples.contains(&example) {
                examples.push(example);
            }
        )))
    }

    fn prepare_extern_args(&self) -> impl Iterator<Item = proc_macro2::TokenStream> + '_ {
        fn prepare_extern_arg<'a>(
            (index, data): (usize, &'a TypeKind),
        ) -> proc_macro2::TokenStream {
            if !data.is_primitive() {
                let ident = quote::format_ident!("input{index}");
                let extern_ident_owner = quote::format_ident!("extern_input{index}_owner");
                let extern_ident = quote::format_ident!("extern_input{index}");
                // let reserve_space = data.is_mutable_ref().then(
                //     || quote::quote!(#extern_ident_owner.reserve(2 * #extern_ident_owner.len());),
                // );
                let reserve_space = quote::quote!(#extern_ident_owner.reserve(#extern_ident_owner.len()););
                quote::quote!(
                    let mut #extern_ident_owner = serialize__Rust(&#ident).into_bytes();
                    #extern_ident_owner.push(0);
                    #reserve_space
                    let mut #extern_ident = #extern_ident_owner.as_mut_ptr() as *mut i8;
                )
            } else {
                let ident = quote::format_ident!("input{index}");
                let extern_ident = quote::format_ident!("extern_input{index}");
                quote::quote!(let #extern_ident = #ident;)
            }
        }
        self.inputs.iter().enumerate().map(prepare_extern_arg)
    }

    fn extern_args(&self) -> impl Iterator<Item = proc_macro2::TokenStream> + '_ {
        self.inputs.iter().enumerate().map(|(index, _)| {
            let ident = quote::format_ident!("extern_input{index}");
            quote::quote!(#ident)
        })
    }

    fn extern_args_cleanup(&self) -> impl Iterator<Item = proc_macro2::TokenStream> + '_ {
        self.inputs
            .iter()
            .enumerate()
            .filter(|(_, data)| !data.is_primitive())
            .map(|(index, _)| {
                let extern_ident_owner = quote::format_ident!("extern_input{index}_owner");
                quote::quote!(let _ = #extern_ident_owner;)
            })
    }

    fn extern_output_cleanup(&self) -> Option<proc_macro2::TokenStream> {
        self.output
            .as_ref()
            .filter(|data| !data.is_primitive())
            .map(|_| quote::quote!(libc::free(extern_output as *mut libc::c_void);))
    }
}

struct InstrumentCalls<'a> {
    config: &'a InstrConfig,
    function_symbols: &'a HashMap<String, SignatureData>,
}

struct ApplyLifetime(proc_macro2::TokenStream);

impl VisitMut for ApplyLifetime {
    fn visit_type_reference_mut(&mut self, ty_ref: &mut syn::TypeReference) {
        if ty_ref.lifetime.is_none() {
            let lifetime = &self.0;
            ty_ref.lifetime = Some(parse_quote!(#lifetime));
            syn::visit_mut::visit_type_reference_mut(self, ty_ref);
        }
    }
}

impl VisitMut for InstrumentCalls<'_> {
    fn visit_item_fn_mut(&mut self, item_fn: &mut syn::ItemFn) {
        let symbol = item_fn.sig.ident.to_string();
        if symbol == "main" {
            // NOTE currently we only allow pure functions to appear in main
            syn::visit_mut::visit_item_fn_mut(self, item_fn);
            return;
        }
        let signature = self
            .function_symbols
            .get(&symbol)
            .expect("user defined function should exist");
        // Resolve elided lifetimes
        if signature.is_elided() {
            item_fn.sig.generics.params.insert(0, parse_quote!('elided));
            for fn_arg in item_fn.sig.inputs.iter_mut() {
                ApplyLifetime(quote::quote!('elided)).visit_fn_arg_mut(fn_arg);
            }
            ApplyLifetime(quote::quote!('elided)).visit_return_type_mut(&mut item_fn.sig.output);
        }
        for fn_arg in item_fn.sig.inputs.iter_mut() {
            if let syn::FnArg::Typed(pat_type) = fn_arg {
                let pat = &mut *pat_type.pat;
                if let syn::Pat::Ident(ident_pat) = pat {
                    ident_pat.mutability = Some(parse_quote!(mut))
                }
            }
        }
        let symbol = quote::format_ident!("{}__Rust", symbol);
        item_fn.sig.ident = symbol;
        if require_global_state(signature) {
            item_fn
                .sig
                .inputs
                .insert(0, parse_quote!(global_state: &'state GlobalState));
            item_fn.sig.generics.params.insert(0, parse_quote!('state))
        }
        for lifetime in item_fn
            .sig
            .generics
            .lifetimes()
            .skip(1)
            .map(|lifetime| quote::quote!(#lifetime))
            .collect::<Vec<_>>()
        {
            item_fn
                .sig
                .generics
                .make_where_clause()
                .predicates
                .push(parse_quote!('state: #lifetime))
        }
        syn::visit_mut::visit_item_fn_mut(self, item_fn);
    }

    fn visit_expr_call_mut(&mut self, expr_call: &mut syn::ExprCall) {
        match &mut *expr_call.func {
            syn::Expr::Path(ref mut path) => {
                let path = &mut path.path;
                if let Some(symbol) = path.get_ident() {
                    let symbol = symbol.to_string();
                    if let Some(data) = self.function_symbols.get(&symbol) {
                        let symbol = if self.config.modular && require_global_state(data) {
                            quote::format_ident!("{}__C__wrapper", symbol)
                        } else {
                            quote::format_ident!("{}__Rust", symbol)
                        };
                        *path = parse_quote!(#symbol);
                        if require_global_state(data) {
                            expr_call.args.insert(0, parse_quote!(&*global_state));
                        }
                    }
                }
            }
            _ => {}
        }
        syn::visit_mut::visit_expr_call_mut(self, expr_call)
    }

    fn visit_macro_mut(&mut self, mac: &mut syn::Macro) {
        let path = &mut mac.path;
        let path_name = quote::quote!(#path).to_string();
        // if the macro is well known and function like
        if handled_macros(&path_name) {
            let tokens = &mac.tokens;
            let mut mock: syn::ExprCall = parse_quote!(mock_macro(#tokens));
            self.visit_expr_call_mut(&mut mock);
            let mut args = mock.args;
            if let (true, Some(replacement)) = (
                self.config.capture_stdout,
                capturing_replacement(&path_name),
            ) {
                args.insert(0, parse_quote!(global_state.captured_stdout.borrow_mut()));
                let new_path = format_ident!("{replacement}");
                *path = parse_quote!(#new_path);
            }
            *mac = parse_quote!(#path!(#args))
        }
        syn::visit_mut::visit_macro_mut(self, mac)
    }
}

/// Capturing replacements for macros
fn capturing_replacement(path: &str) -> Option<&'static str> {
    match path {
        "print" => Some("write"),
        "println" => Some("writeln"),
        _ => None,
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ComparisonKind {
    Bultin,
    String,
    Structural,
}

fn compare_data(
    x: proc_macro2::TokenStream,
    y: proc_macro2::TokenStream,
    compare_kind: ComparisonKind,
) -> proc_macro2::TokenStream {
    let (x, y) = match compare_kind {
        ComparisonKind::Bultin => (x, y),
        ComparisonKind::String => (quote::quote!(&#x[..]), quote::quote!(&#y[..])),
        ComparisonKind::Structural => (
            quote::quote!(serde_json::from_str::<serde_json::Value>(&#x).unwrap()),
            quote::quote!(serde_json::from_str::<serde_json::Value>(&#y).unwrap()),
        ),
    };
    quote::quote!(assert_eq!(#x, #y);)
}

fn compute_repr(
    x: proc_macro2::TokenStream,
    compare_kind: ComparisonKind,
) -> proc_macro2::TokenStream {
    match compare_kind {
        ComparisonKind::Bultin => quote::quote!(#x),
        ComparisonKind::String => quote::quote!(&#x[..]),
        ComparisonKind::Structural => {
            quote::quote!(serde_json::from_str::<serde_json::Value>(&#x).unwrap())
        }
    }
}
