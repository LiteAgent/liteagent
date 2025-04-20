from typing import TypedDict, List, Dict, Union

class Check(TypedDict):
    type: str
    check: Dict[str, Union[str, int]]

class TaskChecks(TypedDict):
    checks: List[Check]
