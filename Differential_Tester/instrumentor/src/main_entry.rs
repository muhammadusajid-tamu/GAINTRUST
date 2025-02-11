//! Find main fuzzing entry

// pub struct MainEntry<'me> {
//     function_symbols: &'me HashMap<String, SignatureData>,
// }

use std::collections::HashMap;

use petgraph::{
    algo::tarjan_scc,
    graph::{DefaultIx, DiGraph, NodeIndex},
};
use syn::visit::Visit;

use crate::handled_macros;
use crate::syntax::SignatureData;

pub fn find_main_entry(
    ast: &syn::File,
    function_symbols: &HashMap<String, SignatureData>,
) -> String {
    let call_graph = CallGraph::new(ast, function_symbols);
    let sccs = tarjan_scc(&call_graph.graph);

    let mut top_levels = vec![];

    for scc in sccs.iter().rev() {
        let useful = scc
            .iter()
            .filter_map(|node_idx| {
                let symbol = call_graph.map.get(node_idx).unwrap();
                if !function_symbols.get(&symbol[..]).unwrap().pure {
                    // Some(symbol)
                    Some(node_idx)
                } else {
                    None
                }
            })
            .collect::<Vec<_>>();
        match useful.len() {
            0 => continue,
            _ => {
                // skip top-level "unused" functions that don't call any other functions
                let node_idx = useful[0];
                if call_graph.graph.neighbors(*node_idx).count() != 0 {
                    let symbol = call_graph.map.get(node_idx).unwrap();
                    return symbol.to_string();
                } else {
                    top_levels.push(node_idx);
                }
                // return useful[0].to_string()
            } // _ => panic!("mutually recursive functions are not handled at this moment"),
        }
    }

    if top_levels.len() > 0 {
        let node_idx = top_levels[0];
        let symbol = call_graph.map.get(node_idx).unwrap();
        return symbol.to_string();
    }

    panic!("main entry not found")
}

struct CallGraph<'name> {
    nodes: HashMap<&'name str, NodeIndex<DefaultIx>>,
    map: HashMap<NodeIndex<DefaultIx>, &'name str>,
    graph: DiGraph<(), ()>,
}

impl<'name> CallGraph<'name> {
    fn new(file: &syn::File, function_symbols: &'name HashMap<String, SignatureData>) -> Self {
        let mut graph = DiGraph::new();
        let mut map = HashMap::new();
        let mut nodes = HashMap::new();
        for name in function_symbols.keys() {
            let node = graph.add_node(());
            nodes.insert(&name[..], node);
            map.insert(node, &name[..]);
        }
        let mut call_graph = CallGraph { nodes, map, graph };
        CallGraphBuilder {
            graph: &mut call_graph,
        }
        .visit_file(file);
        call_graph
    }
}

struct CallGraphBuilder<'me, 'name> {
    graph: &'me mut CallGraph<'name>,
}

impl Visit<'_> for CallGraphBuilder<'_, '_> {
    fn visit_item_fn(&mut self, item_fn: &'_ syn::ItemFn) {
        let name = item_fn.sig.ident.to_string();
        let Some(&idx) = self.graph.nodes.get(&name[..]) else {
            return;
        };
        struct Inner<'me, 'name>(NodeIndex<DefaultIx>, &'me mut CallGraph<'name>);
        impl Visit<'_> for Inner<'_, '_> {
            fn visit_expr_call(&mut self, expr_call: &'_ syn::ExprCall) {
                match &*expr_call.func {
                    syn::Expr::Path(ref path) => {
                        let path = &path.path;
                        if let Some(symbol) = path.get_ident() {
                            let symbol = symbol.to_string();
                            if let Some(&idx) = self.1.nodes.get(&symbol[..]) {
                                self.1.graph.add_edge(self.0, idx, ());
                            }
                        }
                    }
                    _ => {}
                }
                syn::visit::visit_expr_call(self, expr_call);
            }
            fn visit_macro(&mut self, mac: &syn::Macro) {
                let path = &mac.path;
                let path_name = quote::quote!(#path).to_string();
                if handled_macros(&path_name) {
                    let tokens = &mac.tokens;
                    let mock: syn::ExprCall = syn::parse_quote!(mock_macro(#tokens));
                    self.visit_expr_call(&mock);
                }
                syn::visit::visit_macro(self, mac)
            }
        }
        Inner(idx, self.graph).visit_block(&item_fn.block);
    }
}
