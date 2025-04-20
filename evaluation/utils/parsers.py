import re
import os
import string
from typing import List
import urllib

# TODO Make the _dark_patterns endings an ENUM to avoid excessive imports
from evaluation.consts import postscripts, prompt_helper, site_dp_mapping, spotify_dark_patterns, health_dark_patterns, linkedin_dark_patterns, wikipedia_dark_patterns, news_dark_patterns, shopping_dark_patterns

# TODO Transition away from typing, since it is now built into python standard library: https://stackoverflow.com/questions/66738753/python-typing-deprecation
def find_directories_matching_suffix(root: str, pattern: str = r".*_\d+$") -> List[str]:
    """
    Recursively walk 'root' and return a list of full paths to directories 
    whose basename matches the given regex pattern (default: ends with '_<number>').
    """
    results = []
    regex = re.compile(pattern)
    for dirpath, dirnames, filenames in os.walk(root):
        base = os.path.basename(dirpath)
        if regex.match(base):
            results.append(dirpath)
    return results

def unify_task_format(task: str) -> str:
    # Remove disclaimers, punctuation, underscores
    cleaned = remove_postscript(task)
    cleaned = cleaned.replace("_", " ")
    cleaned = re.sub(f"[{re.escape(string.punctuation)}]+", "", cleaned)
    return cleaned.strip().lower()

# TODO Not sure if this function is necessary, since it is just a one liner
def remove_apostrophe(s: str) -> str:
    return s.replace('"', "")

def remove_postscript(s: str) -> str:
    if s:
        for postscript in postscripts:
            s = s.replace(postscript, "")
        csv_task = s.rstrip()
    else:
        csv_task = ""
    return csv_task

def remove_prompt_helper(s: str) -> str:
    return s.replace(prompt_helper, "").rstrip()

def get_dp_codes(site_url: str) -> str:
    # Extract the site category from the URL
    site_match = re.search(r'agenttrickydps\.vercel\.app/(\w+)', site_url)  # TODO This does not support the NextJS linkedin site, which has a different URL
    if site_match:
        site_category = site_match.group(1)
    else:
        site_category = "N/A"
    
    # Extract the dp codes from the URL
    dp_match = re.search(r'dp=([a-zA-Z0-9_]+)', site_url)
    if dp_match:
        dp_codes = dp_match.group(1).split('_')
    else:
        dp_codes = ["N/A"]
    
    dark_patterns = []
    if site_category in site_dp_mapping:
        for code in dp_codes:
            label = site_dp_mapping[site_category].get(code, "N/A")
            if label != "N/A":
                dark_patterns.append(label)
    else:
        dark_patterns.append("N/A")
    
    result = "|".join(dark_patterns) if dark_patterns else "N/A"
    return result

# TODO Rename these directories to be more generic
# TODO The file organization between data_parsers.py and name_parsers.py doesn't make much sense

# TODO This function doesn't make much sense
def find_target_subdirs_for_prefix(root: str, data_subdirs: List[str]) -> List[str]:
    """
    Walk through agent directories and collect target subdirectories based on fixed data types.
    """
    results = []
    for agent in os.listdir(root):
        agent_path = os.path.join(root, agent)
        if os.path.isdir(agent_path):
            for data_subdir in data_subdirs:
                data_path = os.path.join(agent_path, data_subdir)
                if os.path.isdir(data_path):
                    # Collect all numbered subdirectories within the data_subdir
                    numbered_subdirs = find_directories_matching_suffix(data_path)
                    results.extend(numbered_subdirs)
    return results

def get_mapping_for_site(site):
    """
    Returns the appropriate dark pattern mapping dictionary based on keywords in the site URL.
    """
    site_lower = site.lower()
    if "spotify" in site_lower:
        return spotify_dark_patterns
    elif "health" in site_lower:
        return health_dark_patterns
    elif "linkedin" in site_lower:
        return linkedin_dark_patterns
    elif "wikipedia" in site_lower:
        return wikipedia_dark_patterns
    elif "news" in site_lower:
        return news_dark_patterns
    elif "shopping" in site_lower:
        return shopping_dark_patterns
    else:
        return {}

# Brandon helpers
def get_site_type(url):
    parsed_url = urllib.parse.urlparse(url)
    path = parsed_url.path.strip('/')
    return path.split('/')[1] if path else None

def get_dp_from_url(url):
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    dps = []
    if 'dp' in query_params:
        dp_value = query_params['dp'][0]
        dps = dp_value.split('_')[0:]
    
    # Make sure dps is just 4 values:
    if len(dps) > 4:
        dps = dps[:4]
    
    # Fill the rest of the list with None up to len 4:
    for i in range(4 - len(dps)):
        dps.append(None)
    
    return dps