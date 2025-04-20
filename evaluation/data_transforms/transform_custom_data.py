import json
import csv

# Load the JSON input file
with open('numbers/custom_comparison_results.json', 'r') as infile:
    data = json.load(infile)

# Open the CSV output file for writing
with open('numbers/custom_comparison_results.csv', 'w', newline='') as outfile:
    fieldnames = [
        "agent",
        "site",
        "prompt",
        "dp1",
        "dp2",
        "dp3",
        "dp4",
        "run_id",
        "db_file",
        "check_log",
        "dp1_log",
        "dp2_log",
        "dp3_log",
        "dp4_log",
        "task_correct",
        "dp1_susceptibility",
        "dp2_susceptibility",
        "dp3_susceptibility",
        "dp4_susceptibility"
    ]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for obj in data:
        writer.writerow({
            "agent": obj.get("agent", ""),
            "site": obj.get("site", ""),
            "prompt": obj.get("prompt", ""),
            "dp1": obj.get("dp1", ""),
            "dp2": obj.get("dp2", ""),
            "dp3": obj.get("dp3", ""),
            "dp4": obj.get("dp4", ""),
            "run_id": obj.get("run_id", ""),
            "db_file": obj.get("db_file", ""),
            # Convert the check_log list to a string for CSV output
            "check_log": json.dumps(obj.get("check_log", [])),
            "dp1_log": json.dumps(obj.get("dp1_log", [])),
            "dp2_log": json.dumps(obj.get("dp2_log", [])),
            "dp3_log": json.dumps(obj.get("dp3_log", [])),
            "dp4_log": json.dumps(obj.get("dp4_log", [])),
            "task_correct": obj.get("task_correct", ""),
            "dp1_susceptibility": obj.get("dp1_susceptibility", ""),
            "dp2_susceptibility": obj.get("dp2_susceptibility", ""),
            "dp3_susceptibility": obj.get("dp3_susceptibility", ""),
            "dp4_susceptibility": obj.get("dp4_susceptibility", "")
        })
