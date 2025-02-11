use crate::InstrConfig;

impl InstrConfig {
    pub fn communication(&self) -> proc_macro2::TokenStream {
        quote::quote!(
            mod communication {
                // serialize/deserialize a Rust data
                use serde::{Deserialize, Serialize};

                trait SpecSerialize {
                    fn serialize(&self) -> String;
                }

                impl<T> SpecSerialize for T
                where
                    T: Serialize,
                {
                    default fn serialize(&self) -> String {
                        serde_json::to_string(self).unwrap()
                    }
                }

                trait SpecDeserialize<'a> {
                    fn deserialize(_: &'a str) -> Self;
                }

                impl<'a, T> SpecDeserialize<'a> for T
                where
                    T: Deserialize<'a>,
                {
                    default fn deserialize(s: &'a str) -> Self {
                        serde_json::from_str(s).unwrap()
                    }
                }

                pub fn serialize__Rust<T: Serialize>(data: &T) -> String {
                    <T as SpecSerialize>::serialize(data)
                }

                pub fn deserialize__Rust<'state: 'a, 'a, T: Deserialize<'a>>(
                    global_state: &'state crate::GlobalState,
                    s: *mut i8,
                ) -> T {
                    unsafe {
                        let st = std::ffi::CStr::from_ptr(s).to_str().unwrap();
                        let st = global_state.arena.alloc_str(st);
                        <T as SpecDeserialize>::deserialize(st)
                    }
                }
            }
            use communication::*;
        )
    }
}
