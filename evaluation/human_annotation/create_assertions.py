import os
import re
import sys
import asyncio
import argparse  # Added for argument parsing
from playwright.async_api import async_playwright, expect
from dotenv import load_dotenv
import litellm
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
import ast 
from evaluation.utils.logging import logger
load_dotenv()

"""
Usage:
  python add_assertions_llm.py /path/to/source_dir [--llm]

Flow:
  - Recursively find all '_commands.py' files.
  - For each file, interpret 'await page.xxx(...)' and 'await expect(...)' calls in real time,
    pausing after each to possibly insert an assertion.
  - If yes, and if --llm is passed, call an LLM for a suggestion, passing the current URL & minified HTML.
    - Show "LLM suggests: X"
    - If user just presses Enter, accept that suggestion.
    - If user types something else, use that instead.
  - If --llm is not passed, prompt the user to manually input the assertion.
  - Insert the assertion, re-run from top. If it fails, offer to remove it and "rewind."
"""

# Regex patterns
# Matches lines like: await page.goto("https://example.com")
ACTION_REGEX = re.compile(r'^(\s*)await\s+page\.(\w+)\((.*)\)\s*$')
# Matches lines like: await expect(page).to_have_url("https://example.com")
EXPECT_REGEX = re.compile(r'^(\s*)await\s+expect\((.*?)\)\.(\w+)\((.*)\)\s*$')


def find_commands_files(root: str):
    """
    Recursively find all files that end in '_commands.py' under `root`.
    """
    matches = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith("_commands.py"):
                matches.append(os.path.join(dirpath, fn))
    return matches


async def run_playwright_action(page, method_name: str, args_str: str):
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
        "evaluate": page.evaluate,
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


async def run_expect_assertion(page, target_str: str, method_name: str, args_str: str):
    """
    Parse arguments safely and call recognized expect methods.
    """
    try:
        # Safely evaluate the target string to get the Locator object
        target = eval(target_str, {"__builtins__": {}, "page": page})
    except Exception as e:
        logger.warning(f"Failed to evaluate target '{target_str}': {e}")
        raise

    try:
        # Safely parse arguments using ast.literal_eval
        call_args = ast.literal_eval(f"({args_str})")
    except Exception as e:
        logger.warning("Failed to parse arguments '{args_str}': {e}")
        call_args = ()

    if not isinstance(call_args, tuple):
        call_args = (call_args,)

    # Mapping of method names to Playwright expect methods
    expect_mapping = {
        "to_have_url": lambda: expect(page).to_have_url(*call_args),
        "to_have_title": lambda: expect(page).to_have_title(*call_args),
        "to_have_text": lambda: expect(target).to_have_text(*call_args),
        "to_have_selector": lambda: expect(target).to_have_selector(*call_args),
        # Add more expect methods as needed
    }

    if method_name in expect_mapping:
        try:
            await expect_mapping[method_name]()
        except AssertionError as e:
            logger.warning(f"Assertion failed for expect.{method_name} with args {call_args}: {e}")
            raise  # Re-raise to notify replay mechanism
        except Exception as e:
            logger.warning(f"Error executing expect.{method_name} with args {call_args}: {e}")
            raise  # Re-raise to notify replay mechanism
    else:
        logger.warning(f"Unrecognized expect method '{method_name}', skipping actual run.")


async def replay_lines_in_memory(lines, browser):
    """
    Re-run lines from top in a fresh context/page. Return True if no assertion fails,
    else False. Handles both action and expect lines.
    """
    context = await browser.new_context()
    page = await context.new_page()

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check for action lines
        m_action = ACTION_REGEX.match(line)
        if m_action:
            method_name = m_action.group(2)
            args_str = m_action.group(3)
            try:
                await run_playwright_action(page, method_name, args_str)
            except Exception as e:
                logger.warning(f"Execution error on action '{line_stripped}': {e}")
            continue

        # Check for expect assertion lines
        m_expect = EXPECT_REGEX.match(line)
        if m_expect:
            target = m_expect.group(2)
            method_name = m_expect.group(3)
            args_str = m_expect.group(4)
            try:
                await run_expect_assertion(page, target, method_name, args_str)
            except AssertionError:
                await context.close()
                return False
            except Exception as e:
                logger.warning(f"Execution error on expect '{line_stripped}': {e}")
                await context.close()
                return False

    await context.close()
    return True


def minify_html(html: str, max_len: int = 3000) -> str:
    """
    A naive minifier: remove newlines/tabs, collapse spaces, and trim to max_len.
    """
    # Remove newlines and tabs
    txt = html.replace("\n", " ").replace("\t", " ")
    # Collapse multiple spaces into one
    txt = re.sub(r"\s+", " ", txt)
    # Trim to max_len
    if len(txt) > max_len:
        txt = txt[:max_len] + "..."
    return txt.strip()


def get_llm_suggestion(action_line: str, current_url: str, minified_html: str) -> str:
    """
    Use litellm with GPT-4o (or your chosen model) to propose an assertion.
    The prompt includes the action line, current URL, and minified HTML.
    """
    prompt = f"""You are a helpful coding assistant. The user just performed this Playwright action:
Action: {action_line}
URL: {current_url}
HTML (minified up to 3000 chars): {minified_html}

Please propose a *single-line* Python assertion using Playwright's `expect` API that would validate the correctness 
of the page state right after that action. 

Tailor the assertion to the actual content you see from the HTML and URL. 
Return only one line of code. Do not use backticks (```).
"""

    try:
        response = litellm.completion(
            model="gpt-4o-mini",
            messages=[{"content": prompt, "role": "user"}],
            max_tokens=80
        )
        suggestion = response["choices"][0]["message"]["content"].strip()
        return suggestion
    except Exception as e:
        logger.warning(f"LLM suggestion error: {e}")
        return 'await expect(page).to_have_url("https://example.com")  # fallback'


async def prompt_for_assertion(action_line: str, current_url: str, minified_html: str, use_llm: bool, session: PromptSession) -> str:
    """
    1) If use_llm is True:
        a) Get an LLM suggestion for the action line, using the page's URL & HTML
        b) Show the user "LLM suggests: <suggestion>"
        c) If user just hits ENTER, accept it. Otherwise use typed input.
    2) If use_llm is False:
        a) Prompt the user to manually input the assertion.
    """
    if use_llm:
        suggestion = get_llm_suggestion(action_line, current_url, minified_html)
        logger.debug(f"\nLLM suggests: {suggestion}")
        user_input = await session.prompt_async("Press ENTER to accept, or type your own assertion: ")
        user_input = user_input.strip()
        if user_input == "":
            # User accepted suggestion
            return suggestion
        else:
            return user_input
    else:
        # Prompt the user to input their own assertion
        print("\nPlease type your assertion using Playwright's `expect` API.")
        user_input = await session.prompt_async("Enter your assertion: ")
        user_input = user_input.strip()
        if user_input:
            return user_input
        else:
            logger.warning(f"No assertion entered. Skipping insertion.")
            return ""  # Return empty string to indicate no assertion


async def process_file(file_path: str, browser, use_llm: bool, session: PromptSession):
    """
    Read lines from file_path, execute them line by line.
    After each action, optionally insert an expect assertion.
    Write the updated content back to the same file after processing.
    """
    logger.debug(f"\n=== Processing {file_path} ===")

    with open(file_path, "r", encoding="utf-8") as f:
        lines_in_memory = f.readlines()

    changed = False

    context = await browser.new_context()
    page = await context.new_page()

    i = 0
    while i < len(lines_in_memory):
        line = lines_in_memory[i]
        line_stripped = line.strip()
        m_action = ACTION_REGEX.match(line)
        m_expect = EXPECT_REGEX.match(line)

        if m_action:
            logger.debug(f"\nAction line: {line_stripped}")
            method_name = m_action.group(2)
            args_str = m_action.group(3)

            # Execute the action in real-time
            try:
                await run_playwright_action(page, method_name, args_str)
            except Exception as e:
                logger.warning(f"Real-time run error: {e}")

            if method_name in ["goto", "type", "press"]:
                i += 1
                continue
            if method_name == "evaluate" and "window.scrollTo" in args_str:
                i += 1
                continue
            
            # Get current URL and HTML
            current_url = page.url
            html = await page.content()
            min_html = minify_html(html)

            ans = (await session.prompt_async("Insert an assertion after this action? [y/n/s] ")).strip().lower()
            if ans == "s":
                logger.info(f"Skipping file {file_path} as per user request.")
                break  # Skip the rest of the file
            elif ans == "y":
                indent = m_action.group(1)
                # Remove existing assertion lines after the current action
                j = i + 1
                while j < len(lines_in_memory):
                    next_line = lines_in_memory[j]
                    if ACTION_REGEX.match(next_line):
                        break  # Next action line found; stop removing
                    if EXPECT_REGEX.match(next_line):
                        logger.debug(f"Removing existing assertion line: {next_line.strip()}")
                        del lines_in_memory[j]
                        changed = True
                    else:
                        j += 1

                # Get assertion suggestion from LLM or prompt user manually
                assertion_line = await prompt_for_assertion(
                    line_stripped, current_url, min_html, use_llm, session
                )

                if assertion_line:
                    new_line = indent + assertion_line + "\n"
                    lines_in_memory.insert(i + 1, new_line)
                    changed = True

                    logger.info(f"Re-running from top to test the new assertion now...")
                    success = await replay_lines_in_memory(lines_in_memory, browser)
                    if not success:
                        print("[ERROR] The newly inserted assertion failed!")
                        keep_ans = (await session.prompt_async("Keep this failing assertion anyway? [y/n] ")).strip().lower()
                        if keep_ans == "n":
                            lines_in_memory.pop(i + 1)
                            logger.info("Assertion removed.")
                        else:
                            logger.info("Assertion kept (but it fails).")
                    else:
                        logger.info("Assertion passed!")
                    i += 1  # Move past the inserted assertion
                else:
                    logger.info("No assertion inserted.")
                    i += 1
            elif ans == "s":
                logger.info("Skipping assertion insertion for this action.")
                i += 1
            else:
                i += 1
        elif m_expect:
            i += 1
        else:
            i += 1

    await page.close()
    await context.close()

    if changed:
        # Backup the original file
        backup = file_path + ".bak"
        try:
            os.rename(file_path, backup)
            logger.info(f"Backup created: {backup}")
        except FileExistsError:
            logger.warning(f"Backup file already exists: {backup}. Overwriting.")
            os.remove(backup)
            os.rename(file_path, backup)
            logger.info(f"Backup created: {backup}")

        # Write the updated content back to the original file
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines_in_memory)
        logger.info(f"Updated {file_path} with inserted assertions.")
    else:
        logger.info(f"No changes made to {file_path}.")


async def main_async(source_dir, use_llm: bool):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        files = find_commands_files(source_dir)
        if not files:
            logger.info("No '_commands.py' files found.")
            return

        logger.info(f"Found {len(files)} file(s) to process.")

        # Initialize PromptSession
        session = PromptSession()

        # Use patch_stdout to prevent print statements from interfering with prompts
        with patch_stdout():
            for fp in sorted(files):
                await process_file(fp, browser, use_llm, session)

        await browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Add assertions to Playwright '_commands.py' files, optionally using an LLM."
    )
    parser.add_argument(
        "source_dir",
        type=str,
        help="Path to the source directory containing '_commands.py' files."
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use LLM to suggest assertions."
    )

    args = parser.parse_args()

    source_dir = args.source_dir
    use_llm = args.llm

    if not os.path.isdir(source_dir):
        logger.error(f"Not a directory: {source_dir}")
        sys.exit(1)

    asyncio.run(main_async(source_dir, use_llm))


# TODO Main won't run, since this is now a module, in which it uses the logger from the utils package 
if __name__ == "__main__":
    main()
