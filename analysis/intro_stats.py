from analysis.config import feedback_strats, llms, projects, bm_data, data

for llm in llms:
    llm_data = data[data["llm"] == llm]
    print(str(round(len(llm_data[llm_data["final_status"] == "Success"])/len(llm_data)*100,1)) + f"\\% ({llm}),")
pass