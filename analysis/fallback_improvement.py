import pandas, numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from analysis.config import feedback_strats, llms, projects, bm_data, data
import matplotlib, math
matplotlib.use('TkAgg')
plt.rcParams["figure.figsize"] = [6.4,3.8]
s = 14
font = {'size' : s}
matplotlib.rc('font', **font)
matplotlib.rc('xtick', labelsize=s)
matplotlib.rc('ytick', labelsize=s)
# plt.xticks(rotation=45)

res = {}
for llm in llms:
    llm_res = data[(data["llm"] == llm)]
    res[llm] = []
    for f in feedback_strats:
        llm_res_all = llm_res[llm_res["feedback_strategy"] == f]
        assert len(llm_res_all) != 0
        success = llm_res_all[llm_res_all["status_detail"] == "Success after feedback"]
        res[llm].append(len(success)/len(llm_res_all))

n = 4
r = np.arange(n)
width = 0.25
width = width / 2

color = iter(cm.rainbow(np.linspace(0, 1, len(llms))))
for idx, llm in enumerate(llms):
    #     print(idx)
    #     print(model)
    data = [data if data is not None else 0 for data in res[llm]]
    #     print(f"{model}: \n" + str(data))
    plt.bar(r + width * idx, data, color=next(color), width=width, label=llm)

plt.xlabel("Feedback Strategy")
plt.ylabel("Success Rate Improvement")
# plt.title("Improvement in Success Rate for Feedback Strategy")

# plt.grid(linestyle='--')
plt.xticks(r + width / 2, feedback_strats)
plt.legend()

plt.tight_layout()
plt.savefig("feedback_improvement.jpeg")