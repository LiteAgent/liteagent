"""
CustomChecker Module

This module provides the CustomChecker class, which is used to validate and analyze
data from a directory of runs. The CustomChecker class performs various checks on
task correctness and dark pattern susceptibility using data from SQLite databases
and other files in the specified directory, customized based on the task and site.

Classes:
    CustomChecker: A class to perform validation and analysis on run data.

Usage:
    Run this module as a script with the directory path as an argument to validate
    the runs in the specified directory.

Example:
    python custom_checker.py /path/to/directory
"""

import argparse
import os
import sqlite3
import json
from evaluation.dp_checks import DP_CHECKS
from evaluation.task_checks import TASK_CHECKS
from evaluation.utils.db import is_db_empty
from evaluation.utils.file_utils import list_folders_in_directory, read_file_endswith, construct_results_file_path
from evaluation.utils.parsers import get_dp_from_url, get_site_type
from evaluation.utils.logging import logger

class CustomChecker:
    def __init__(self, directory_path: str):
        self.directory_path = directory_path
        self.data = {
            'agent': [],
            'site': [],
            'prompt': [],
            'dp1': [],
            'dp2': [],
            'dp3': [],
            'dp4': [],
            'run_id': [],
            'db_file': [],
            'check_log': [],
            'dp1_log':[],
            'dp2_log':[],
            'dp3_log':[],
            'dp4_log':[],
            'task_correct': [],
            'dp1_susceptibility': [],
            'dp2_susceptibility': [],
            'dp3_susceptibility': [],
            'dp4_susceptibility': []
        }

    def check_task_correctness(self, site_type, prompt, file_paths):
        if site_type is None:
            logger.error("Skipped check: site_type is None")
            return None, ["Skipped check: site_type is None"]
        if site_type not in TASK_CHECKS:
            logger.error(f"Skipped check: site_type '{site_type}' not found in TASK_CHECKS")
            return None, [f"Skipped check: site_type '{site_type}' not found"]
        if prompt not in TASK_CHECKS[site_type]:
            logger.error(f"Skipped check: prompt '{prompt}' not found for site_type '{site_type}'")
            return None, [f"Skipped check: prompt '{prompt}' not found"]
        checks = TASK_CHECKS[site_type][prompt]["checks"]
        correct = True
        check_log = []
        for check in checks:
            try:
                check_function = check['type']
                params = list(check['check'].values())
                params = [file_paths] + params
                result = getattr(self, check_function)(*params)
            except Exception as e:
                logger.error(f"Error in check {check['type']}: {e}")
                result = False
            correct = correct and result
            check_log.append(f"Result of {check['type'].value}, {[check['check'][c] for c in check['check']]}: {result}")
        return correct, check_log

    def check_dp_correctness(self, site_type, dp_type, file_paths):
        if site_type is None:
            logger.error("Skipped check: site_type is None")
            return None, ["Skipped check: site_type is None"]
        if dp_type is None:
            logger.error("Skipped check: dp_type is None")
            return None, ["Skipped check: dp_type is None"]
        if site_type not in DP_CHECKS:
            logger.error(f"Skipped check: site_type '{site_type}' not found in DP_CHECKS")
            return None, [f"Skipped check: site_type '{site_type}' not found"]
        if dp_type not in DP_CHECKS[site_type]:
            logger.error(f"Skipped check: dp_type '{dp_type}' not found for site_type '{site_type}'")
            return None, [f"Skipped check: dp_type '{dp_type}' not found"]
        checks = DP_CHECKS[site_type][dp_type]["checks"]
        correct = True
        check_log = []
        for check in checks:
            try:
                check_function = check['type']
                params = list(check['check'].values())
                params = [file_paths] + params
                result = getattr(self, check_function)(*params)
            except Exception as e:
                logger.error(f"Error in check {check['type']}: {e}")
                result = False
            correct = correct and result
            check_log.append(f"Result of {check['type'].value}, {[check['check'][c] for c in check['check']]}: {result}")
        return correct, check_log

    def db_has_x_instances_click_element_id(self, file_paths, element_id_substring, num_instances, invert=False):
        db_path = file_paths[0]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_name = cursor.fetchone()[0]
        query = f"""
            SELECT *
            FROM [{table_name}]
            WHERE event_type = ? AND element_id LIKE ? ESCAPE '\\'
            """
        cursor.execute(query, ('click', f'{element_id_substring}%'))
        rows = cursor.fetchall()
        conn.close()
        result = len(rows) == num_instances
        if invert:
            return not result
        else:
            return result

    def db_exact_match_click_element_id(self, file_paths, element_id, invert=False):
        db_path = file_paths[0]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_name = cursor.fetchone()[0]
        query = f"""
            SELECT *
            FROM [{table_name}]
            WHERE event_type = ? AND element_id = ?
            """
        cursor.execute(query, ('click', element_id))
        rows = cursor.fetchall()
        conn.close()
        result = len(rows) > 0
        if invert:
            return not result
        else:
            return result
    
    def db_at_least_one_match_element_ids(self, file_paths, element_ids, invert=False):
        result = False
        for element_id in element_ids:
            result = result or (self.db_exact_match_click_element_id(file_paths, element_id))
        if invert:
            return not result
        else:
            return result

    def db_exact_match_click_xpath(self, file_paths, xpath, invert=False):
        db_path = file_paths[0]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_name = cursor.fetchone()[0]
        query = f"""
            SELECT *
            FROM [{table_name}]
            WHERE event_type = ? AND xpath = ?
            """
        cursor.execute(query, ('click', xpath))
        rows = cursor.fetchall()
        conn.close()
        result = len(rows) > 0
        if invert:
            return not result
        else:
            return result

    def db_at_least_one_match_xpaths(self, file_paths, xpaths, invert=False):
        result = False
        for xpath in xpaths:
            result = result or (self.db_exact_match_click_xpath(file_paths, xpath))
        if invert:
            return not result
        else:
            return result
    
    def db_all_element_ids_match(self, file_paths, element_ids, invert=False):
        result = False
        for element_id in element_ids:
            result = result and (self.db_exact_match_click_element_id(file_paths, element_id))
        if invert:
            return not result
        else:
            return result
    
    def db_all_xpaths_match(self, file_paths, xpaths, invert=False):
        result = False
        for xpath in xpaths:
            result = result and (self.db_exact_match_click_xpath(file_paths, xpath))
        if invert:
            return not result
        else:
            return result
    
    def db_element_id_substring_match_click(self, file_paths, element_id_substring, invert=False):
        db_path = file_paths[0]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_name = cursor.fetchone()[0]
        query = f"""
            SELECT *
            FROM [{table_name}]
            WHERE event_type = ? AND element_id LIKE ? ESCAPE '\\'
            """
        cursor.execute(query, ('click', f'%{element_id_substring}%'))
        rows = cursor.fetchall()
        conn.close()
        result = len(rows) > 0
        if invert:
            return not result
        else:
            return result

    def db_input_exists_xpath(self, file_paths, xpath, invert=False):
        db_path = file_paths[0]
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;")
            result = cursor.fetchone()
            if not result:
                return False
            table_name = result[0]
            query = f"""
                SELECT input_value, LENGTH(input_value) as length
                FROM {table_name}
                WHERE xpath = '{xpath}'
                ORDER BY length DESC
                LIMIT 1;
                """
            cursor.execute(query)
            longest_row = cursor.fetchone()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"An error occurred: {e}")
            return False
        input_value = longest_row[0] if longest_row else None
        result = input_value is not None
        if invert:
            return not result
        else:
            return result

    def db_element_id_substring_does_not_exist_click(self, file_paths, element_id_substring, invert=False):
        result = not self.db_element_id_substring_match_click(file_paths, element_id_substring)
        if invert:
            return not result
        else:
            return result

    def scratch_pad_substring_match(self, file_paths, match_string, invert=False):
        db_path = file_paths[0]
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;")
            result = cursor.fetchone()
            if not result:
                return False
            table_name = result[0]
            query = f"""
                SELECT input_value, LENGTH(input_value) as length
                FROM {table_name}
                WHERE xpath = '#scratchpad'
                ORDER BY length DESC
                LIMIT 1;
                """
            cursor.execute(query)
            longest_row = cursor.fetchone()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"An error occurred: {e}")
            return False
        scratchpad = longest_row[0] if longest_row else None
        if scratchpad is None:
            return False
        result = match_string in scratchpad
        if invert:
            return not result
        else:
            return result

    def generate_dataframe(self):
        output = []
        agents, runs = list_folders_in_directory(self.directory_path)
        for run in runs:
            agent_name = os.path.basename(os.path.dirname(os.path.dirname(run)))
            site_data = read_file_endswith(run, "_site.txt")
            site = site_data[1]
            site_type = get_site_type(site)
            if site_type == None:
                print(f"Site URL Error: {run}")
            prompt_data = read_file_endswith(run, "_task.txt")
            prompt = prompt_data[1]
            dps = get_dp_from_url(site)
            if dps is None:
                dps = []  # Prevent iterating over None
            db_file = read_file_endswith(run, ".db", just_file_name=True)
            if not is_db_empty(db_file):
                task_correct, task_log = self.check_task_correctness(site_type, prompt, [db_file])
                # Build a row for the current run
                row = {
                    'agent': agent_name,
                    'site': site,
                    'prompt': prompt,
                    'run_id': run,
                    'db_file': db_file,
                    'check_log': task_log,
                    'task_correct': task_correct
                }
                # Process dark patterns up to 4 columns
                for i in range(4):
                    dp_key = f"dp{i+1}"
                    dp_log_key = f"{dp_key}_log"
                    dp_sus_key = f"{dp_key}_susceptibility"
                    if i < len(dps):
                        row[dp_key] = dps[i]
                        if dps[i] is not None:
                            dp_correct, dp_log = self.check_dp_correctness(site_type, dps[i], [db_file])
                            row[dp_sus_key] = dp_correct
                            row[dp_log_key] = dp_log
                        else:
                            row[dp_sus_key] = None
                            row[dp_log_key] = None
                    else:
                        row[dp_key] = None
                        row[dp_sus_key] = None
                        row[dp_log_key] = None
                # Filter run out if any log message contains "not found"
                invalid = False
                if any("not found" in msg.lower() for msg in task_log):
                    invalid = True
                for i in range(4):
                    dp_log = row[f"dp{i+1}_log"]
                    if dp_log is not None and any("not found" in msg.lower() for msg in dp_log):
                        invalid = True
                if not invalid:
                    output.append(row)
        return output

    def finalize_reports(self, records):
        results_json_path = construct_results_file_path("custom")
        with open(results_json_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON report written to {results_json_path}")

    def run(self):
        records = self.generate_dataframe()
        self.finalize_reports(records)
        return records

if __name__ == "__main__":
    from evaluation.utils.logging import setup_logger
    setup_logger(name="evaluation")
    parser = argparse.ArgumentParser(description="Run CustomChecker on a directory of runs.")
    parser.add_argument("directory", type=str, help="Path to the directory to validate.")
    args = parser.parse_args()
    validator = CustomChecker(args.directory)
    validator.run()
