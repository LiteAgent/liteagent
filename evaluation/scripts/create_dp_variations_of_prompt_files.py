"""
This script reads all files from a source directory.
Each file is assumed to have the following format:

    <base URL>
    <instruction 1>
    <instruction 2>
    ...
    
The base URL (the first line) is modified to include every combination
of dark patterns according to a mapping defined for that site (based on
its endpoint). For example, if the file’s URL is:
    
    agenttrickydps.vercel.app/health

and the mapping for health is:

    health_dark_patterns = {
        "pa": "Pregnancy Analytics",
        "cs": "Complex Settings",
        "tos": "Terms Of Service",
    }

then the script will generate new files with the URL changed to include a
query parameter `dp=` with every nonempty combination of the keys.
For instance, one variation will have:

    agenttrickydps.vercel.app/health?dp=pa
    agenttrickydps.vercel.app/health?dp=cs
    agenttrickydps.vercel.app/health?dp=tos
    agenttrickydps.vercel.app/health?dp=pa_cs
    agenttrickydps.vercel.app/health?dp=pa_tos
    agenttrickydps.vercel.app/health?dp=cs_tos
    agenttrickydps.vercel.app/health?dp=pa_cs_tos

If a file’s URL does not correspond to any known mapping (or can be
mapped via a heuristic, such as endpoints starting with "shop"), then the
file is simply copied unchanged.
"""

import os
import itertools
import argparse
from urllib.parse import urlparse, urlunparse
from consts import *

def get_endpoint(url):
    """
    Given a URL (which may or may not include a scheme),
    return the endpoint (i.e. the last nonempty part of the path).
    """
    # If no scheme is present, prepend "http://"
    if not url.startswith("http"):
        url_with_scheme = "http://" + url
    else:
        url_with_scheme = url

    parsed = urlparse(url_with_scheme)
    # Split the path and get the last nonempty part
    path_parts = [part for part in parsed.path.split("/") if part]
    if path_parts:
        return path_parts[-1]
    return ""


def generate_combinations(keys):
    """
    Return a list of underscore-joined strings representing every nonempty
    combination of the provided keys.
    """
    combos = []
    # Generate combinations for r = 1 to len(keys)
    for r in range(1, len(keys) + 1):
        for combo in itertools.combinations(keys, r):
            dp_string = "_".join(combo)
            combos.append(dp_string)
    return combos


def modify_url(url, dp_string):
    """
    Given the original URL and a dp_string (e.g. "pa_cs"),
    return the URL with a query parameter appended: ?dp=<dp_string>.
    If the URL already has a query string, the new parameter is appended.
    """
    # Ensure we have a URL with a scheme for parsing
    if not url.startswith("http"):
        url_with_scheme = "http://" + url
    else:
        url_with_scheme = url

    parsed = urlparse(url_with_scheme)
    # If there is already a query, append the dp parameter with "&", otherwise use "dp="
    if parsed.query:
        query = parsed.query + f"&dp={dp_string}"
    else:
        query = f"dp={dp_string}"
    new_parsed = parsed._replace(query=query)
    new_url = urlunparse(new_parsed)

    # If the original URL did not include a scheme, remove the "http://" prefix.
    if not url.startswith("http"):
        new_url = new_url.replace("http://", "", 1)
    return new_url


def process_file(file_path, dst_dir):
    """
    Process a single file. If the file’s first line (URL) maps to a dark
    pattern dictionary, generate one file for every combination of dark
    pattern keys and write them to dst_dir. Otherwise, copy the file unchanged.
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    if not lines:
        return

    original_url = lines[0].strip()
    rest_of_file = "".join(lines[1:])

    endpoint = get_endpoint(original_url)
    # Look up a mapping based on the endpoint.
    mapping = site_dp_mapping.get(endpoint)
    # Optionally, if the endpoint starts with "shop" (like "shoptwo"), assume shopping patterns.
    if mapping is None and endpoint.startswith("shop"):
        mapping = shopping_dark_patterns

    basename = os.path.basename(file_path)
    name, ext = os.path.splitext(basename)

    if mapping:
        # Get the dark pattern keys in the order of definition.
        mapping_keys = list(mapping.keys())
        dp_combinations = generate_combinations(mapping_keys)
        for dp_string in dp_combinations:
            new_url = modify_url(original_url, dp_string)
            new_content = new_url + "\n" + rest_of_file
            new_filename = f"{name}_dp_{dp_string}{ext}"
            new_file_path = os.path.join(dst_dir, new_filename)
            with open(new_file_path, "w") as out_f:
                out_f.write(new_content)
    else:
        # No mapping was found: simply copy the file over unchanged.
        dst_file_path = os.path.join(dst_dir, basename)
        with open(dst_file_path, "w") as out_f:
            out_f.write("".join(lines))


def main(src_dir, dst_dir):
    # Create the destination directory if it does not exist.
    os.makedirs(dst_dir, exist_ok=True)

    # Process each file in the source directory.
    for entry in os.listdir(src_dir):
        file_path = os.path.join(src_dir, entry)
        if os.path.isfile(file_path):
            process_file(file_path, dst_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate variations of site files with dark pattern query parameters."
    )
    parser.add_argument("src_dir", help="Path to the source directory containing the files.")
    parser.add_argument("dst_dir", help="Path to the destination directory for variations.")
    args = parser.parse_args()

    main(args.src_dir, args.dst_dir)
