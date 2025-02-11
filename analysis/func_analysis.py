import pandas, numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from analysis.config import feedback_strats, llms, projects, bm_data, data
plt.rcParams["figure.figsize"] = [6.4,4.2]
s = 14
font = {'size' : s}
matplotlib.rc('font', **font)
matplotlib.rc('xtick', labelsize=s)
matplotlib.rc('ytick', labelsize=s)
# plt.xticks(rotation=45)

# bm_data = bm_data[((bm_data["func_log"] != 26) & (bm_data["func_log"] != 27)) | (bm_data["project"] != "ach")]
# data = data[((data["func_loc"] != 26) & (data["func_loc"] != 27 )) | (data["project"] != "ach")]

lower, upper = data["num_funcs"].min(), data["num_funcs"].max()
num_bins = 7
n = 7
r = np.arange(n)
width = 0.25
width = width / 2


# bins = [(1,2),(3, 4),(5, 6),(7, 9),(10,13),(14,18),(18,upper)]
bins = [(1,1),(2, 2),(3, 3),(4, 4),(5,6),(7,9),(9,upper)]
num_benches_in_bin = []
for bin in bins:
    num_benches_in_bin.append(
        len(bm_data[(bin[0] <= bm_data["funcs"]) & (bm_data["funcs"] <= bin[1])])
    )

data_filter = data["feedback_strategy"].isin(feedback_strats) & data["project"].isin(projects)

res = {}
for llm in llms:
    llm_res = data[data_filter & (data["llm"] == llm)]
    res[llm] = []
    for bin in bins:
        llm_res_in_bin = llm_res[(bin[0] <= llm_res["num_funcs"]) & (llm_res["num_funcs"] <= bin[1])]
        assert len(llm_res_in_bin) != 0
        success = llm_res_in_bin[llm_res_in_bin["final_status"] == "Success"]
        res[llm].append(len(success)/len(llm_res_in_bin))

color = iter(cm.rainbow(np.linspace(0, 1, len(llms))))
for idx, llm in enumerate(llms):
    #     print(idx)
    #     print(model)
    data = [data if data is not None else 0 for data in res[llm]]
    #     print(f"{model}: \n" + str(data))
    plt.bar(r + width * idx, data, color=next(color), width=width, label=llm)

plt.xlabel("Number of Functions")
plt.ylabel("Success Rate")
# plt.title("Success Rate for Number of Functions")

# plt.grid(linestyle='--')
plt.xticks(r + width / 2, [f"{b[0]}-{b[1]}\n[n={tot}]" if b[0] != b[1] else f"{b[0]}\n[n={tot}]" for (b, tot) in zip(bins, num_benches_in_bin)])
# plt.legend()

plt.tight_layout()
plt.savefig("func_analysis.jpeg")
# plt.show()
