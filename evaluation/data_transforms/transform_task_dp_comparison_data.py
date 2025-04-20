import json
import csv
from evaluation.utils.parsers import get_mapping_for_site  # Returns the appropriate mapping dict for a given site

def get_unmapped_code(raw_code, website):
    """
    Given a raw DP value (which may be a full description) and a website,
    use the mapping for that site (returned by get_mapping_for_site) to reverse‐lookup
    the unmapped (short) code. If not found, return the raw code.
    """
    mapping = get_mapping_for_site(website)
    # Iterate over the mapping: keys are short codes, values are full descriptions.
    for short_code, full_desc in mapping.items():
        if full_desc.lower() == raw_code.lower():
            return short_code
    return raw_code

# Load the JSON input (adjust the filename as needed)
with open('final_comparison_results.json', 'r') as infile:
    data = json.load(infile)

# Group data by individual DP code (using the unmapped short code).
# Each group will accumulate a set of base URLs, tasks, and full DP descriptions.
dp_groups = {}

for obj in data:
    dark_patterns = obj.get("dark_patterns", "").strip()
    # Skip if no dark patterns or if dark_patterns is "N/A"
    if not dark_patterns or dark_patterns.upper() == "N/A":
        continue

    website = obj.get("site", "").strip()
    # Remove any query parameters from the site (so we only keep the base URL)
    base_url = website.split('?')[0]
    task = obj.get("task", "").strip()

    # Determine the delimiter in dark_patterns.
    if "_" in dark_patterns:
        raw_codes = [code.strip() for code in dark_patterns.split("_") if code.strip()]
    elif "|" in dark_patterns:
        raw_codes = [code.strip() for code in dark_patterns.split("|") if code.strip()]
    else:
        raw_codes = [dark_patterns]

    for raw_code in raw_codes:
        # Convert the raw value into the unmapped (short) code using reverse lookup.
        unmapped = get_unmapped_code(raw_code, website)
        # Initialize the group if not present.
        if unmapped not in dp_groups:
            dp_groups[unmapped] = {"webpages": set(), "tasks": set(), "descriptions": set()}
        # Add the base URL (without any query)
        dp_groups[unmapped]["webpages"].add(base_url)
        dp_groups[unmapped]["tasks"].add(task)
        # Look up the full description from the mapping.
        mapping = get_mapping_for_site(website)
        full_desc = mapping.get(unmapped, raw_code)
        dp_groups[unmapped]["descriptions"].add(full_desc)

# Sort the unique DP codes and assign each a unique ID (e.g. D1, D2, …)
sorted_codes = sorted(dp_groups.keys())
dp_id_mapping = {code: f"D{idx+1}" for idx, code in enumerate(sorted_codes)}

# Open the CSV output file for writing.
with open('numbers/dp_summary.csv', 'w', newline='') as outfile:
    fieldnames = [
        "Webpage",
        "Dark Pattern ID",
        "Dark Pattern Code",
        "DP Description",
        "Applicable Tasks",
        "Susceptibility checks",
        "Brandon Verification",
        "Devin Verification",
        "Arjun Verification",
        "Ananth Verification"
    ]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    # Write one row per individual DP (unmapped code).
    for code in sorted_codes:
        group = dp_groups[code]
        webpages_str = " | ".join(sorted(group["webpages"]))
        tasks_str = " | ".join(sorted(group["tasks"]))
        # Usually there will be a single full description; if more, join them with a comma.
        descriptions_str = ", ".join(sorted(group["descriptions"]))
        dp_id = dp_id_mapping[code]

        writer.writerow({
            "Webpage": webpages_str,
            "Dark Pattern ID": dp_id,
            "Dark Pattern Code": code,
            "DP Description": descriptions_str,
            "Applicable Tasks": tasks_str,
            "Susceptibility checks": "db",
            "Brandon Verification": "",
            "Devin Verification": "",
            "Arjun Verification": "",
            "Ananth Verification": ""
        })
