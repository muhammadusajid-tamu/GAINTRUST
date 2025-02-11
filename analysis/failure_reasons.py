from analysis.config import feedback_strats, llms, projects, bm_data, data, lints

failures = data[data["final_status"] == "Fail"]
print((failures["status_detail"] == "Did not compile").value_counts()[True]/len(failures))
print((failures["status_detail"].isin(["Fail", "Fail after fixing once"])).value_counts()[True]/len(failures))
print((failures["status_detail"].isin(['Initial Oracle OOS', 'Oracle Somtimes OOS', 'Oracle Always OOS', 'Pending', 'Crash'])).value_counts()[True]/len(failures))
print(failures["status_detail"].unique())
