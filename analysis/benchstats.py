from analysis.config import feedback_strats, llms, projects, bm_data, data, lints

for p in projects:
    b = bm_data[bm_data["project"] == p].sort_values("language")
    loc = " \\textbf{/} ".join([str(int(i)) for i in [b['loc'].min(), b['loc'].max(), b['loc'].mean()]])
    funcs = " \\textbf{/} ".join([str(round(i,1)) for i in [b['funcs'].min(), b['funcs'].max(), b['funcs'].mean()]])
    print(f"\\textit{{{p}}} & {b['language'].iloc[0].capitalize()} & {len(b)} & {loc} & {funcs} \\\\")