#!/usr/bin/env python3
"""
Script to filter tasks from run files using global indices from Filtered_Rows.csv,
grouping the output by the full site URL (including the ?dp parameter).

Each input .txt file is assumed to have:
    - First line: the full site URL (e.g. "agenttrickydps.vercel.app/health?dp=tos")
    - Subsequent lines: one task per line.

The CSV file (Filtered_Rows.csv) is assumed to contain one number per row—
each number represents the global (1-indexed) position of a task (ignoring the first line
of every file) that should be kept.

The script:
  - Processes all .txt files (in sorted order) in the input directory.
  - Assigns a global index to each task.
  - Keeps only tasks whose global index is in the CSV.
  - Groups the kept tasks by the full site URL (including the ?dp part),
    so that each dark‑pattern code (dp parameter) gets its own file.
  - Removes duplicate tasks per grouping.
  - Writes one output file per full site URL in the output directory.

Usage:
    python filter_tasks.py --input_dir path/to/input --output_dir path/to/output --csv path/to/Filtered_Rows.csv [--debug]
"""

import os
import csv
import argparse
import re

def load_filtered_indices(csv_path, debug=False):
    """
    Reads the CSV file (one number per row, no header) and returns a set of indices (integers).
    """
    indices = set()
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row and row[0].strip():
                try:
                    idx = int(row[0].strip())
                    indices.add(idx)
                    if debug:
                        print(f"[DEBUG] Loaded filtered index from CSV: {idx}")
                except ValueError:
                    if debug:
                        print(f"[DEBUG] Could not convert CSV row to int: '{row[0].strip()}'")
    if debug:
        print(f"[DEBUG] Total filtered indices loaded: {len(indices)}")
    return indices

def sanitize_filename(s):
    """
    Sanitizes a string for use as a filename.
    Replaces any character that is not alphanumeric, dot, underscore, or hyphen.
    """
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s)

def process_files(input_dir, filtered_indices, debug=False):
    """
    Processes each .txt file (in sorted order) in the input directory.
    
    For each file:
      - Reads all non-empty lines.
      - The first line is the full site URL (including the ?dp part) and is used as the key.
      - Each subsequent line is a task. A global counter (starting at 1) is assigned
        to every task (ignoring the first line of each file).
      - If the global index is in filtered_indices, the task is kept.
      - Duplicate tasks are not added multiple times.
    
    Returns a dictionary mapping each full site URL to a list of tasks.
    """
    site_tasks = {}
    global_index = 1
    for filename in sorted(os.listdir(input_dir)):
        if filename.endswith('.txt'):
            file_path = os.path.join(input_dir, filename)
            if debug:
                print(f"[DEBUG] Processing file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            if not lines:
                if debug:
                    print(f"[DEBUG] Skipping empty file: {file_path}")
                continue
            # Use the full site line (including the ?dp part) as the key
            full_site = lines[0]
            if debug:
                print(f"[DEBUG] Using full site key: '{full_site}'")
            tasks = lines[1:]
            for task in tasks:
                if debug:
                    print(f"[DEBUG] Global index {global_index}: '{task}'")
                if global_index in filtered_indices:
                    if debug:
                        print(f"[DEBUG] Task matched (global index {global_index}): '{task}'")
                    # Add task only if not already present for this site key.
                    if task not in site_tasks.setdefault(full_site, []):
                        site_tasks[full_site].append(task)
                else:
                    if debug:
                        print(f"[DEBUG] Task did NOT match (global index {global_index}): '{task}'")
                global_index += 1
    return site_tasks

def write_output_files(output_dir, site_tasks):
    """
    Writes one output file per full site URL (including dp code) in the output directory.
    
    The output file is named after the sanitized full site URL and contains:
      - The full site URL on the first line.
      - Each kept task on a new line.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for site, tasks in site_tasks.items():
        output_filename = sanitize_filename(site) + '.txt'
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(site + "\n")
            for task in tasks:
                f.write(task + "\n")
        print(f"Wrote file: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Filter tasks from run files using global indices and group by full site URL (including ?dp code)."
    )
    parser.add_argument('--input_dir', type=str, required=True,
                        help="Directory containing the input .txt run files.")
    parser.add_argument('--output_dir', type=str, required=True,
                        help="Directory where the output files will be written.")
    parser.add_argument('--csv', type=str, required=True,
                        help="Path to the CSV file (e.g. Filtered_Rows.csv) containing global task indices to keep.")
    parser.add_argument('--debug', action="store_true",
                        help="Enable debug output.")
    
    args = parser.parse_args()

    filtered_indices = load_filtered_indices(args.csv, debug=args.debug)
    print(f"Loaded {len(filtered_indices)} filtered indices from {args.csv}.")

    site_tasks = process_files(args.input_dir, filtered_indices, debug=args.debug)
    
    if args.debug:
        print(f"[DEBUG] Processed site tasks: {site_tasks}")

    if not site_tasks:
        print("No tasks matched the filtered list. Please check your CSV file and input files for consistency.")
        return

    write_output_files(args.output_dir, site_tasks)
    print("Processing complete.")

if __name__ == '__main__':
    main()
