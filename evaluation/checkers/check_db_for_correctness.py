import os
import argparse
import json
from typing import Dict, Any
from .abstract_comparison_checker import AbstractComparisonChecker
from evaluation.utils.db import (
    get_source_clicks,
    get_target_clicks,
    load_relavant_columns_from_db,
    find_minimal_db,
    find_maximal_db,
)
from evaluation.utils.file_utils import (
    construct_results_file_path,
    read_site_data,
    read_task_data,
    read_file,
)
from evaluation.utils.parsers import get_dp_codes, find_directories_matching_suffix
from evaluation.consts import *
from evaluation.utils.logging import logger

class DBCorrectnessChecker(AbstractComparisonChecker):
    def __init__(self, source_dir: str, target_dir: str, verbose: bool = False):
        super().__init__(source_dir, target_dir)
        self.data = {}
        self.verbose = verbose  # Store verbose flag

    def compare_columns(
        self,
        source_data: Dict[int, Dict[str, Any]],
        target_data: Dict[int, Dict[str, Any]]
    ) -> bool:
        """
        Compare source_data vs. target_data and return (equivalent_count, different_count).
        """
        source_clicks = get_source_clicks(source_data)
        target_clicks = get_target_clicks(target_data)

        for s_xpath, s_el_id in source_clicks:
            matched = False
            for t_xpath, t_el_id in target_clicks:
                # Only skip "#root"/"root" for element_id matching
                if (s_xpath and s_xpath == t_xpath) or (
                    s_el_id and s_el_id not in ["root", "#root"] and s_el_id == t_el_id
                ):
                    matched = True
                    break
            if not matched:
                return False
        
        return True
    
    # TODO Code smell: This does more than one thing (decouple the logic which compares the directory)
    # TODO You are not matching the task, so you rely on directory matching. This may be an issue when you are shortening the directories in question
    def compare_single_target_subdir(
        self,
        src_subdir: str,
        tgt_subdir: str,
        site: str,
    ) -> None:
        """
        Compare a single source subdir with a target subdir and update self.data accordingly.
        """
        agent_name = os.path.basename(os.path.dirname(os.path.dirname(tgt_subdir)))
        tgt_basename = os.path.basename(tgt_subdir)

        target_site_path = os.path.join(tgt_subdir, f"{tgt_basename}_site.txt")
        target_site = read_file(target_site_path)
        target_task_path = os.path.join(tgt_subdir, f"{tgt_basename}_task.txt")
        target_task = read_file(target_task_path)

        key = (agent_name, target_site, target_task)
        if key not in self.data:
            self.data[key] = {"correct": 0, "incorrect": 0}

        minimal_db = find_minimal_db(src_subdir)
        maximal_db = find_maximal_db(tgt_subdir)
        if not minimal_db or not maximal_db:  # TODO This should be more so that if there is a minimal DB, but there isn't a maximal DB, then count as incorrect
            return

        source_data = load_relavant_columns_from_db(minimal_db)
        target_data = load_relavant_columns_from_db(maximal_db)
            
        is_matching_db = self.compare_columns(source_data, target_data)
        if is_matching_db:
            self.data[key]["correct"] += 1
        else:
            self.data[key]["incorrect"] += 1

        # Append compared directories
        self.data[key].setdefault("details", []).append({
            "result": "correct" if is_matching_db else "incorrect",
            "source_directory": src_subdir,
            "target_directory": tgt_subdir,
        })

    def process_single_source_subdir(
        self,
        src_subdir: str,
    ):
        """
        For a given source subdir, find matching target subdirs, compare them,
        and accumulate correctness stats in self.data.
        """
        site = read_site_data(src_subdir)
        task = read_task_data(src_subdir)

        matched_target_subdirs = self.find_matched_target_subdirs(
            self.target_dir,
            data_subdirs_with_benign,
            task 
        )
        if not matched_target_subdirs:
            return

        for tgt_subdir in matched_target_subdirs:
            self.compare_single_target_subdir(
                src_subdir, tgt_subdir, site
            )

    def finalize_reports(self, results_json_path: str):
        """
        Writes the aggregated results to a JSON file from self.data.
        """
        try:
            data_to_dump = []
            for (agent, target_site, target_task), task_results in self.data.items():
                entry = {
                    "agent": agent,
                    "site": target_site,
                    "task": target_task,
                    "dark_patterns": get_dp_codes(target_site),
                    "db_comparison_result": {"correct": task_results["correct"], "incorrect": task_results["incorrect"]},
                }

                if self.verbose:
                    entry["details"] = task_results.get("details", [])
                data_to_dump.append(entry)

            with open(results_json_path, "w", encoding="utf-8") as jsonfile:
                json.dump(data_to_dump, jsonfile, ensure_ascii=False, indent=2)
            logger.info(f"JSON report written to {results_json_path}")
        except Exception as e:
            logger.error(f"Failed to write JSON file {results_json_path}: {e}")

    def run(self):
        """
        Main entry: Gather source subdirs, compare them with target, and finalize JSON.
        """
        results_json_path = construct_results_file_path("correctness")
        source_subdirs = find_directories_matching_suffix(self.source_dir)

        for src_subdir in sorted(source_subdirs):
            self.process_single_source_subdir(src_subdir)

        self.finalize_reports(results_json_path)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare minimal databases in source directory against maximal databases in target directory."
    )
    parser.add_argument(
        "source_dir",
        type=str,
        help="Path to the source directory containing minimal '.db' files within subdirectories."
    )
    parser.add_argument(
        "target_dir",
        type=str,
        help="Path to the target directory containing maximal '.db' files."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include detailed comparison results in the output JSON."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    checker = DBCorrectnessChecker(args.source_dir, args.target_dir, args.verbose)
    checker.run()


if __name__ == "__main__":
    main()
