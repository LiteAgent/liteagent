from evaluation.enums import CheckTypes, CheckKeys
from typing import Dict, Union

# TODO Make sure these enforcements are correct
def create_check(check_type: CheckTypes, **kwargs) -> Dict[str, Union[str, Dict[str, Union[str, int]]]]:
    if check_type == CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID:
        allowed_keys = {CheckKeys.ELEMENT_ID, CheckKeys.ELEMENT_ID_SUBSTRING, CheckKeys.XPATH, CheckKeys.NUM_INSTANCES}
        extra_keys = set(kwargs.keys()) - allowed_keys
        if extra_keys:  # TODO Add extra_keys to rest of the checks
            raise ValueError(f"Invalid keys {extra_keys} for check type {check_type}")
    elif check_type == CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID:
        allowed_keys = {CheckKeys.ELEMENT_ID, CheckKeys.NUM_INSTANCES, CheckKeys.INVERT}
    elif check_type == CheckTypes.DB_INPUT_EXISTS_XPATH:
        allowed_keys = {CheckKeys.ELEMENT_ID, CheckKeys.ELEMENT_ID_SUBSTRING, CheckKeys.XPATH, CheckKeys.INVERT}
    elif check_type == CheckTypes.SCRATCHPAD_SUBSTRING_MATCH:
        allowed_keys = {CheckKeys.MATCH_STRING, CheckKeys.INVERT}
    elif check_type == CheckTypes.DB_AT_LEAST_ONE_MATCH_ELEMENT_IDS:
        allowed_keys = {CheckKeys.ELEMENT_IDS, CheckKeys.INVERT}
    elif check_type == CheckTypes.DB_AT_LEAST_ONE_MATCH_XPATHS:
        allowed_keys = {CheckKeys.XPATHS, CheckKeys.INVERT}
    return {"type": check_type, "check": kwargs}
