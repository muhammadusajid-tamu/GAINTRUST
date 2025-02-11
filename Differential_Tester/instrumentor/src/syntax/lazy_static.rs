use syn::{parse::ParseStream, parse_quote, visit_mut::VisitMut};

pub struct Replace;

struct LazyStaticItems(Vec<syn::ItemStatic>);

impl syn::parse::Parse for LazyStaticItems {
    fn parse(input: ParseStream) -> syn::parse::Result<Self> {
        let mut items = Vec::new();
        while !input.is_empty() {
            items.push(input.parse()?);
        }
        syn::parse::Result::Ok(LazyStaticItems(items))
    }
}

impl VisitMut for Replace {
    fn visit_file_mut(&mut self, file: &mut syn::File) {
        let items = std::mem::take(&mut file.items);
        let mut new_items = vec![];
        for item in items.into_iter() {
            let syn::Item::Macro(item_macro) = item else {
                new_items.push(item);
                continue;
            };

            let mac = &item_macro.mac;

            match mac.path.get_ident() {
                Some(name) if name == "lazy_static" => {
                    let tokens = &mac.tokens;
                    let string = tokens.to_string().replace(" ref ", " ");
                    let static_items: Vec<syn::ItemStatic> =
                        syn::parse_str::<LazyStaticItems>(&string).unwrap().0;
                    for mut static_item in static_items.into_iter() {
                        let ty = static_item.ty;
                        static_item.ty = parse_quote!(once_cell::sync::Lazy<#ty>);
                        let expr = static_item.expr;
                        static_item.expr = parse_quote!(once_cell::sync::Lazy::new(|| #expr));
                        new_items.push(syn::Item::Static(static_item));
                    }
                }
                _ => {
                    new_items.push(syn::Item::Macro(item_macro));
                    continue;
                }
            }
        }

        file.items = new_items;
    }
}
