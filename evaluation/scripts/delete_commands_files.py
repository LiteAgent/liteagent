import os

def delete_command_files(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('_commands.py'):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")

if __name__ == "__main__":
    root_directory = '/home/hue/Desktop/phd/agi/data/db'
    delete_command_files(root_directory)