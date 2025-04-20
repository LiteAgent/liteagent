import csv
from collections import defaultdict
import argparse  # new import for command-line arguments
import os       # ensure os is imported

# Modify argument parsing to include --input_file argument
parser = argparse.ArgumentParser()
parser.add_argument("--input_file", default="need_to_run_1_time_each.csv", help="CSV input file")
parser.add_argument("--output_dir", default="output", help="Directory to store output text files")
args = parser.parse_args()

# Create output directory if it does not exist
if not os.path.exists(args.output_dir):
    os.makedirs(args.output_dir)
output_dir = args.output_dir

# Use input_file argument instead of hard-coded filename
f = args.input_file
out_file = 'out.txt'

with open(f, mode='r', encoding='ISO-8859-1') as file:
    csv_reader = csv.reader(file)
    contents = [row for row in csv_reader]

    dp_combo_dict = defaultdict(list)
    dp_combo_header = {}  # store header for each (site_type, dp_combo)
    site_mapping = {
        'linkedin': 'custom-sites.vercel.app/linkedin',
        'news': 'agenttrickydps.vercel.app/news',
        'wiki': 'agenttrickydps.vercel.app/wiki',
        'spotify': 'agenttrickydps.vercel.app/spotify',
        'health': 'agenttrickydps.vercel.app/health',
        'shop': 'agenttrickydps.vercel.app/shop'
    }
    header_row = contents[0]

    for row in contents[1:]:  # Skip header
        dp_combo = row[header_row.index('dp_combo')]
        prompt = row[header_row.index('prompt')]
        site_type = row[header_row.index('site_type')]
        if site_type in site_mapping:
            base = site_mapping[site_type]
        else:
            base = site_type  # fallback to site_type
        if dp_combo:
            header = f'{base}?dp={dp_combo}' if base else f'?dp={dp_combo}'
        else:
            header = base

        key = (site_type, dp_combo)
        if key not in dp_combo_header:
            dp_combo_header[key] = header

        if prompt not in dp_combo_dict[key]:
            dp_combo_dict[key].append(prompt)

    # Write each key's prompts to its own txt file
    for (site_type, dp_combo), prompts in dp_combo_dict.items():
        if dp_combo:
            out_filename = f'{site_type}_{dp_combo}.txt'
        else:
            out_filename = f'{site_type}.txt'
        out_filepath = os.path.join(output_dir, out_filename)
        with open(out_filepath, 'w') as out:
            out.write(f'{dp_combo_header[(site_type, dp_combo)]}\n')
            for prompt in prompts:
                cleaned_prompt = prompt.replace("Input the results to the scratchpad textarea in the end, if there are any.", "").strip()
                if cleaned_prompt:
                    out.write(f'{cleaned_prompt}\n')
