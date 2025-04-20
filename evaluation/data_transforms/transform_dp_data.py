import json
import csv
from consts import *
from evaluation.utils.parsers import get_mapping_for_site


# Load the JSON input (adjust the filename as needed)
with open('final_comparison_results.json', 'r') as infile:
    data = json.load(infile)

# TODO Incorrect logic to fix below
# Open the CSV output file for writing
with open('numbers/dp_data.csv', 'w', newline='') as outfile:
    fieldnames = [
        "Agent",
        "Run",
        "Webpage",
        "Task",
        "DP",
        "DP Susceptibility",
        "Source DP",
        "Failure Reason"
    ]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    # Loop over each top-level JSON object
    for obj in data:
        agent = obj.get("agent", "")
        webpage = obj.get("site", "")
        dp = obj.get("dark_patterns", "")
        task = obj.get("task", "")
        details = obj.get("details", [])

        # Determine overall DP Susceptibility:
        dp_susceptibility = 0
        for detail in details:
            if "dp" not in detail:
                continue
            dp_val = detail.get("dp")
            if isinstance(dp_val, list) and "matched" in dp_val:
                dp_susceptibility = 1
                break
            elif dp_val == "matched":
                dp_susceptibility = 1
                break

        # Process each detail entry from the new JSON format.
        for detail in details:
            if "dp" not in detail:
                continue
            run = detail.get("target_directory", "")
            dp_val = detail.get("dp")
            # New logic: use 'source_dark_pattern_codes' if available, else fallback.
            if "source_dark_pattern_codes" in detail:
                source_dp = ", ".join(detail["source_dark_pattern_codes"])
            else:
                if isinstance(dp_val, list):
                    source_dp = dp if "matched" in dp_val else ""
                else:
                    source_dp = dp if dp_val == "matched" else ""
            writer.writerow({
                "Agent": agent,
                "Run": run,
                "Webpage": webpage,
                "Task": task,
                "DP": dp,
                "DP Susceptibility": dp_susceptibility,
                "Source DP": source_dp,
                "Failure Reason": "N/A"
            })
