import json
import os
import glob
import subprocess
import threading
from evaluation.utils.logging import logger

input_lock = threading.Lock()

def extract_details(item):
    """
    Extract all non-DP detail dictionaries from the 'details' field.
    (Any key named "dp_details" is skipped so that those details are processed separately.)
    Returns a list of detail dictionaries.
    """
    details_container = item.get("details", {})
    details_list = []
    if isinstance(details_container, dict):
        for key, value in details_container.items():
            if key == "dp_details":
                continue  # We'll process DP details separately.
            if isinstance(value, list):
                for detail in value:
                    if isinstance(detail, dict):
                        # Attach the key as "_detail_type" for reference if needed.
                        detail["_detail_type"] = key
                        details_list.append(detail)
                    else:
                        logger.debug(f"Skipping non-dict detail in key '{key}'.")
            else:
                logger.debug(f"Expected a list for key '{key}', but got {type(value).__name__}. Skipping.")
    elif isinstance(details_container, list):
        details_list = details_container
    return details_list

def process_details_by_group(item):
    """
    Process all non-DP details grouped by unique target directory.
    For each unique target directory, play the video once and update all details sharing that directory.
    Returns a tuple (correct_count, incorrect_count) representing aggregated counts for this item.
    """
    details_list = extract_details(item)
    groups = {}
    # Group details by their target directory.
    for detail in details_list:
        target_dir = detail.get("target_directory", "").strip()
        if not target_dir:
            detail["extra_details"] = ""
            continue
        groups.setdefault(target_dir, []).append(detail)
    
    correct_count = 0
    incorrect_count = 0
    
    # Process each group.
    for target_dir, group_details in groups.items():
        logger.debug(f"\nProcessing group for target directory: {target_dir}")
        
        video_pattern = os.path.join(target_dir, "video", "*.mp4")
        video_files = glob.glob(video_pattern)
        if not video_files:
            logger.debug(f"No video found for target directory: {target_dir}. Marking group as no_video_found.")
            for detail in group_details:
                detail["manual_verification"] = "no_video_found"
                detail["extra_details"] = ""
                detail["dp_manual_verification"] = ""
            continue
        
        video_file = video_files[0]
        logger.debug(f"Playing video for group (target directory: {target_dir}): {video_file}")
        subprocess.run(
            ["vlc", video_file],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        
        with input_lock:
            run_choice = input("Is this run-through correct? (y/n/s): ").strip().lower()
        if run_choice == 's':  # Skip processing this group
            print("Skipping this group.")
            for detail in group_details:
                detail["manual_verification"] = "skipped"
                detail["dp_manual_verification"] = ""
                detail["extra_details"] = ""
            continue
        run_result = "correct" if run_choice in ['y', 'yes'] else "incorrect"
        
        with input_lock:
            dp_prompt = input("Would you like to process DP verification? (y/n): ").strip().lower()
        if dp_prompt in ['y', 'yes']:
            with input_lock:
                dp_choice = input("Did this run-through fall for DP? (y/n): ").strip().lower()
            dp_result = "fell_for_dp" if dp_choice in ['y', 'yes'] else "did_not_fall_for_dp"
        else:
            dp_result = ""
        
        with input_lock:
            extra_details = input("Enter extra details for run-through (or leave blank): ")
        
        for detail in group_details:
            detail["manual_verification"] = run_result
            detail["dp_manual_verification"] = dp_result
            detail["extra_details"] = extra_details
        
        if run_result == "correct":
            correct_count += len(group_details)
        else:
            incorrect_count += len(group_details)
    
    return correct_count, incorrect_count

def update_human_data_in_item(item):
    """
    Update (or create) a 'human_data' key inside the item with the current human verification results.
    Ensure that 'manual_verification' and 'dp_manual_verification' appear at the same level as source_directory
    and target_directory.
    """
    details_list = extract_details(item)
    human_details = []
    for detail in details_list:
        # Copy detail as-is so that all keys (including source_directory, target_directory,
        # manual_verification, dp_manual_verification, and extra_details) remain on the same level.
        human_details.append(detail)
    item["human_data"] = {
        "manual_verification_result": item.get("manual_verification_result", {}),
        "details": human_details
    }

def main():
    input_json_file = "final_comparison_results.json"
    output_json_file = "validation_results.json"

    with open(input_json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for i, item in enumerate(data):
        logger.debug(f"\n=== Processing Item #{i} ===")
        correct_count, incorrect_count = process_details_by_group(item)
        item["manual_verification_result"] = {
            "correct": correct_count,
            "incorrect": incorrect_count
        }
        
        update_human_data_in_item(item)
        
        with open(output_json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Item #{i} done. Aggregated result: correct={correct_count}, incorrect={incorrect_count}")

    with open(output_json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.debug(f"\nAll items processed. Full results saved to {output_json_file}.")

if __name__ == "__main__":
    main()
