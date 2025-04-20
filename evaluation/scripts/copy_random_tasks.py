#!/usr/bin/env python3

import os
import sys
import re
import random
import shutil

def copy_random_tasks_from_each_category(input_dir: str, output_dir: str, tasks_per_category: int = 10):
    """
    For each <agent>/<category> directory in input_dir, randomly select up to
    tasks_per_category subdirectories ending in '_<count>' and copy them (with their
    contents) to output_dir, preserving relative structure.
    """

    # Regex to match directory names ending with an underscore + digits (e.g., '..._2')
    pattern = re.compile(r'.*_\d+$')

    # 1) Iterate over everything in input_dir to find "agent" folders
    for agent_name in os.listdir(input_dir):
        agent_path = os.path.join(input_dir, agent_name)
        # Skip if not a directory (e.g., ignore files)
        if not os.path.isdir(agent_path):
            continue

        # 2) For each agent, iterate over subfolders to find "category" folders
        for category_name in os.listdir(agent_path):
            category_path = os.path.join(agent_path, category_name)
            # Skip if not a directory
            if not os.path.isdir(category_path):
                continue

            # 3) Gather all subdirectories that match the task pattern (.*_\d+$)
            task_dirs = []
            for candidate in os.listdir(category_path):
                candidate_path = os.path.join(category_path, candidate)
                if os.path.isdir(candidate_path) and pattern.match(candidate):
                    task_dirs.append(candidate_path)

            if not task_dirs:
                # No task directories found in this category
                continue

            # 4) Randomly pick up to `tasks_per_category`
            if len(task_dirs) > tasks_per_category:
                chosen_subdirs = random.sample(task_dirs, tasks_per_category)
            else:
                chosen_subdirs = task_dirs

            print(f"\nAgent: {agent_name} | Category: {category_name}")
            print(f"Found {len(task_dirs)} matching tasks, copying {len(chosen_subdirs)}...\n")

            # 5) Copy each chosen subdirectory to the output, preserving relative paths
            for subdir_path in chosen_subdirs:
                rel_path = os.path.relpath(subdir_path, start=input_dir)
                dest_path = os.path.join(output_dir, rel_path)

                print(f"  Copying: {subdir_path} -> {dest_path}")
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                # If it already exists, remove or handle differently
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)

                shutil.copytree(subdir_path, dest_path)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input_directory> <output_directory> [tasks_per_category=10]")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    tasks_per_category = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    # Optional: set a random seed for reproducible results
    # random.seed(0)

    copy_random_tasks_from_each_category(input_dir, output_dir, tasks_per_category)


if __name__ == "__main__":
    main()
