import os
import re
import sys
import sqlite3
import argparse
from typing import List, Dict, Union, Optional

###############################################################################
# 1. Directory / File-Finding Helpers
###############################################################################

def find_source_subdirs_with_number_suffix(root: str, pattern: str = r".*_\d+$") -> List[str]:
    """
    Recursively walk 'root' and return a list of full paths to directories 
    whose basename matches the given regex pattern (default: ends with '_<number>').
    """
    results = []
    regex = re.compile(pattern)
    for dirpath, dirnames, filenames in os.walk(root):
        base = os.path.basename(dirpath)
        if regex.match(base):
            results.append(dirpath)
    return results

def parse_prefix(dir_name: str) -> str:
    """
    Extract the prefix from a directory name ending with '_<number>'.
    E.g., "Add_one_laptop_to_cart_1" -> "Add_one_laptop_to_cart".
    """
    pattern = r"^(.*)_[0-9]+$"
    match = re.match(pattern, dir_name)
    if match:
        return match.group(1)
    return dir_name

def find_minimal_db(subdir_path: str) -> Optional[str]:
    """
    Finds the minimal db in the given subdirectory.
    Assumes minimal dbs have filenames ending with '_minimal.db'.
    Returns the full path to the minimal db or None if not found.
    """
    for filename in os.listdir(subdir_path):
        if filename.endswith("_minimal.db"):
            return os.path.join(subdir_path, filename)
    return None

def find_maximal_db(subdir_path: str) -> Optional[str]:
    """
    Finds the maximal db in the given subdirectory.
    Assumes maximal dbs have filenames ending with '.db' but not '_minimal.db'.
    Returns the full path or None if not found.
    """
    for filename in os.listdir(subdir_path):
        if filename.endswith(".db") and not filename.endswith("_minimal.db"):
            return os.path.join(subdir_path, filename)
    return None

def find_source_commands_script(subdir_path: str) -> Optional[str]:
    """
    Finds exactly one Python file in 'subdir_path' that:
      1) starts with 'test'
      2) ends with '_commands.py'.

    Returns the full path or None if not found.
    """
    pattern = re.compile(r"^test.*_commands\.py$")
    for filename in os.listdir(subdir_path):
        if pattern.match(filename):
            return os.path.join(subdir_path, filename)
    return None

def find_target_commands_script(subdir_path: str) -> Optional[str]:
    """
    Finds exactly one Python file in 'subdir_path' that ends with '_commands.py'
    (regardless of how it starts).
    """
    pattern = re.compile(r".*_commands\.py$")
    for filename in os.listdir(subdir_path):
        if pattern.match(filename):
            return os.path.join(subdir_path, filename)
    return None

###############################################################################
# 2. Database Loading
###############################################################################

def load_relavant_columns_from_db(db_path: str) -> Dict[int, Dict[str, Union[str, None]]]:
    """
    Connects to the SQLite database at db_path and retrieves all rows with their columns.
    Returns a dictionary with 'id' as keys and other columns as values,
    ignoring certain columns like 'url', 'additional_info', 'time_since_last_action'.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get the first user-defined table
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        LIMIT 1
    """)
    row = cursor.fetchone()
    if not row:
        print(f"[WARN] No user-defined tables found in {db_path}.")
        conn.close()
        return {}
    
    table_name = row[0]
    
    data = {}
    try:
        cursor.execute(f"SELECT * FROM \"{table_name}\"")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        ignored_columns = {'url', 'additional_info', 'time_since_last_action'}
        for row_tuple in rows:
            pk_id = row_tuple[0]
            row_dict = {}
            for col_name, val in zip(columns[1:], row_tuple[1:]):
                if col_name not in ignored_columns:
                    row_dict[col_name] = val
            data[pk_id] = row_dict
    except sqlite3.Error as e:
        print(f"[ERROR] Failed to retrieve data from table '{table_name}' in {db_path}: {e}")
        data = {}
    
    conn.close()
    return data

###############################################################################
# 3. Reading & Writing the Scripts, Inserting Assertion Lines
###############################################################################

def read_text_file(file_path: str) -> str:
    """
    Reads the content of a text file and returns it as a string.
    Returns an empty string if the file does not exist or is empty.
    """
    if not os.path.isfile(file_path):
        print(f"[WARN] File not found: {file_path}")
        return ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content
    except Exception as e:
        print(f"[ERROR] Failed to read file {file_path}: {e}")
        return ""

def read_script_lines(py_path: str) -> List[str]:
    """Return all lines from a python script as a list."""
    if not os.path.isfile(py_path):
        return []
    with open(py_path, "r", encoding="utf-8") as f:
        return f.readlines()

def write_script_lines(py_path: str, lines: List[str]) -> None:
    """Write the lines back to py_path."""
    with open(py_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def find_click_line_indexes(lines: List[str]) -> Dict[str, int]:
    """
    Return a mapping {selector_string: line_index} for lines that look like:
      await page.click("#some-id")
    or
      await page.click('#some-id')
    """
    pattern = re.compile(r"await\s+page\.click\(\s*[\"']([^\"']+)[\"']\s*\)")
    results = {}
    for i, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            selector = match.group(1).strip()
            results[selector] = i
    return results

def convert_db_row_to_selector(row_data: Dict[str, Union[str, None]]) -> Optional[str]:
    """
    Given a DB row (e.g., { 'event_type': 'click', 'xpath': ..., 'element_id': ... }),
    produce a CSS selector that matches how the script typically calls page.click('#...').
    If row_data['element_id'] is non-empty, we assume it might be something like 'add-to-cart-button-2'
    => '#add-to-cart-button-2'
    If row_data['element_id'] already starts with '#', keep it.
    Else, if there's an xpath we use that. Return None if no valid approach.
    """
    el_id = row_data.get("element_id", "") or ""
    xp = row_data.get("xpath", "") or ""

    if el_id.startswith("#"):
        return el_id  # e.g. '#add-to-cart-button-2'
    elif el_id:
        return f"#{el_id}"
    elif xp:
        # Some 'xpath' might literally be '#scratchpad' or similar
        return xp
    return None

def find_assertion_lines_after(lines: List[str], start_idx: int) -> List[str]:
    """
    Gather lines that contain either 'await expect(' or 'assert ' 
    after start_idx, stopping if we encounter another 'await page.click(' 
    or the next 'def' block, or we run out of lines.
    """
    click_re = re.compile(r"await\s+page\.click\(")
    def_re = re.compile(r"^\s*(async\s+def\s+|def\s+)")
    results = []

    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        if click_re.search(line) or def_re.search(line):
            break
        if "await expect(" in line or "assert " in line:
            results.append(line)
        i += 1

    return results

def insert_lines_after_index(original_lines: List[str], idx: int, new_lines: List[str]) -> List[str]:
    """
    Insert new_lines into original_lines immediately *after* line index idx.
    """
    if not new_lines:
        return original_lines
    if idx >= len(original_lines) - 1:
        return original_lines + new_lines
    return original_lines[:idx+1] + new_lines + original_lines[idx+1:]

def merge_playwright_scripts(
    source_data: Dict[int, Dict[str, Union[str, None]]],
    target_data: Dict[int, Dict[str, Union[str, None]]],
    source_lines: List[str],
    target_lines: List[str],
) -> Optional[List[str]]:
    """
    1. Identify in source_data all rows with event_type='click'.
    2. For each, see if there's a matching row in target_data 
       where either element_id or xpath is the same.
    3. If yes, we find the 'selector' in source & target scripts, 
       gather assertion lines from A after the click, 
       insert them in B after the matched click.
    4. Return the final merged lines for B.
    """
    src_click_map = find_click_line_indexes(source_lines)
    tgt_click_map = find_click_line_indexes(target_lines)

    inserts = []
    for pkA, rowA in source_data.items():
        if rowA.get('event_type') != 'click':
            continue

        src_sel = convert_db_row_to_selector(rowA)
        if not src_sel or src_sel not in src_click_map:
            continue

        # match by either element_id or xpath
        elA = rowA.get('element_id', '')
        xpA = rowA.get('xpath', '')
        matched_pkB = None
        for pkB, rowB in target_data.items():
            if rowB.get('event_type') != 'click':
                continue
            elB = rowB.get('element_id', '')
            xpB = rowB.get('xpath', '')
            if (elA and elA == elB) or (xpA and xpA == xpB):
                matched_pkB = pkB
                break

        if not matched_pkB:
            continue

        tgt_sel = convert_db_row_to_selector(target_data[matched_pkB])
        if not tgt_sel or tgt_sel not in tgt_click_map:
            continue

        # gather assertion lines from A
        src_click_idx = src_click_map[src_sel]
        assertion_lines = find_assertion_lines_after(source_lines, src_click_idx)
        if not assertion_lines:
            continue

        # prepare insertion in B
        tgt_click_idx = tgt_click_map[tgt_sel]
        inserts.append((tgt_click_idx, assertion_lines))

    # sort by ascending line index
    inserts.sort(key=lambda x: x[0])
    if not inserts:
        return None  # No new assertion lines to merge

    merged = list(target_lines)
    shift = 0
    for (orig_idx, new_lines) in inserts:
        real_idx = orig_idx + shift
        merged = insert_lines_after_index(merged, real_idx, new_lines)
        shift += len(new_lines)
    return merged

###############################################################################
# 4. Main driver: Directory Traversal & Merging
###############################################################################

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Traverse source subdirectories (with minimal DB + test*_commands.py) and "
            "match to target subdirectories (with .db + ANY*_commands.py). Then merge "
            "assertion lines from the source script into the target script. "
            "The merged script will begin with 'test_'."
        )
    )
    parser.add_argument(
        "source_dir",
        type=str,
        help="Path to the source directory containing subdirs with _minimal.db + test*_commands.py"
    )
    parser.add_argument(
        "target_dir",
        type=str,
        help="Path to the target directory containing subdirs with .db + ANY*_commands.py"
    )
    parser.add_argument(
        "--merged-suffix",
        type=str,
        default="_merged.py",
        help="Suffix to append to merged script (default: _merged.py). The final file name will always start with 'test_'."
    )
    args = parser.parse_args()

    source_dir = args.source_dir
    target_dir = args.target_dir
    merged_suffix = args.merged_suffix

    if not os.path.isdir(source_dir):
        print(f"[ERROR] Source directory does not exist: {source_dir}")
        sys.exit(1)
    if not os.path.isdir(target_dir):
        print(f"[ERROR] Target directory does not exist: {target_dir}")
        sys.exit(1)

    # Step 1: Find all source subdirectories ending with '_<number>'
    source_subdirs = find_source_subdirs_with_number_suffix(source_dir, r".*_\d+$")
    if not source_subdirs:
        print(f"[INFO] No subdirectories ending with '_<number>' found in source directory: {source_dir}")
        sys.exit(0)

    log_path = "merge_log.txt"
    try:
        log_file = open(log_path, "w", encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Failed to create log file {log_path}: {e}")
        sys.exit(1)

    for src_subdir in sorted(source_subdirs):
        src_dir_basename = os.path.basename(src_subdir)
        prefix = parse_prefix(src_dir_basename)
        print(f"\n=== Processing Source Subdir: {src_subdir} (Prefix: '{prefix}') ===")

        # read optional site/task if present
        site_txt_path = os.path.join(src_subdir, f"{src_dir_basename}_site.txt")
        task_txt_path = os.path.join(src_subdir, f"{src_dir_basename}_task.txt")
        site = read_text_file(site_txt_path)
        task_txt = read_text_file(task_txt_path)

        # find minimal DB + source commands script
        minimal_db = find_minimal_db(src_subdir)
        if not minimal_db:
            print(f"[WARN] No minimal database found in source subdir: {src_subdir}")
            continue
        src_py_path = find_source_commands_script(src_subdir)
        if not src_py_path:
            print(f"[WARN] No test*_commands.py found in source subdir: {src_subdir}")
            continue

        # load data + lines from source
        source_data = load_relavant_columns_from_db(minimal_db)
        source_lines = read_script_lines(src_py_path)

        # gather possible target subdirs by prefix
        matched_target_subdirs = []
        for agent in os.listdir(target_dir):
            agent_path = os.path.join(target_dir, agent)
            if os.path.isdir(agent_path):
                for dirpath, dirnames, filenames in os.walk(agent_path):
                    base = os.path.basename(dirpath)
                    if base.startswith(prefix + "_"):
                        matched_target_subdirs.append(dirpath)

        if not matched_target_subdirs:
            print(f"[WARN] No matching target subdirectories for prefix '{prefix}'")
            continue

        print(f"[INFO] Found {len(matched_target_subdirs)} matching target subdir(s) for prefix '{prefix}':")

        for tgt_subdir in sorted(matched_target_subdirs):
            tgt_dir_basename = os.path.basename(tgt_subdir)
            print(f"\n--- Merging Source: {src_subdir} => Target: {tgt_subdir} ---")

            # find the 'maximal' db + target commands script
            maximal_db = find_maximal_db(tgt_subdir)
            if not maximal_db:
                print(f"[WARN] No maximal database found in target subdir: {tgt_subdir}")
                continue
            tgt_py_path = find_target_commands_script(tgt_subdir)
            if not tgt_py_path:
                print(f"[WARN] No *_commands.py found in target subdir: {tgt_subdir}")
                continue

            target_data = load_relavant_columns_from_db(maximal_db)
            target_lines = read_script_lines(tgt_py_path)

            # merge
            if target_lines:
                merged_lines = merge_playwright_scripts(source_data, target_data, source_lines, target_lines)
                if not merged_lines:
                    print(f"[INFO] No new assertion lines found for merging. Skipping creation of test_ file for {tgt_subdir}")
                else:
                    # Construct the merged script name so it starts with test_, 
                    # plus your custom suffix if desired.
                    base_no_ext = os.path.splitext(os.path.basename(tgt_py_path))[0]  
                    # e.g. "myapp_commands"
                    merged_file_name = "test_" + base_no_ext + merged_suffix  
                    # e.g. "test_myapp_commands_merged.py"
                    merged_py_path = os.path.join(os.path.dirname(tgt_py_path), merged_file_name)

                    write_script_lines(merged_py_path, merged_lines)
                    print(f"[INFO] Merged script written to: {merged_py_path}")
                    log_file.write(f"[INFO] Merged script written to: {merged_py_path}\n")

    log_file.close()
    print(f"\n[INFO] Merging finished. See {log_path} for details.")

if __name__ == "__main__":
    main()
