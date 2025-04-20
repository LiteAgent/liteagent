import os
import concurrent.futures
import argparse
import subprocess
import json
import concurrent.futures
from .abstract_comparison_checker import AbstractComparisonChecker
from evaluation.utils.file_utils import (
    construct_results_file_path,
    read_site_data,
    read_task_data,
    read_file,
)
from evaluation.utils.parsers import get_dp_codes, find_directories_matching_suffix
from evaluation.consts import *
from evaluation.utils.logging import logger

class AssertionCorrectnessChecker(AbstractComparisonChecker):
    def __init__(self, source_dir: str, target_dir: str, verbose: bool = False):
        super().__init__(source_dir, target_dir)
        self.data = {}
        self.verbose = verbose

    def check_assertions(self, dir_to_check: str) -> int:
        # Adjust this pattern to match your files
        for filename in os.listdir(dir_to_check):
            if filename.startswith('test_') and filename.endswith('_merged.py'):
                full_file_path = os.path.join(dir_to_check, filename)
                with open(full_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for a Playwright 'expect('
                if 'expect(' not in content:  # Either an incorrect merge ocurred, or there is no script to merge afterward
                    return -1
                else:
                    # Run pytest
                    cmd = ["pytest", full_file_path, "--maxfail=1", "-q"]
                    try:
                        subprocess.check_call(cmd)
                        return 1
                    except subprocess.CalledProcessError:
                        return 0

        return -1

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

        assertion_correct = self.check_assertions(tgt_subdir) 
        if assertion_correct == 1:
            self.data[key]["correct"] += 1
        elif assertion_correct == 0:
            self.data[key]["incorrect"] += 1
        else:
            return
        
        self.data[key].setdefault("details", []).append({
            "result": "correct" if assertion_correct == 1 else "incorrect",
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
            self.compare_single_target_subdir(src_subdir, tgt_subdir, site)

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
                    "assertion_comparison_result": {"correct": task_results["correct"], "incorrect": task_results["incorrect"]},
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
        results_json_path = construct_results_file_path("assertion")
        source_subdirs = find_directories_matching_suffix(self.source_dir)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for src_subdir in sorted(source_subdirs):
                futures.append(executor.submit(self.process_single_source_subdir, src_subdir))
            for future in futures:
                future.result()

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
    checker = AssertionCorrectnessChecker(args.source_dir, args.target_dir, args.verbose)
    checker.run()


if __name__ == "__main__":
    main()
