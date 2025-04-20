import os
import re
import sys
import sqlite3
import argparse
from typing import List, Dict, Set, Tuple

def find_databases(root: str, db_pattern: str = r".*\.db$") -> List[str]:
    """
    Recursively walk 'root' and return a list of full paths to SQLite '.db' files matching the pattern.
    """
    results = []
    regex = re.compile(db_pattern, re.IGNORECASE)
    for dirpath, dirnames, filenames in os.walk(root):
        for filename in filenames:
            if regex.match(filename):
                results.append(os.path.join(dirpath, filename))
    return results

def get_all_table_names(db_path: str) -> List[str]:
    """
    Retrieves all user-defined table names from the SQLite database.
    Excludes internal SQLite tables.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
    """)
    rows = cursor.fetchall()
    conn.close()
    table_names = [row[0] for row in rows]
    return table_names

def load_input_values(db_path: str, table_name: str) -> List[Dict]:
    """
    Loads all input_value entries from the specified table in ascending ID order.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = f"""
        SELECT
            id,
            input_value,
            element_id
        FROM "{table_name}"
        ORDER BY id
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[ERROR] Failed to retrieve data from '{table_name}' in {db_path}: {e}")
        conn.close()
        return []
    
    conn.close()

    found_scratchpad = False
    filtered_actions = []
    for row in rows:
        element_id = row[2] or ""
        if found_scratchpad:
            filtered_actions.append({
                "id": row[0],
                "input_value": row[1] or ""
            })
        elif element_id == "scratchpad":
            found_scratchpad = True
    return filtered_actions

def get_longest_input(actions: List[Dict]) -> Dict:
    """
    Returns the input_value with the maximum length.
    If multiple entries have the same maximum length, returns the one with the highest ID.
    """
    if not actions:
        return {}
    max_length = max(len(action["input_value"]) for action in actions)
    # Filter actions with the maximum length
    longest_actions = [action for action in actions if len(action["input_value"]) == max_length]
    # Return the action with the highest ID (last in ascending order)
    return longest_actions[-1]

def write_to_scratchpad(db_dir: str, table_name: str, input_value: str):
    """
    Writes the approved input_value to 'scratchpad.txt' in the specified directory.
    Overwrites the file if it already exists.
    Creates a backup before overwriting.
    """
    scratchpad_path = os.path.join(db_dir, "scratchpad.txt")
    backup_path = scratchpad_path + ".bak"
    
    # Create a backup if scratchpad.txt exists
    if os.path.isfile(scratchpad_path):
        try:
            os.rename(scratchpad_path, backup_path)
            print(f"[INFO] Backup created: {backup_path}")
        except Exception as e:
            print(f"[ERROR] Failed to create backup for '{scratchpad_path}': {e}")
            return  # Exit the function to prevent data loss
    
    # Write the new input_value to scratchpad.txt
    try:
        with open(scratchpad_path, "w", encoding="utf-8") as f:
            f.write(input_value + "\n")
        print(f"[INFO] Written to scratchpad: {scratchpad_path}")
    except Exception as e:
        print(f"[ERROR] Failed to write to scratchpad '{scratchpad_path}': {e}")

def process_database(db_path: str):
    """
    Processes a single database:
    - Identifies all user-defined tables.
    - For each table, extracts input_value entries.
    - Selects the longest input_value.
    - Writes the selected input_value to scratchpad.txt.
    """
    print(f"\n=== Processing Database: {db_path} ===")
    table_names = get_all_table_names(db_path)
    if not table_names:
        print(f"[WARN] No user-defined tables found in '{db_path}'. Skipping.")
        return
    
    actions_found = False  # Flag to check if any input_values are processed

    for table_name in table_names:
        actions = load_input_values(db_path, table_name)
        if not actions:
            print(f"[WARN] No input_value entries found in table '{table_name}'. Skipping.")
            continue
        
        longest_input = get_longest_input(actions)
        
        if not longest_input or not longest_input["input_value"].strip():
            print(f"[INFO] No valid input_value to write for table '{table_name}' in '{db_path}'. Skipping.")
            continue
        
        db_dir = os.path.dirname(db_path)
        
        # Write the longest input to scratchpad.txt
        write_to_scratchpad(db_dir, table_name, longest_input["input_value"])
        actions_found = True
    
    if not actions_found:
        print(f"[INFO] No valid input_value entries were found and written to scratchpad.txt for '{db_path}'.")

def main():
    parser = argparse.ArgumentParser(
        description="Automatically generate 'scratchpad.txt' by selecting the longest input_value from all tables in SQLite databases."
    )
    parser.add_argument(
        "source_dir",
        type=str,
        help="Path to the source directory containing SQLite '.db' files."
    )
    
    args = parser.parse_args()
    source_dir = args.source_dir
    
    if not os.path.isdir(source_dir):
        print(f"[ERROR] Source directory does not exist: {source_dir}")
        sys.exit(1)
    
    # Find all '.db' files in the source directory
    db_files = find_databases(source_dir)
    if not db_files:
        print(f"[INFO] No SQLite '.db' files found in '{source_dir}'.")
        sys.exit(0)
    
    print(f"[INFO] Found {len(db_files)} database file(s) to process.")
    
    for db_path in sorted(db_files):
        process_database(db_path)
    
    print("\n=== Processing Complete ===")

if __name__ == "__main__":
    main()
