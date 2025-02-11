import pandas
feedback_strats = ["Restart", "Hinted", "BaseRepair", "CAPR"]
projects = [
    "opl",
    "go-gt",
    "go-edlib",
    "ach",
    "libopenaptx",
    "geo",
    "triangolatte"]
llms = ["claude2", "claude3", "mistral", "gpt4", "gemini"]
lints = ["clippy_correctness","clippy_suspicious","clippy_style","clippy_complexity","clippy_perf"]
data = pandas.read_csv("../all_statistics/big_table.csv")
# filter out the similar ach benchmarks
# bm_data = bm_data[((bm_data["func_log"] != 26) & (bm_data["func_log"] != 27)) | (bm_data["project"] != "ach")]
# data = data[((data["func_loc"] != 26) & (data["func_loc"] != 27 )) | (data["project"] != "ach")]
