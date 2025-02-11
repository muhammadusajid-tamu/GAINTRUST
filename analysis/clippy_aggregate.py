from analysis.config import feedback_strats, llms, projects, bm_data, data, lints
from collections import defaultdict
import json

agg = defaultdict(int)
for d in data["rustc_warnings"]:
    for key, val in json.loads(d).items():
        agg[key] += val
print("\n".join([f"{key} : {val}" for key, val in agg.items()]))