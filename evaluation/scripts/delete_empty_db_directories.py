import os
import sqlite3
import shutil

def is_empty_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        # If no tables, consider empty
        if len(tables) == 0:
            return True
        # Check row count of the single table
        table_name = tables[0][0]
        cursor.execute(f"SELECT COUNT(1) FROM {table_name}")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0
    except sqlite3.Error:
        # If invalid or missing DB, consider empty
        return True

def delete_dirs_with_empty_db(root_dir):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.db'):
                db_path = os.path.join(dirpath, filename)
                if is_empty_db(db_path):
                    print(f"Deleting directory: {dirpath}")
                    shutil.rmtree(dirpath)
                    break  # Move to next directory after deletion

if __name__ == "__main__":
    root_directory = '/home/hue/Desktop/phd/agi/data/db'
    delete_dirs_with_empty_db(root_directory)
