import os
import re
import requests
import cv2
from filelock import FileLock


def sanitize(value: str) -> str:
    value = re.sub(r"(https?://)|(www\.)|(\.com)", "", value)
    value = re.sub(r"[^\w\s-]", "_", value)
    value = value.strip().replace(" ", "_")
    return value.rstrip("_").strip("_")


def sanitize_filename(url: str) -> str:
    sanitized_url = re.sub(r"^https?://", "", url)
    sanitized_url = re.sub(r"[^\w\-]", "_", sanitized_url)
    return sanitized_url[:100]


def get_new_db_path(db_directory_path: str) -> str:
    dirname, basename = os.path.split(db_directory_path)

    lock_path = dirname + ".lock"
    with FileLock(lock_path):
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    pattern = re.escape(basename) + r"_(\d+)"
    max_num = 0

    for file in os.listdir(dirname):
        match = re.match(pattern, file)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    new_db_path = os.path.join(dirname, f"{basename}_{max_num + 1}")

    # Ensure the new directory is created with a file lock
    if not os.path.exists(new_db_path):
        with FileLock(new_db_path + ".lock"):
            os.makedirs(new_db_path, exist_ok=True)

    return new_db_path


def shorten_url(long_url):
    api_url = f"http://tinyurl.com/api-create.php?url={long_url}"
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception("Error shortening URL")

def truncate(text: str, max_length: int) -> str:
    """Truncates the text to the specified maximum length."""
    if len(text) > max_length:
        text = text[:100]
    return text

def get_new_db_path(db_directory_path: str) -> str:
    dirname, basename = os.path.split(db_directory_path)

    # Truncate basename if it is longer than 100 characters
    basename = truncate(basename, 100)

    # Ensure the dirname exists
    lock_path = dirname + ".lock"
    with FileLock(lock_path):
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    pattern = re.escape(basename) + r"_(\d+)"
    max_num = 0

    for file in os.listdir(dirname):
        match = re.match(pattern, file)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    new_db_path = os.path.join(dirname, f"{basename}_{max_num + 1}")

    # Ensure the new directory is created with a unique path
    if not os.path.exists(new_db_path):
        os.makedirs(new_db_path, exist_ok=True)

    return new_db_path

def write_file(
    file_path: str, content: str, mode: str = "w", encoding: str = "utf-8"
) -> None:
    """Writes content to a file using the specified mode and encoding."""
    lock_path = file_path + ".lock"
    with FileLock(lock_path):
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)


def create_video_writer(
    file_path: str, fourcc: int, fps: float, frame_size: tuple
) -> cv2.VideoWriter:
    """Creates and returns a cv2.VideoWriter object."""
    return cv2.VideoWriter(file_path, fourcc, fps, frame_size)
