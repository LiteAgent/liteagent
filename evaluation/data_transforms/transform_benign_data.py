import json
import csv

# Load the JSON input (adjust the filename as needed)
with open('final_comparison_results.json', 'r') as infile:
    data = json.load(infile)

# Open the CSV output file for writing
with open('numbers/benign_data.csv', 'w', newline='') as outfile:
    fieldnames = ["Agent", "Run", "Webpage", "Task", "Task Completion", "Eval Method", "Failure Reason"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    # Loop over each top-level JSON object
    for obj in data:
        agent = obj.get("agent", "")
        webpage = obj.get("site", "")
        task = obj.get("task", "")
        details_list = obj.get("details", [])
        
        for entry in details_list:
            run = entry.get("target_directory", "")
            for method in ["db", "scratchpad", "assertion"]:
                if method in entry and entry.get(method) != "":
                    writer.writerow({
                        "Agent": agent,
                        "Run": run,
                        "Webpage": webpage,
                        "Task": task,
                        "Task Completion": 1 if entry.get(method, "") == "correct" else 0,
                        "Eval Method": method,
                        "Failure Reason": "N/A"
                    })
