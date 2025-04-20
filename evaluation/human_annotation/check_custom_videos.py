import json
import os
import glob
import subprocess
import threading
from evaluation.utils.logging import logger

# TODO Merge together the checking of videos with the checking of custom videos (both of which require first merging the two distinct codebases)
input_lock = threading.Lock()

def main():
    input_json_file = "/home/hue/Desktop/phd/agi/numbers/custom_comparison_results.json"
    output_json_file = "/home/hue/Desktop/phd/agi/numbers/custom_validation_results.json"

    with open(input_json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for i, item in enumerate(data):
        logger.debug(f"\n=== Processing Item #{i} ===")
        run_id = item.get("run_id", "").strip()
        video_pattern = os.path.join(run_id, "video", "*.mp4")
        video_files = glob.glob(video_pattern)
        if not video_files:
            logger.debug(f"No video found for item #{i} using pattern: {video_pattern}")
            item["manual_verification"] = "no_video_found"
            item["dp_manual_verification"] = ""
            item["extra_details"] = ""
        else:
            video_file = video_files[0]
            logger.debug(f"Playing video for item #{i}: {video_file}")
            subprocess.run(
                ["vlc", video_file],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            with input_lock:
                run_choice = input("Is this run-through correct? (y/n/s): ").strip().lower()
            if run_choice == 's':
                print("Skipping this item.")
                item["manual_verification"] = "skipped"
                item["dp_manual_verification"] = ""
                item["extra_details"] = ""
            else:
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
                item["manual_verification"] = run_result
                item["dp_manual_verification"] = dp_result
                item["extra_details"] = extra_details

        logger.debug(f"Item #{i} updated with: manual_verification={item.get('manual_verification')}")
    
    with open(output_json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.debug(f"\nAll items processed. Results saved to {output_json_file}.")

if __name__ == "__main__":
    main()
