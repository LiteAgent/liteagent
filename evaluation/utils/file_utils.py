import os
from pathlib import Path
from evaluation.utils.logging import logger

def read_file(file_path: str) -> str:
    """
    Reads the content of a text file and returns it as a string.
    Returns an empty string if the file does not exist or is empty.
    """
    if not os.path.isfile(file_path):
        logger.warning("File not found: {file_path}")
        return ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content
    except Exception as e:
        logger.error("Failed to read file {file_path}: {e}")
        return ""

def construct_results_file_path(eval_type: str):
    os.makedirs("numbers", exist_ok=True)
    return os.path.join("numbers", f"{eval_type}_comparison_results.json")

def read_site_data(dir: Path) -> str:
    site_txt_filename = f"{os.path.basename(dir)}_site.txt"
    site_txt_path = os.path.join(dir, site_txt_filename)
    site = read_file(site_txt_path)
    return site

def read_task_data(dir: Path) -> str:
    task_txt_filename = f"{os.path.basename(dir)}_task.txt"
    task_txt_path = os.path.join(dir, task_txt_filename)
    task = read_file(task_txt_path)
    return task

# Brandon helpers
def list_folders_in_directory(directory):
    agents = []
    batch = []
    runs = []
    try:
        # Loop through each item in the directory
        for item in os.listdir(directory):
            # Construct the full path of the item
            item_path = os.path.join(directory, item)
            # Check if the item is a folder
            if os.path.isdir(item_path):
                agents.append((item,item_path))
            
        for agent in agents:
            for item in os.listdir(agent[1]):
                item_path = os.path.join(agent[1], item)
                if os.path.isdir(item_path):
                    batch.append(item_path)

        for folder in batch:
            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                if os.path.isdir(item_path) and item != 'payloads' and item != 'cookies':
                    runs.append(item_path)

    except FileNotFoundError:
        print(f"The directory '{directory}' does not exist.")
    except PermissionError:
        print(f"Permission denied to access '{directory}'.")
    
    return agents, runs

def read_file_endswith(folder_path, ending, just_file_name = False):
    try:
        # Iterate through files in the folder
        for filename in os.listdir(folder_path):
            # Check if the file ends with ending
            if filename.endswith(ending):
                # Construct the full file path
                file_path = os.path.join(folder_path, filename)

                if just_file_name:
                    return file_path
                
                # Open and read the file
                with open(file_path, 'r') as file:
                    content = file.read()
                    return file_path, content
    
    except FileNotFoundError:
        print(f"The folder '{folder_path}' does not exist.")
    except PermissionError:
        print(f"Permission denied to access '{folder_path}'.")

    return '-1'
