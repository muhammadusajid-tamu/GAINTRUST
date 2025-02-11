import pandas, numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from analysis.config import feedback_strats, llms, projects, bm_data, data, lints
import matplotlib, math
matplotlib.use('TkAgg')
plt.rcParams["figure.figsize"] = [6.4,4.2]
s = 14
font = {'size' : s}
matplotlib.rc('font', **font)
matplotlib.rc('xtick', labelsize=s)
matplotlib.rc('ytick', labelsize=s)
plt.xticks(rotation=25)

res = {}
for llm in llms:
    llm_res = data[(data["llm"] == llm) & (data["final_status"] == "Success")]
    res[llm] = []
    for wtype in lints:
        # success = llm_res_all[llm_res_all["status_detail"] == "Success after feedback"]
        res[llm].append(len(llm_res[llm_res[wtype].apply(lambda x: len(x) > 2)])/len(llm_res))
    res[llm].append(llm_res["has_unsafe"].value_counts()[True]/len(llm_res))
res["C2Rust"] = [2/112, 0, 81/112, 13/112, 0, 102/112]

n = 6
r = np.arange(n)
width = 0.25
width = width / 2

color = iter(cm.rainbow(np.linspace(0, 1, len(llms))))
for idx, llm in enumerate(llms):
    #     print(idx)
    #     print(model)
    data = [data if data is not None else 0 for data in res[llm]]
    #     print(f"{model}: \n" + str(data))
    plt.bar(r + width * idx, data, color=next(color), width=width, label=llm if llm != "mistral" else "mixtral")
plt.bar(r + width * len(llms), [2/112, 0, 81/112, 13/112, 0, 102/112], color='brown', width=width, label="C2Rust")

plt.xlabel("Lint Category")
plt.ylabel("Warning Rate")
# plt.title("Percentage of Rust Translations Containing Linter Warnings")

# plt.grid(linestyle='--')
plt.xticks(r + width / 2, [l.split("_")[1].capitalize() for l in lints] + ["Unsafe"])
plt.legend()

plt.tight_layout()
plt.savefig("clippy_res.jpeg")