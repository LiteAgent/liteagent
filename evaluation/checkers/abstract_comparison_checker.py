# abstract_comparison_checker.py

import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

from evaluation.utils.file_utils import read_file
from evaluation.utils.parsers import unify_task_format, find_target_subdirs_for_prefix

class AbstractComparisonChecker(ABC):
    """
    Abstract base class holding common logic for comparing 
    minimal DBs (source) and maximal DBs (target).
    """

    # TODO Custom correctness checker does not use this constructor
    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = source_dir
        self.target_dir = target_dir

    # TODO Not all comparisons occur in this way (across the respective agents), so it may be better to move this to utils
    def get_click_events(self, data: Dict[int, Dict[str, Any]]) -> List[Tuple[str, str]]:
        """
        Extract (xpath, element_id) for all click events from the DB data.
        """
        return [
            (row.get('xpath'), row.get('element_id'))
            for row in data.values()
            if row.get('event_type') == 'click'
        ]

    # TODO This is completely different in the custom checks
    def find_matched_target_subdirs(
        self, 
        target_dir: str, 
        data_subdirs: List[str], 
        original_task: str
    ) -> List[str]:
        """
        Finds target subdirectories whose task matches the given original_task,
        after normalizing/unifying the task format.
        """
        target_subdirs = find_target_subdirs_for_prefix(target_dir, data_subdirs)
        matched_target_subdirs = []
        normalized_source_task = unify_task_format(original_task)

        for t_subdir in sorted(target_subdirs):
            t_basename = os.path.basename(t_subdir)
            t_task_path = os.path.join(t_subdir, f"{t_basename}_task.txt")
            t_task = read_file(t_task_path)

            normalized_target_task = unify_task_format(t_task)
            if normalized_target_task == normalized_source_task:
                matched_target_subdirs.append(t_subdir)

        return matched_target_subdirs

    # TODO Add more abstract methods that have common logic

    @abstractmethod
    def finalize_reports(self, results_json_path: str) -> None:
        pass

    @abstractmethod
    def run(self):
        """
        Each child class implements its own main entry point logic.
        """
        pass
