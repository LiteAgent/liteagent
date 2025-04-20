import os
import shutil
import sys

def move_and_rename_reasoning_files(root_directory):
    """
    Recursively searches for 'reasoning' directories under root_directory.
    If found, it looks for any files ending with '_reasoning.txt', renames them to
    'scratchpad.txt', moves them one directory up, and then deletes the 'reasoning'
    directory.
    """
    # Walk the directory tree
    for current_path, dirs, files in os.walk(root_directory):
        # Check if "reasoning" is one of the subdirectories
        if "reasoning" in dirs:
            reasoning_path = os.path.join(current_path, "reasoning")
            
            # Look for files ending in '_reasoning.txt' inside that directory
            for filename in os.listdir(reasoning_path):
                if filename.endswith("_reasoning.txt"):
                    old_file_path = os.path.join(reasoning_path, filename)
                    
                    # New file path: same directory as reasoning_path's parent (current_path),
                    # but rename it to scratchpad.txt
                    new_file_path = os.path.join(current_path, "scratchpad.txt")
                    
                    print(f"Renaming and moving {old_file_path} -> {new_file_path}")
                    shutil.move(old_file_path, new_file_path)

            # After moving all files, remove the entire reasoning directory
            print(f"Removing directory: {reasoning_path}")
            shutil.rmtree(reasoning_path)

if __name__ == "__main__":
    # Usage: python script.py /path/to/directory
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <directory_path>")
        sys.exit(1)
    
    dir_path = sys.argv[1]
    if not os.path.isdir(dir_path):
        print(f"Error: {dir_path} is not a valid directory.")
        sys.exit(1)
    
    move_and_rename_reasoning_files(dir_path)
