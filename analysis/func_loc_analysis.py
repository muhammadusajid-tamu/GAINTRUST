import pandas, numpy as np
import math
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from analysis.config import feedback_strats, llms, projects, bm_data, data

bm_data = bm_data[((bm_data["func_log"] != 26) & (bm_data["func_log"] != 27)) | (bm_data["project"] != "ach")]
data = data[((data["func_loc"] != 26) & (data["func_loc"] != 27 )) | (data["project"] != "ach")]

lower, upper = data["func_loc"].min(), data["func_loc"].max()
num_bins = n = 7
starts = list(map(lambda i: bm_data["func_log"].sort_values().iloc[i], range(0, len(bm_data), math.ceil(len(bm_data)/num_bins))))

r = np.arange(n)
width = 0.25
width = width / 2


bin_size = (upper - lower) // num_bins
bins = []
for i in range(0, len(starts)):
    if len(bins) == num_bins - 1:
        bins.append((starts[i], upper))
        break
    else:
        bins.append((starts[i], starts[i+1]-1))
# bins = [(0,24),(25, 49),(50, 74), (25, 99), (100, 124),(125,149), (150,199), (200, upper)]
num_benches_in_bin = []
for bin in bins:
    num_benches_in_bin.append(
        len(bm_data[(bin[0] <= bm_data["func_log"]) & (bm_data["func_log"] <= bin[1])])
    )

data_filter = data["feedback_strategy"].isin(feedback_strats) & data["project"].isin(projects)

res = {}
for llm in llms:
    llm_res = data[data_filter & (data["llm"] == llm)]
    res[llm] = []
    for bin in bins:
        llm_res_in_bin = llm_res[(bin[0] <= llm_res["func_loc"]) & (llm_res["func_loc"] <= bin[1])]
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

plt.xlabel("Lines of Code")
plt.ylabel("Success Rate")
plt.title("Success Rate for Function LoC")

# plt.grid(linestyle='--')
plt.xticks(r + width / 2, [f"{s[0]}-{s[1]}\n[n={tot}]" for (s, tot) in zip(bins, num_benches_in_bin)])
plt.legend()

plt.savefig("func_loc_analysis.jpeg")
# plt.show()
