import json
import csv

# Load the JSON input (adjust the filename as needed)
with open('final_comparison_results.json', 'r') as infile:
    data = json.load(infile)

# Create a mapping of unique task strings to unique IDs.
unique_tasks = { obj.get("task", "") for obj in data }
sorted_unique_tasks = sorted(unique_tasks)
task_mapping = { task: f"T{idx+1}" for idx, task in enumerate(sorted_unique_tasks) }

# Sort tasks for output (preserving alphabetical order by task description)
sorted_data = sorted(data, key=lambda o: o.get("task", ""))

# Open the CSV output file for writing (you can name the file as desired)
with open('numbers/task_details.csv', 'w', newline='') as outfile:
    fieldnames = [
        "Webpage",
        "Task ID",
        "Task Description",
        "Checks for correctness",
        "Brandon Verification",
        "Devin Verification",
        "Arjun Verification",
        "Ananth Verification"
    ]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    # Loop over each task and use the mapping for a unique task ID.
    for obj in sorted_data:
        webpage = obj.get("site", "")
        task = obj.get("task", "")
        task_id = task_mapping.get(task, "")  # Retrieve task ID from mapping.
        # Replace old details-based check with aggregated_result-based checks.
        agg = obj.get("aggregated_result", {})
        checks = []
        if agg.get("assertion", {}).get("correct", 0) > 0:
            checks.append("assertion")
        if agg.get("scratchpad", {}).get("correct", 0) > 0:
            checks.append("scratchpad")
        if agg.get("db", {}).get("correct", 0) > 0:
            checks.append("db")
        checks_for_correctness = ", ".join(checks)

        # Write one row per task.
        writer.writerow({
            "Webpage": webpage,
            "Task ID": task_id,
            "Task Description": task,
            "Checks for correctness": checks_for_correctness,
            "Brandon Verification": "",
            "Devin Verification": "",
            "Arjun Verification": "",
            "Ananth Verification": ""
        })
