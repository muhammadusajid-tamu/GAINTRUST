//! Very naive associated function mangling

use std::collections::HashMap;

use syn::{parse_quote, visit::Visit, visit_mut::VisitMut};

use crate::handled_macros;

enum Mutability {
    Mut,
    Not,
}

struct ReceiverTy {
    name: String,
    by_ref: Option<Mutability>,
}

/// Duplicated method names (even implemented for different types)
/// are not allowed.
///
/// Allowing duplicated method names requires static dispatch when
/// handling method call expressions. This may involves type checkers.
struct Associated(HashMap<String, ReceiverTy>);

impl Visit<'_> for Associated {
    fn visit_item_impl(&mut self, item_impl: &syn::ItemImpl) {
        if item_impl.trait_.is_some() {
            syn::visit::visit_item_impl(self, item_impl);
            return;
        }
        let self_ty = item_impl.self_ty.as_ref();
        let syn::Type::Path(..) = self_ty else {
            syn::visit::visit_item_impl(self, item_impl);
            return;
        };
        for impl_item in item_impl.items.iter() {
            let syn::ImplItem::Fn(impl_item_fn) = impl_item else {
                continue;
            };
            let name = quote::quote!(#self_ty).to_string();
            let by_ref = impl_item_fn
                .sig
                .receiver()
                .and_then(|receiver| match &*receiver.ty {
                    syn::Type::Reference(ty_ref) => {
                        if ty_ref.mutability.is_some() {
                            Some(Mutability::Mut)
                        } else {
                            Some(Mutability::Not)
                        }
                    }
                    _ => None,
                });
            let receiver_ty = ReceiverTy { name, by_ref };
            assert!(
                self.0
                    .insert(impl_item_fn.sig.ident.to_string(), receiver_ty)
                    .is_none(),
                "duplicated method names are not supported for now"
            );
        }
    }
}

/// Replace occurences of `self`
struct ReplaceSugaredSelf;

impl VisitMut for ReplaceSugaredSelf {
    fn visit_item_impl_mut(&mut self, item_impl: &mut syn::ItemImpl) {
        if item_impl.trait_.is_some() {
            return
        }
        syn::visit_mut::visit_item_impl_mut(self, item_impl);
    }

    fn visit_expr_path_mut(&mut self, expr_path: &mut syn::ExprPath) {
        if expr_path.qself.is_none()
            && expr_path
                .path
                .get_ident()
                .is_some_and(|ident| ident.to_string() == "self")
        {
            *expr_path = syn::parse_quote!(this);
        }
    }

    fn visit_macro_mut(&mut self, mac: &mut syn::Macro) {
        let path = &mut mac.path;
        let path_name = quote::quote!(#path).to_string();
        // if the macro is well known and function like
        if handled_macros(&path_name) {
            let tokens = &mac.tokens;
            let mut mock: syn::ExprCall = syn::parse_quote!(mock_macro(#tokens));
            self.visit_expr_call_mut(&mut mock);
            let args = mock.args;
            *mac = syn::parse_quote!(#path!(#args))
        }
        syn::visit_mut::visit_macro_mut(self, mac)
    }
}

/// Replace occurences of `Self`
struct ReplaceSelf<'me>(&'me str);

impl VisitMut for ReplaceSelf<'_> {
    fn visit_path_mut(&mut self, path: &mut syn::Path) {
        if matches!(path.get_ident(), Some(ident) if ident.to_string() == "Self") {
            *path = syn::parse_str(self.0).unwrap();
        }
        syn::visit_mut::visit_path_mut(self, path);
    }
}

struct MentionIdent<'a>(bool, &'a syn::Ident);

impl Visit<'_> for MentionIdent<'_> {
    fn visit_ident(&mut self, ident: &'_ syn::Ident) {
        if ident == self.1 {
            self.0 = true;
        }
    }
}

fn mention_ident(expr: &syn::Expr, ident: &syn::Ident) -> bool {
    let mut vis = MentionIdent(false, ident);
    vis.visit_expr(expr);
    return vis.0;
}

/// Handling two-phased borrows:
/// ```
/// v.push(v.len());
/// push(_, &mut v, v.len()); // fails borrow checker
/// ```
/// Presumably we would like to transform it into
/// ```
/// let mut temp0 = &two_phased v;
/// let temp1 = v.len();
/// push(_, temp0, temp1);
/// ```
/// However, two phased borrows are not visible in the surface
/// language. Here we can only make compromise on semantics
/// ```
/// let temp1 = v.len();
/// push(_, &mut v, temp1);
/// ```
fn two_phased_arg(
    recv: &syn::Ident,
    arg: &mut syn::Expr,
    new_name: &str,
) -> Option<proc_macro2::TokenStream> {
    mention_ident(&*arg, recv).then(|| {
        let new_name = &quote::format_ident!("{new_name}");
        let expr = std::mem::replace(arg, parse_quote!(#new_name));
        quote::quote!(let #new_name = #expr;)
    })
}

fn two_phased(
    recv: &syn::Expr,
    args: &mut syn::punctuated::Punctuated<syn::Expr, syn::token::Comma>,
) -> Vec<proc_macro2::TokenStream> {
    let syn::Expr::Path(path) = recv else {
        return vec![];
    };
    let Some(ident) = path.path.get_ident() else {
        return vec![];
    };
    args.iter_mut()
        .enumerate()
        .filter_map(|(index, arg)| two_phased_arg(ident, arg, &format!("two_phased_temp{index}")))
        .collect()
}

struct ReplaceMethodCalls<'me>(&'me HashMap<String, ReceiverTy>);

impl VisitMut for ReplaceMethodCalls<'_> {
    fn visit_expr_mut(&mut self, expr: &mut syn::Expr) {
        match expr {
            syn::Expr::MethodCall(expr_method_call) => {
                let symbol = expr_method_call.method.to_string();
                let Some(ty) = self.0.get(&symbol) else {
                    syn::visit_mut::visit_expr_mut(self, expr);
                    return;
                };

                let symbol = mangle(&ty.name, &symbol);

                let args = &mut expr_method_call.args;
                let receiver_expr = &*expr_method_call.receiver;
                let two_phased = matches!(ty.by_ref, Some(Mutability::Mut))
                    .then(|| two_phased(receiver_expr, args))
                    .unwrap_or_default();
                args.insert(
                    0,
                    match ty.by_ref {
                        Some(Mutability::Mut) => parse_quote!(&mut #receiver_expr),
                        Some(Mutability::Not) => parse_quote!(&#receiver_expr),
                        None => parse_quote!(#receiver_expr),
                    },
                );

                if !two_phased.is_empty() {
                    *expr = syn::parse_quote!({
                        #( #two_phased )*
                        #symbol(#args)
                    });
                } else {
                    *expr = syn::parse_quote!(#symbol(#args));
                }
            }
            syn::Expr::Call(expr_call) => {
                let syn::Expr::Path(path) = &mut *expr_call.func else {
                    syn::visit_mut::visit_expr_mut(self, expr);
                    return;
                };
                if path.path.segments.len() != 2 {
                    syn::visit_mut::visit_expr_mut(self, expr);
                    return;
                }
                let explicit_ty = &path.path.segments[0];
                let associated = &path.path.segments[1];
                let symbol = associated.ident.to_string();
                let Some(ty) = self.0.get(&symbol) else {
                    syn::visit_mut::visit_expr_mut(self, expr);
                    return;
                };
                if &ty.name != &explicit_ty.ident.to_string() {
                    syn::visit_mut::visit_expr_mut(self, expr);
                    return;
                }
                let symbol = mangle(&ty.name, &symbol);
                let args = &expr_call.args;
                *expr = syn::parse_quote!(#symbol(#args));
            }
            _ => {}
        }
        syn::visit_mut::visit_expr_mut(self, expr);
    }

    fn visit_macro_mut(&mut self, mac: &mut syn::Macro) {
        let path = &mut mac.path;
        let path_name = quote::quote!(#path).to_string();
        // if the macro is well known and function like
        if handled_macros(&path_name) {
            let tokens = &mac.tokens;
            let mut mock: syn::ExprCall = syn::parse_quote!(mock_macro(#tokens));
            self.visit_expr_call_mut(&mut mock);
            let args = mock.args;
            *mac = syn::parse_quote!(#path!(#args))
        }
        syn::visit_mut::visit_macro_mut(self, mac)
    }
}

pub fn mangle_associated_methods(mut ast: syn::File) -> syn::File {
    let mut vis = Associated(HashMap::new());
    vis.visit_file(&ast);
    let associated = vis.0;

    ReplaceSugaredSelf.visit_file_mut(&mut ast);
    ReplaceMethodCalls(&associated).visit_file_mut(&mut ast);

    let mut replacements = vec![];

    ast.items.iter_mut().for_each(|item| {
        let syn::Item::Impl(item_impl) = item else {
            return;
        };
        if item_impl.trait_.is_some() {
            return;
        }

        let items = std::mem::take(&mut item_impl.items)
            .into_iter()
            .filter_map(|impl_item| {
                let syn::ImplItem::Fn(mut impl_item_fn) = impl_item else {
                    return Some(impl_item);
                };

                let symbol = impl_item_fn.sig.ident.to_string();
                let Some(ty) = associated.get(&symbol) else {
                    return Some(syn::ImplItem::Fn(impl_item_fn));
                };
                let ty = &ty.name;

                let symbol = mangle(ty, &symbol);

                let mut sig = impl_item_fn.sig;
                let receiver_ty = sig.receiver().map(|recv| {
                    let mut receiver_ty = recv.ty.as_ref().clone();
                    ReplaceSelf(&ty).visit_type_mut(&mut receiver_ty);
                    receiver_ty
                });
                sig.ident = symbol;
                for arg in sig.inputs.iter_mut() {
                    match arg {
                        syn::FnArg::Receiver(..) => {
                            let receiver_ty = receiver_ty.as_ref().unwrap();
                            *arg = syn::parse_quote!(mut this: #receiver_ty);
                        }
                        syn::FnArg::Typed(pat_type) => {
                            ReplaceSelf(&ty).visit_type_mut(&mut *pat_type.ty)
                        }
                    }
                }
                if let syn::ReturnType::Type(_, ret_ty) = &mut sig.output {
                    ReplaceSelf(&ty).visit_type_mut(&mut *ret_ty)
                }

                ReplaceSelf(&ty).visit_block_mut(&mut impl_item_fn.block);

                replacements.push(syn::Item::Fn(syn::ItemFn {
                    attrs: impl_item_fn.attrs,
                    vis: impl_item_fn.vis,
                    sig,
                    block: Box::new(impl_item_fn.block),
                }));
                None
            })
            .collect::<Vec<_>>();

        item_impl.items = items;
    });

    ast.items.extend(replacements);

    ast
}

fn mangle(ty: &str, symbol: &str) -> proc_macro2::Ident {
    use convert_case::*;
    let ty = ty.to_case(Case::Snake);
    let symbol = quote::format_ident!("{ty}_{symbol}");
    symbol
}
