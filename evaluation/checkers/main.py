import csv
import os
import sys
import json
import argparse 

from .check_scratchpad_for_correctness import ScratchpadCorrectnessChecker
from .dp_checker import DPComparisonChecker
from .check_db_for_correctness import DBCorrectnessChecker
from .check_assertions_for_correctness import AssertionCorrectnessChecker
from .custom_checker import CustomChecker
from evaluation.utils.parsers import get_dp_codes, remove_apostrophe, remove_prompt_helper
from evaluation.utils.logging import logger

def combine_results(source_dir_1, source_dir_2, source_dir_3, target_dir, output_path, verbose=False): 
    # If source_dir_1 is missing, skip all checkers that use it.
    if not os.path.exists(source_dir_1):
        logger.debug(f"Warning: source_dir_1 ({source_dir_1}) does not exist. Skipping DB, assertion, and scratchpad checks.")
        class DummyChecker:
            pass
        checker_db_correctness = DummyChecker()
        checker_db_correctness.data = {}
        checker_assertion_correctness = DummyChecker()
        checker_assertion_correctness.data = {}
        checker_scratch = DummyChecker()
        checker_scratch.data = {}
        custom_checker = DummyChecker()
        custom_checker.data = {}
    else:
        checker_db_correctness = DBCorrectnessChecker(source_dir_1, target_dir, verbose=verbose)
        checker_db_correctness.run()

        checker_assertion_correctness = AssertionCorrectnessChecker(source_dir_1, target_dir, verbose=verbose)
        checker_assertion_correctness.run()

        checker_scratch = ScratchpadCorrectnessChecker(source_dir_1, target_dir, verbose=verbose)
        checker_scratch.run()

        # TODO Add these results to the resultant CSV
        custom_checker = CustomChecker(target_dir)
        custom_checker.run()

    # For DP checks we require both source_dir_2 and source_dir_3.
    if not (os.path.exists(source_dir_2) and os.path.exists(source_dir_3)):
        logger.debug(f"Warning: One of the source directories for DP check (source_dir_2: {source_dir_2} or source_dir_3: {source_dir_3}) does not exist. Skipping DP check.")
        class DummyCheckerDP:
            pass
        checker_dp = DummyCheckerDP()
        checker_dp.data = {}
    else:
        checker_dp = DPComparisonChecker(source_dir_2, source_dir_3, target_dir, verbose=verbose)
        checker_dp.run()

    # The following processing remains the same; empty .data dictionaries mean that nothing from that check will be included.
    correctness_dict = {}
    for (agent, target_site, target_task), task_results in checker_db_correctness.data.items():
        correctness_dict[(agent, target_site, target_task)] = {
            "correctness_result": f"{task_results['correct']}/{task_results['correct']+task_results['incorrect']} correct"
        }
        if verbose:
            correctness_dict[(agent, target_site, target_task)]["details"] = task_results.get("details", [])

    assertion_dict = {}
    for (agent, target_site, target_task), task_results in checker_assertion_correctness.data.items():
        assertion_dict[(agent, target_site, target_task)] = {
            "assertion_result": f"{task_results['correct']}/{task_results['correct']+task_results['incorrect']} correct"
        }
        if verbose:
            assertion_dict[(agent, target_site, target_task)]["details"] = task_results.get("details", [])

    scratchpad_dict = {}
    for (agent, target_site, target_task), task_results in checker_scratch.data.items():
        total = task_results["correct"] + task_results["incorrect"]
        scratchpad_dict[(agent, target_site, target_task)] = {
            "scratchpad_result": f"{task_results['correct']}/{total} correct"
        }
        if verbose:
            scratchpad_dict[(agent, target_site, target_task)]["details"] = task_results.get("details", [])

    dp_dict = {}
    for key, task_results in checker_dp.data.items():
        grouped = {"fell_for_dp": {}, "did_not_fall_for_dp": {}}
        for group in ["fell_for_dp", "did_not_fall_for_dp"]:
            for dp_name, count in task_results.get(group, {}).items():
                grouped[group][dp_name] = grouped[group].get(dp_name, 0) + count
        dp_dict[key] = {"dp_result": grouped}
        if verbose:
            dp_dict[key]["details"] = task_results.get("details", [])

    all_comparison_keys = set(scratchpad_dict.keys()) | set(dp_dict.keys()) | set(correctness_dict.keys())

    # Step 3: Write a row for each comparison key to the CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline='', encoding="utf-8") as csvfile:
        fieldnames = [
            "agent",
            "dark_pattern",
            "site",
            "task",
            "correctness_result",
            "assertion_result",
            "dp_result",
            "scratchpad_result",
            "details"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for (agent, target_site, target_task) in all_comparison_keys:
            row = {
                "agent": agent,
                "dark_pattern": get_dp_codes(target_site),
                "site": target_site,
                "task": remove_apostrophe(remove_prompt_helper(target_task)),
                "correctness_result": correctness_dict.get((agent, target_site, target_task), {}).get("correctness_result", "N/A"),
                "assertion_result": assertion_dict.get((agent, target_site, target_task), {}).get("assertion_result", "N/A"),
                "dp_result": dp_dict.get((agent, target_site, target_task), {}).get("dp_result", "N/A"),
                "scratchpad_result": scratchpad_dict.get((agent, target_site, target_task), {}).get("scratchpad_result", "N/A"),
            }

            if verbose:
                row_details = {
                    "correctness_details": correctness_dict.get((agent, target_site, target_task), {}).get("details", {}),
                    "assertion_details": assertion_dict.get((agent, target_site, target_task), {}).get("details", {}),
                    "dp_details": dp_dict.get((agent, target_site, target_task), {}).get("details", {}),
                    "scratchpad_details": scratchpad_dict.get((agent, target_site, target_task), {}).get("details", {}),
                }
                row["details"] = json.dumps(row_details)

            writer.writerow(row)

    final_results = []
    for (agent, target_site, target_task) in all_comparison_keys:
        agent_correctness = checker_db_correctness.data.get((agent, target_site, target_task), {"correct": 0, "incorrect": 0})
        agent_assertion = checker_assertion_correctness.data.get((agent, target_site, target_task), {"correct": 0, "incorrect": 0, "N/A": 0})
        agent_scratchpad = checker_scratch.data.get((agent, target_site, target_task), {"correct": 0, "incorrect": 0})
        
        agent_dp_grouped = {"fell_for_dp": {}, "did_not_fall_for_dp": {}}
        for key, res in checker_dp.data.items():
            if key == (agent, target_site, target_task):
                for group in ["fell_for_dp", "did_not_fall_for_dp"]:
                    for dp_name, count in res.get(group, {}).items():
                        agent_dp_grouped[group][dp_name] = agent_dp_grouped[group].get(dp_name, 0) + count

        if verbose:
            db_details = correctness_dict.get((agent, target_site, target_task), {}).get("details", [])
            assertion_details = assertion_dict.get((agent, target_site, target_task), {}).get("details", [])
            scratchpad_details = scratchpad_dict.get((agent, target_site, target_task), {}).get("details", [])
            dp_details = dp_dict.get((agent, target_site, target_task), {}).get("details", [])
            
            def normalize_dp_source(src):
                for token in ["fell_for_dp", "did_not_fall_for_dp"]:
                    if token in src:
                        return src.split(token, 1)[-1]
                return src

            # Build a set of unique (source_directory, target_directory) from non-dp details
            combined_keys = set()
            for d in db_details + assertion_details + scratchpad_details:
                if "source_directory" in d and "target_directory" in d:
                    combined_keys.add((d["source_directory"], d["target_directory"]))
            # Also include normalized keys from dp_details
            for d in dp_details:
                if "source_directory" in d and "target_directory" in d:
                    norm_src = normalize_dp_source(d["source_directory"])
                    combined_keys.add((norm_src, d["target_directory"]))
            
            details_list = []
            for src, tgt in combined_keys:
                run_detail = {
                    "source_directory": src,
                    "target_directory": tgt
                }
                for d in db_details:
                    if d.get("source_directory") == src and d.get("target_directory") == tgt:
                        run_detail["db"] = d.get("result")
                        break
                for a in assertion_details:
                    if a.get("source_directory") == src and a.get("target_directory") == tgt:
                        run_detail["assertion"] = a.get("result")
                        break
                for s in scratchpad_details:
                    if s.get("source_directory") == src and s.get("target_directory") == tgt:
                        run_detail["scratchpad"] = s.get("result")
                        break
                # Group dp details based on normalized source_directory
                grouped_dp = [p for p in dp_details 
                              if normalize_dp_source(p.get("source_directory")) == src 
                              and p.get("target_directory") == tgt]
                
                if grouped_dp:
                    run_detail["source_directories"] = [p.get("source_directory") for p in grouped_dp]
                    run_detail["dp"] = [p.get("result") for p in grouped_dp]
                    run_detail["source_dark_pattern_codes"] = list({code for p in grouped_dp for code in p.get("source_dark_pattern_codes", [])})
                details_list.append(run_detail)
            details = details_list
        else:
            details = {}

        final_results.append({
            "agent": agent,
            "dark_patterns": get_dp_codes(target_site),
            "site": target_site,
            "task": remove_apostrophe(remove_prompt_helper(target_task)),
            "aggregated_result": {
                "db": {
                    "correct": agent_correctness["correct"],
                    "incorrect": agent_correctness["incorrect"]
                },
                "assertion": {
                    "correct": agent_assertion["correct"],
                    "incorrect": agent_assertion["incorrect"],
                },
                "scratchpad": {
                    "correct": agent_scratchpad["correct"],
                    "incorrect": agent_scratchpad["incorrect"]
                },
                "dp": agent_dp_grouped
            },
            "details": details,
        })

    output_json_path = os.path.join(os.path.dirname(output_path), "final_comparison_results.json")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2)
    logger.info(f"JSON report written to {output_json_path}")

def main(args=None):
    parser = argparse.ArgumentParser(
        description="Combine results from various checkers into a single CSV."
    )
    parser.add_argument(
        "source_dir_1",
        type=str,
        help="Path to the first source directory."
    )
    parser.add_argument(
        "source_dir_2",
        type=str,
        help="Path to the second source directory."
    )
    parser.add_argument(
        "source_dir_3",
        type=str,
        help="Path to the third source directory."
    )
    parser.add_argument(
        "target_dir",
        type=str,
        help="Path to the target directory."
    )
    parser.add_argument(
        "output_csv",
        type=str,
        help="Path to the output CSV file."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose mode to include detailed comparison results."
    )
    args = parser.parse_args()
    if not all([args.source_dir_1, args.source_dir_2, args.source_dir_3, args.target_dir, args.output_csv]):
        logger.info("Usage: python final_combiner.py <source1> <source2> <source3> <target> <output_csv> [-v|--verbose]")
        sys.exit(1)

    combine_results(args.source_dir_1, args.source_dir_2, args.source_dir_3, args.target_dir, args.output_csv, args.verbose)

if __name__ == "__main__":
    main()
