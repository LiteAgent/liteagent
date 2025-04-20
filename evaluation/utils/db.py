import sqlite3
from typing import Dict
import os
from evaluation.utils.logging import logger

def get_source_clicks(source_data: Dict[int, Dict[str, any]]): 
    return [(row.get('xpath'), row.get('element_id')) for row in source_data.values() if row.get('event_type') == 'click'] 

def get_target_clicks(target_data: Dict[int, Dict[str, any]]):
    return [(row.get('xpath'), row.get('element_id')) for row in target_data.values() if row.get('event_type') == 'click']

def load_relavant_columns_from_db(db_path: str) -> Dict[int, Dict[str, any]]:
    """
    Connects to the SQLite database at db_path and retrieves all rows with their columns.
    Returns a dictionary with 'id' as keys and other columns as values, excluding specified columns.
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
        logger.warning("No user-defined tables found in {db_path}.")
        conn.close()
        return {}
    
    table_name = row[0]
    
    try:
        cursor.execute(f"SELECT * FROM \"{table_name}\"")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        ignored_columns = {'url', 'additional_info', 'time_since_last_action'}
        data = {
            row[0]: {
                col: val 
                for col, val in zip(columns[1:], row[1:]) 
                if col not in ignored_columns
            } 
            for row in rows
        }
    except sqlite3.Error as e:
        logger.error("Failed to retrieve data from table '{table_name}' in {db_path}: {e}")
        data = {}
    
    conn.close()
    return data

def find_minimal_db(subdir_path: str) -> str:
    """
    Finds the minimal db in the given subdirectory.
    Assumes minimal dbs have filenames ending with '_minimal.db'.
    Returns the full path to the minimal db or None if not found.
    """
    for filename in os.listdir(subdir_path):
        if filename.endswith("_minimal.db"):
            return os.path.join(subdir_path, filename)
    return None

def find_maximal_db(subdir_path: str) -> str:
    """
    Finds the maximal db in the given subdirectory.
    Assumes maximal dbs have filenames ending with '.db' but not '_minimal.db'.
    Returns the full path to the maximal db or None if not found.
    """
    for filename in os.listdir(subdir_path):
        if filename.endswith(".db") and not filename.endswith("_minimal.db"):
            return os.path.join(subdir_path, filename)
    return None

# Brandon helpers
def is_db_empty(db_file):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Check if there are any tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            return True
        
        # Check if the first (and only) table is empty
        table_name = tables[0][0]
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        row_count = cursor.fetchone()[0]
        
        return row_count == 0
    
    except sqlite3.Error:
        return True
    finally:
        if conn:
            conn.close()