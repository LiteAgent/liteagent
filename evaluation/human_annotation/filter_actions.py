import os
import re
import sys
import sqlite3
import asyncio
import argparse
from playwright.async_api import async_playwright, Page, expect
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from evaluation.utils.logging import logger
import ast

# Load environment variables if any
load_dotenv()

# Constants
START_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../data/db"))

# Updated Regex patterns to parse Playwright commands
# Matches lines like: # ID 1: navigate to https://example.com
# or: # ID 1: click => selector
ACTION_REGEX = re.compile(r'^# ID (\d+): (\w+(?: [\w\-]+)*) (?:=>|to) (.+)')
PLAYWRIGHT_COMMAND_REGEX = re.compile(r'^\s*await\s+page\.(\w+)\((.*)\)\s*$')
EXPECT_COMMAND_REGEX = re.compile(r'^\s*await\s+expect\((.*?)\)\.(\w+)\((.*)\)\s*$')

def find_commands_files(root: str):
    """
    Recursively find all files that end with '_commands.py' under `root`.
    """
    matches = []
    for dirpath, dirs, files in os.walk(root):
        for filename in files:
            if filename.endswith("_commands.py"):
                matches.append(os.path.join(dirpath, filename))
    return matches

def get_associated_db(commands_file: str):
    """
    Given a '_commands.py' file path, find the associated '.db' file in the same directory.
    Assumes the '.db' file shares the same base name as the '_commands.py' file.
    """
    dir_name, filename = os.path.split(commands_file)
    base, _ = os.path.splitext(filename)
    db_filename = base.replace("_commands", "").replace("test_", "") + ".db"
    db_path = os.path.join(dir_name, db_filename)
    if os.path.isfile(db_path):
        return db_path
    else:
        logger.warning(f"Associated DB not found for {commands_file}: expected {db_path}")
        return None

def get_first_table_name(db_path: str) -> str:
    """
    Returns the first user-defined table name in 'db_path', or None if none found.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def load_actions_from_db(db_path: str, table_name: str):
    """
    Loads actions (id, event_type, xpath, class_name, element_id, input_value, url, additional_info)
    from the table in ascending ID order.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = f"""
        SELECT
            id,
            event_type,
            xpath,
            class_name,
            element_id,
            input_value,
            url,
            additional_info
        FROM "{table_name}"
        ORDER BY id
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    actions = []
    for row in rows:
        actions.append({
            "id":             row[0],
            "event_type":     row[1] or "",
            "xpath":          row[2] or "",
            "class_name":     row[3] or "",
            "element_id":     row[4] or "",
            "input_value":    row[5] or "",
            "url":            row[6] or "",
            "additional_info":row[7] or "",
        })
    return actions

def build_selector(action):
    """
    Builds a CSS selector from 'element_id', 'xpath' (which is actually a CSS in your logs),
    or 'class_name'. Skips blacklisted IDs like 'root'.
    """
    bad_ids = {"root", "", "body"}
    elem_id = action["element_id"].strip().lower()
    if elem_id and elem_id not in bad_ids:
        return f"#{action['element_id']}"

    if action["xpath"]:
        return action["xpath"]

    if action["class_name"]:
        # just the first chunk
        return f".{action['class_name'].split()[0]}"

    return "body"

def remove_ephemeral_focused(selector: str) -> str:
    """
    Remove .ant-input-affix-wrapper-focused or similar ephemeral class from the final CSS.
    """
    return selector.replace(".ant-input-affix-wrapper-focused", "")

def create_minimal_db(original_db_path: str, table_name: str, kept_actions: list, output_db_path: str):
    """
    Creates a new SQLite DB with only the kept actions.
    Overrides the existing minimal DB if it exists.
    Ensures that 'id's are unique.
    """
    if not kept_actions:
        logger.warning(f"No actions to keep. Minimal DB not created for {original_db_path}.")
        return
        
    # Remove duplicates based on 'id', keeping the first occurrence
    unique_actions = {}
    for action in kept_actions:
        if action['id'] not in unique_actions:
            unique_actions[action['id']] = action
        else:
            logger.warning(f"Duplicate Action ID {action['id']} found. Keeping the first occurrence.")

    kept_actions = list(unique_actions.values())

    # Connect to original DB to get the schema
    original_conn = sqlite3.connect(original_db_path)
    original_cursor = original_conn.cursor()

    # Get the schema for the table
    original_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    create_table_sql = original_cursor.fetchone()
    if not create_table_sql:
        logger.error(f"Failed to retrieve table schema for '{table_name}' from '{original_db_path}'")
        original_conn.close()
        return
    create_table_sql = create_table_sql[0]

    original_conn.close()

    # Create new DB and table
    new_conn = sqlite3.connect(output_db_path)
    new_cursor = new_conn.cursor()
    new_cursor.execute(create_table_sql)

    # Insert kept actions
    insert_query = f"""
        INSERT INTO "{table_name}" (id, event_type, xpath, class_name, element_id, input_value, url, additional_info)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    for action in kept_actions:
        try:
            new_cursor.execute(insert_query, (
                action["id"],
                action["event_type"],
                action["xpath"],
                action["class_name"],
                action["element_id"],
                action["input_value"],
                action["url"],
                action["additional_info"],
            ))
        except sqlite3.IntegrityError as e:
            logger.error(f"IntegrityError for Action ID {action['id']}: {e}")
            logger.info(f"Skipping Action ID {action['id']}.")

    new_conn.commit()
    new_conn.close()
    logger.info(f"Created minimal DB: {output_db_path}")

async def run_playwright_action(page: Page, method_name: str, args_str: str):
    """
    Parse arguments safely and call recognized methods on `page`.
    """
    try:
        # Safely parse arguments using ast.literal_eval
        call_args = ast.literal_eval(f"({args_str})")
    except Exception as e:
        logger.warning(f"Failed to parse arguments '{args_str}': {e}")
        call_args = ()

    if not isinstance(call_args, tuple):
        call_args = (call_args,)

    # Mapping of method names to Playwright page methods
    method_mapping = {
        "goto": page.goto,
        "click": page.click,
        "fill": page.fill,
        "press": page.press,
        "wait_for_timeout": page.wait_for_timeout,
        "hover": page.hover,
        "type": page.type,
        "check": page.check,
        "uncheck": page.uncheck,
        "select_option": page.select_option,
        # Add more methods as needed
    }

    if method_name in method_mapping:
        try:
            await method_mapping[method_name](*call_args)
        except Exception as e:
            logger.warning(f"Error executing page.{method_name} with args {call_args}: {e}")
    else:
        logger.warning(f"Unrecognized method '{method_name}', skipping actual run.")

async def process_commands_file(commands_file: str, browser, session: PromptSession):
    """
    Process a single '_commands.py' file:
    - Execute each Playwright action.
    - After each action, check if it's in the database.
        - If yes, prompt to keep or discard or skip.
        - If no, execute without prompting.
    - Collect kept actions.
    - Generate a minimal database with kept actions.
    - Provide option to skip processing the entire file by inputting 's'.
    """
    logger.debug(f"\n=== Processing {commands_file} ===")

    # Find associated DB
    db_path = get_associated_db(commands_file)
    if not db_path:
        logger.warning(f"Skipping {commands_file} due to missing associated DB.")
        return

    table_name = get_first_table_name(db_path)
    if not table_name:
        logger.warning(f"No user-defined table in {db_path}, skipping.")
        return

    # Load all actions from DB
    all_actions = load_actions_from_db(db_path, table_name)
    if not all_actions:
        logger.warning(f"No actions found in table '{table_name}' for {db_path}, skipping.")
        return

    # Create a mapping from ID to action
    action_map = {action['id']: action for action in all_actions}

    kept_actions = []

    # Read the '_commands.py' file
    with open(commands_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Read site URL from <db_basename>_site.txt
    dir_name = os.path.dirname(db_path)
    filename = os.path.basename(db_path)
    db_basename, _ = os.path.splitext(filename)
    site_path = os.path.join(dir_name, f"{db_basename}_site.txt")
    site_url = None
    if os.path.exists(site_path):
        with open(site_path, "r", encoding="utf-8") as sf:
            site_url = sf.read().strip()

    # Initialize Playwright page
    context = await browser.new_context()
    context.set_default_timeout(10000)
    page = await context.new_page()
    if site_url:
        await page.goto(f"https://{site_url}")

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        line_stripped = line.strip()

        # Parse action ID and description from comment
        m_comment = ACTION_REGEX.match(line_stripped)
        if m_comment:
            action_id = int(m_comment.group(1))
            action_description = m_comment.group(2)
            action_details = m_comment.group(3)

            # Determine output DB path
            dir_name, filename = os.path.split(db_path)
            base, ext = os.path.splitext(filename)
            output_db_name = f"{base}_minimal{ext}"
            output_db_path = os.path.join(dir_name, output_db_name)

            # Next line should be the Playwright command
            if idx + 1 < len(lines):
                command_line = lines[idx + 1].strip()
                m_command = PLAYWRIGHT_COMMAND_REGEX.match(command_line)
                if m_command:
                    method_name = m_command.group(1)
                    args_str = m_command.group(2)

                    logger.debug(f"\nAction ID {action_id}: {action_description} => {action_details}")
                    logger.debug(f"Executing: await page.{method_name}({args_str})")

                    # Execute the Playwright action
                    try:
                        await run_playwright_action(page, method_name, args_str)
                    except Exception as e:
                        logger.warning(f"Error executing action ID {action_id}: {e}")

                    # Check if the output DB already exists and remove it to avoid OperationalError
                    if os.path.exists(output_db_path):
                        logger.info(f"A minimal DB named '{output_db_path}' already exists.")
                        should_remove = await session.prompt_async(f"Remove minimal DB? [y/n]: ")
                        should_remove = should_remove.strip().lower()
                        if should_remove == 'y':
                            try:
                                os.remove(output_db_path)
                                logger.info(f"Existing minimal DB '{output_db_path}' removed.")
                            except Exception as e:
                                logger.error(f"Failed to remove existing minimal DB '{output_db_path}': {e}")
                                return
                        elif should_remove == 'n':
                            logger.info(f"Keeping existing minimal DB '{output_db_path}'.")
                        else:
                            logger.error(f"Invalid input '{should_remove}'. Please enter 'y' or 'n'.")
                        
                    # Check if the action exists in the database
                    if action_id in action_map:
                        # Prompt user to keep, discard, or skip
                        while True:
                            user_input = await session.prompt_async(f"Keep Action ID {action_id}? [y/n/s]: ")
                            user_input = user_input.strip().lower()
                            if user_input in ('y', 'n', 's'):
                                break
                            else:
                                print("Please enter 'y', 'n', or 's'.")

                        if user_input == 'y':
                            kept_actions.append(action_map[action_id])
                            logger.info(f"Kept Action ID {action_id}.")
                        elif user_input == 'n':
                            logger.info(f"Discarded Action ID {action_id}.")
                        elif user_input == 's':
                            logger.info(f"Skipping the rest of the actions in {commands_file}.")
                            # Optionally, you can choose to clear kept_actions if you don't want to keep any actions from this file
                            # kept_actions = []
                            # Break the loop to skip the rest of the file
                            break
                    else:
                        logger.info(f"Action ID {action_id} not found in database. Executed without prompting.")

                    # Move to the line after the command
                    idx += 2
                else:
                    logger.warning(f"Playwright command not found after comment line at index {idx}.")
                    idx += 1
            else:
                logger.warning(f"No Playwright command found after comment line at index {idx}.")
                idx += 1
        else:
            # Non-action, non-comment lines can be skipped or handled as needed
            idx += 1

    # Close Playwright page and context
    await page.close()
    await context.close()

    if kept_actions:
        create_minimal_db(db_path, table_name, kept_actions, output_db_path)
    else:
        logger.warning(f"No actions kept for {db_path}. Minimal DB not created.")

async def main_async(source_dir):
    """
    Main asynchronous function to process all '_commands.py' files.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        commands_files = find_commands_files(source_dir)
        if not commands_files:
            logger.info("No '_commands.py' files found.")
            await browser.close()
            return

        logger.info(f"Found {len(commands_files)} '_commands.py' file(s) to process.")

        # Initialize PromptSession
        session = PromptSession()

        # Use patch_stdout to prevent print statements from interfering with prompts
        with patch_stdout():
            for commands_file in sorted(commands_files):
                await process_commands_file(commands_file, browser, session)

        await browser.close()

def main():
    parser = argparse.ArgumentParser(
        description="Execute Playwright actions from '_commands.py' files and generate minimal databases based on user input."
    )
    parser.add_argument(
        "source_dir",
        type=str,
        nargs='?',
        default=START_DIR,
        help="Path to the source directory containing '.db' and '_commands.py' files. Defaults to '../../data/db'."
    )
    parser.add_argument("--subdir", type=str, default=None, help="Optional subdirectory within source_dir.")

    args = parser.parse_args()

    source_dir = args.source_dir

    if args.subdir:
        source_dir = os.path.join(source_dir, args.subdir)

    if not os.path.isdir(source_dir):
        logger.error(f"Not a directory: {source_dir}")
        sys.exit(1)

    # Initialize PromptSession
    session = PromptSession()
    # Use patch_stdout to prevent print statements from interfering with prompts
    with patch_stdout():
        asyncio.run(main_async(source_dir))

if __name__ == "__main__":
    main()
