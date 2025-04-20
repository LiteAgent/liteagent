import os
import argparse
import sys
import shutil
from evaluation.utils.logging import logger

def prompt_yes_no(prompt: str) -> bool:
    """
    Prompt the user with a yes/no question and return True for 'yes' and False for 'no'.
    """
    while True:
        response = input(f"{prompt} [y/n]: ").strip().lower()
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

def get_user_inputs() -> list:
    """
    Prompt the user to enter multiple lines of text.
    The user can type 'DONE' (case-insensitive) on a new line to finish.
    Returns a list of entered lines.
    """
    print("\nEnter the content you wish to include in 'scratchpad_minimal.txt'.")
    print("Type 'DONE' on a new line when you are finished.\n")
    inputs = []
    while True:
        try:
            line = input()
            if line.strip().upper() == 'DONE':
                break
            inputs.append(line)
        except EOFError:
            # Handle end-of-file (e.g., user presses Ctrl+D)
            break
    return inputs

def backup_file(file_path: str):
    """
    Creates a backup of the specified file by copying it with a '.bak' extension.
    """
    backup_path = file_path + ".bak"
    try:
        shutil.copy2(file_path, backup_path)
        logger.info("Backup created at '{backup_path}'.")
    except Exception as e:
        logger.error("Failed to create backup for '{file_path}': {e}")

def write_to_file(file_path: str, contents: list, mode: str):
    """
    Write the contents to the specified file.
    Mode can be 'w' for overwrite or 'a' for append.
    """
    try:
        with open(file_path, mode, encoding='utf-8') as f:
            for line in contents:
                f.write(line + '\n')
        action = "Appended to" if mode == 'a' else "Written to"
        logger.info(f"{action} '{file_path}' successfully.")
    except Exception as e:
        logger.error("Failed to write to '{file_path}': {e}")

def process_directory(dir_path: str, mode: str, skip_existing: bool):
    """
    Process a single directory:
    - Check for '.db' files.
    - If present, prompt user to create/update 'scratchpad_minimal.txt'.
    - If yes, get user inputs and write to the file.
    """
    # Check if the directory contains any '.db' file
    has_db = any(filename.endswith('.db') for filename in os.listdir(dir_path))
    if not has_db:
        return  # Skip directories without '.db' files

    logger.debug(f"\n--- Directory: {dir_path} ---")
    scratchpad_filename = "scratchpad_minimal.txt"
    scratchpad_path = os.path.join(dir_path, scratchpad_filename)
    
    if os.path.isfile(scratchpad_path):
        logger.info("'{scratchpad_filename}' already exists in '{dir_path}'.")

    # If skipping existing files and the file exists, skip processing
    if skip_existing and os.path.isfile(scratchpad_path):
        logger.info("'{scratchpad_filename}' already exists and '--skip-existing' is enabled. Skipping.")
        return
    
    create_scratchpad = prompt_yes_no(f"Do you want to create/update '{scratchpad_filename}' in this directory?")
    if not create_scratchpad:
        logger.info("Skipping '{scratchpad_filename}' in '{dir_path}'.")
        return
    
    user_contents = get_user_inputs()
    if not user_contents:
        logger.info("No content entered. Scratchpad not created/updated.")
        return
    
    # Determine file mode
    file_mode = 'w' if mode == 'overwrite' else 'a'
    
    # If overwriting and file exists, confirm overwrite and backup
    if mode == 'overwrite' and os.path.isfile(scratchpad_path):
        overwrite = prompt_yes_no(f"'{scratchpad_filename}' already exists. Do you want to overwrite it?")
        if not overwrite:
            append = prompt_yes_no(f"Do you want to append to the existing '{scratchpad_filename}'?")
            if append:
                file_mode = 'a'
            else:
                logger.info("Skipping writing to scratchpad.")
                return
        else:
            # Create a backup before overwriting
            backup_file(scratchpad_path)
    
    # Write to scratchpad file
    write_to_file(scratchpad_path, user_contents, file_mode)

def traverse_and_process(root_dir: str, subdir: str, mode: str, skip_existing: bool):
    """
    Traverse the root directory (and optional subdirectory) and process eligible directories.
    """
    directories_with_db = []
    if subdir:
        target_dir = os.path.join(root_dir, subdir)
        if not os.path.isdir(target_dir):
            logger.error("The specified subdirectory does not exist within '{root_dir}': {subdir}")
            sys.exit(1)
        logger.info("Processing subdirectory: {target_dir}")
        # Traverse only the specified subdirectory
        for dirpath, dirnames, filenames in os.walk(target_dir):
            if any(filename.endswith('.db') for filename in filenames):
                directories_with_db.append(dirpath)
    else:
        # Traverse the entire root directory and its subdirectories
        for dirpath, dirnames, filenames in os.walk(root_dir):
            if any(filename.endswith('.db') for filename in filenames):
                directories_with_db.append(dirpath)
    total = len(directories_with_db)
    for i, dp in enumerate(directories_with_db):
        process_directory(dp, mode, skip_existing)
        logger.info("{total - i - 1} directories left to process.")

def main():
    parser = argparse.ArgumentParser(
        description="Create or update 'scratchpad_minimal.txt' files in directories containing '.db' files based on user input."
    )
    parser.add_argument(
        "root_dir",
        type=str,
        help="Path to the root directory to traverse."
    )
    parser.add_argument(
        "--subdir",
        type=str,
        default=None,
        help="Optional subdirectory within the root directory to traverse."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=['overwrite', 'append'],
        default='overwrite',
        help="Default file handling mode: 'overwrite' to replace existing files, 'append' to add to them. Defaults to 'overwrite'."
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip creating/updating 'scratchpad_minimal.txt' if it already exists."
    )
    
    args = parser.parse_args()
    root_dir = args.root_dir
    subdir = args.subdir
    mode = args.mode
    skip_existing = args.skip_existing
    
    if not os.path.isdir(root_dir):
        logger.error("The specified root directory does not exist: {root_dir}")
        sys.exit(1)
    
    # Determine the target directory based on the presence of --subdir
    if subdir:
        target_dir = os.path.join(root_dir, subdir)
        if not os.path.isdir(target_dir):
            logger.error("The specified subdirectory does not exist within '{root_dir}': {subdir}")
            sys.exit(1)
        logger.debug(f"\n=== Scratchpad Minimal Creator ===")
        logger.debug(f"Root Directory: {root_dir}")
        logger.debug(f"Subdirectory: {subdir}")
    else:
        logger.debug(f"\n=== Scratchpad Minimal Creator ===")
        logger.debug(f"Root Directory: {root_dir}")
    
    logger.debug(f"Default File Mode: {mode}")
    logger.debug(f"Skip Existing Files: {'Enabled' if skip_existing else 'Disabled'}")
    print("===================================\n")
    
    traverse_and_process(root_dir, subdir, mode, skip_existing)
    
    logger.info("\n=== Processing Complete ===\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nScript terminated by user.")
        sys.exit(0)
