use crate::InstrConfig;
use syn::{parse_quote, visit_mut::VisitMut, File};

pub fn code(ast: &File, config: &InstrConfig) -> proc_macro2::TokenStream {
    let wrapper_structs = config
        .wrapper_structs
        .then(|| wrapper_structs(ast))
        .into_iter()
        .flatten();
    quote::quote!(
        use super::*;
        use serde_json::Value;


        pub fn f32_eq(this: f32, that: f32) -> bool {
            return (this - that).abs() < f32::EPSILON
        }

        #[doc="Checking with reduced precision..."]
        pub fn f64_eq(this: f64, that: f64) -> bool {
            return (this - that).abs() < (f32::EPSILON as f64)
        }

        pub fn structural_eq(this: &Value, that: &Value) -> bool {
            match (this, that) {
                (Value::Null, Value::Null) => true,
                (Value::Bool(this), Value::Bool(that)) => this == that,
                (Value::Number(this), Value::Number(that)) => {
                    if let (Some(this), Some(that)) = (this.as_f64(), that.as_f64()) {
                        f64_eq(this, that)
                    } else {
                        false
                    }
                }
                (Value::String(this), Value::String(that)) => this == that,
                (Value::Array(this), Value::Array(that)) => {
                    if this.len() != that.len() {
                        return false;
                    }
                    this.iter()
                        .zip(that)
                        .all(|(this, that)| structural_eq(this, that))
                }
                (Value::Object(this), Value::Object(that)) => {
                    this.iter()
                        .zip(that)
                        .all(|((this_key, this_value), (that_key, that_value))| {
                            this_key == that_key && structural_eq(this_value, that_value)
                        })
                }
                _ => false
            }
        }

        mod generator {
            use super::*;
            // leaking generators for references
            pub fn ref_generator<'a, T: ?Sized + 'a>() -> impl ValueGenerator<Output = &'a T>
            where
                Box<T>: TypeGenerator,
            {
                bolero::gen::<Box<T>>().map_gen(|data| &*Box::leak(data))
            }

            pub fn ref_mut_generator<'a, T: ?Sized + 'a>() -> impl ValueGenerator<Output = &'a mut T>
            where
                Box<T>: TypeGenerator,
            {
                bolero::gen::<Box<T>>().map_gen(|data| Box::leak(data))
            }

            pub fn string_generator() -> impl ValueGenerator<Output = String> {
                bolero::gen::<String>().filter_gen(|data| {
                    data.is_ascii() && !data.chars().any(|c| c.is_ascii_control())
                })
            }

            pub fn boxed_str_generator() -> impl ValueGenerator<Output = Box<str>> {
                bolero::gen::<Box<str>>().filter_gen(|data| {
                    data.is_ascii() && !data.chars().any(|c| c.is_ascii_control())
                })
            }

            pub fn f32_generator() -> impl ValueGenerator<Output = f32> {
                bolero::gen::<f32>().filter_gen(|data| {
                    data.is_finite()
                })
            }

            pub fn f64_generator() -> impl ValueGenerator<Output = f64> {
                bolero::gen::<f64>().filter_gen(|data| {
                    data.is_finite()
                })
            }
        }
        pub use generator::*;

        use serde::{Serialize, Deserialize};

        pub mod arrays {
            use std::{convert::TryInto, marker::PhantomData};

            use serde::{
                de::{SeqAccess, Visitor},
                ser::SerializeTuple,
                Deserialize, Deserializer, Serialize, Serializer,
            };
            pub fn serialize<S: Serializer, T: Serialize, const N: usize>(
                data: &[T; N],
                ser: S,
            ) -> Result<S::Ok, S::Error> {
                let mut s = ser.serialize_tuple(N)?;
                for item in data {
                    s.serialize_element(item)?;
                }
                s.end()
            }

            struct ArrayVisitor<T, const N: usize>(PhantomData<T>);

            impl<'de, T, const N: usize> Visitor<'de> for ArrayVisitor<T, N>
            where
                T: Deserialize<'de>,
            {
                type Value = [T; N];

                fn expecting(&self, formatter: &mut std::fmt::Formatter) -> std::fmt::Result {
                    formatter.write_str(&format!("an array of length {}", N))
                }

                #[inline]
                fn visit_seq<A>(self, mut seq: A) -> Result<Self::Value, A::Error>
                where
                    A: SeqAccess<'de>,
                {
                    // can be optimized using MaybeUninit
                    let mut data = Vec::with_capacity(N);
                    for _ in 0..N {
                        match (seq.next_element())? {
                            Some(val) => data.push(val),
                            None => return Err(serde::de::Error::invalid_length(N, &self)),
                        }
                    }
                    match data.try_into() {
                        Ok(arr) => Ok(arr),
                        Err(_) => unreachable!(),
                    }
                }
            }
            pub fn deserialize<'de, D, T, const N: usize>(
                deserializer: D,
            ) -> Result<[T; N], D::Error>
            where
                D: Deserializer<'de>,
                T: Deserialize<'de>,
            {
                deserializer.deserialize_tuple(N, ArrayVisitor::<T, N>(PhantomData))
            }
        }

        // cannot derive Default as std only derive it for arrays of length
        // le 32...
        #[repr(transparent)]
        #[derive(Serialize, Deserialize, Debug, Copy, Clone)]
        enum ArrayWrapper<T, const N: usize> {
            #[serde(with = "arrays")]
            #[serde(bound(serialize = "T: Serialize", deserialize = "T: Deserialize<'de>"))]
            #[serde(untagged)]
            Arr([T; N])
        }

        #( #wrapper_structs )*
    )
}

fn wrapper_structs(ast: &File) -> impl Iterator<Item = proc_macro2::TokenStream> + '_ {
    ast.items
        .iter()
        .filter_map(|item| match item {
            syn::Item::Struct(item_struct) => Some(item_struct),
            _ => None,
        })
        .map(|item_struct| {
            let mut item_struct = item_struct.clone();
            struct ApplyWrapper;
            impl VisitMut for ApplyWrapper {
                fn visit_type_mut(&mut self, ty: &mut syn::Type) {
                    if let syn::Type::Array(type_array) = ty {
                        let elem_type = &type_array.elem;
                        let len = &type_array.len;
                        let len = if let syn::Expr::Lit(..) = len {
                            quote::quote!(#len)
                        } else {
                            quote::quote!({#len})
                        };
                        *ty = parse_quote!(
                            ArrayWrapper<#elem_type, #len>
                        )
                    }
                    syn::visit_mut::visit_type_mut(self, ty);
                }
            }
            ApplyWrapper.visit_item_struct_mut(&mut item_struct);
            let ident = &item_struct.ident.clone();
            let wrapper_ident = &quote::format_ident!("{ident}Wrapper");
            item_struct.ident = wrapper_ident.clone();
            let mut repred = false;
            for attr in item_struct.attrs.iter() {
                if attr.path().is_ident("repr") {
                    repred = true;
                }
            }
            if !repred {
                item_struct.attrs.push(parse_quote!(#[repr(C)]));
            }
            item_struct
                .attrs
                .push(parse_quote!(#[derive(Serialize, Deserialize)]));
            item_struct.vis = parse_quote!(pub);
            quote::quote!(
                #item_struct

                impl std::convert::From<#ident> for #wrapper_ident {
                    fn from(value: #ident) -> Self {
                        unsafe {
                            std::mem::transmute::<#ident, #wrapper_ident>(value)
                        }
                    }
                }

                impl std::convert::From<#wrapper_ident> for #ident {
                    fn from(value: #wrapper_ident) -> Self {
                        unsafe {
                            std::mem::transmute::<#wrapper_ident, #ident>(value)
                        }
                    }
                }
            )
        })
}
