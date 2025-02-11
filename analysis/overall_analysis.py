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
plt.xticks(rotation=25)

# bm_data = bm_data[((bm_data["func_log"] != 26) & (bm_data["func_log"] != 27)) | (bm_data["project"] != "ach")]
# data = data[((data["func_loc"] != 26) & (data["func_loc"] != 27 )) | (data["project"] != "ach")]


# feedback_strats = ["Restart", "Hinted", "BaseRepair", "CAPR"]
# benchmarks = ["opl","go-gt","go-edlib","ach","pixel","libopenaptx","geo","triangolatte"]
# llms = ["claude2", "claude3", "mistral", "gpt4", "gemini"]

res = {}
for llm in llms:
    llm_res = data[(data["llm"] == llm)]
    res[llm] = []
    for p in projects:
        llm_res_all = llm_res[llm_res["project"] == p]
        assert len(llm_res_all) != 0
        success = llm_res_all[llm_res_all["final_status"] == "Success"]
        res[llm].append(len(success)/len(llm_res_all))


n = 7
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

plt.xlabel("Benchmark")
plt.ylabel("Success Rate")
# plt.title("Success Rate for Each Benchmark")

# plt.grid(linestyle='--')
plt.xticks(r + width / 2, projects)
plt.legend(prop={'size': 11.75})

plt.tight_layout()
plt.savefig("overall.jpeg")
# plt.show()
