import os
import sqlite3
import argparse
import re

# Adjust if needed
START_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../data/db"))

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
    Loads actions (id, event_type, xpath, class_name, element_id, input_value, url, additional_info, time_since_last_action)
    from the table in ascending ID order.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if 'time_since_last_action' column exists
    cursor.execute(f'PRAGMA table_info("{table_name}")')
    columns = [info[1] for info in cursor.fetchall()]
    has_time_since = 'time_since_last_action' in columns

    # Adjust SELECT query based on column existence
    if has_time_since:
        query = f"""
            SELECT
                id,
                event_type,
                xpath,
                class_name,
                element_id,
                input_value,
                url,
                additional_info,
                time_since_last_action
            FROM "{table_name}"
            ORDER BY id
        """
    else:
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
            "time_since_last_action": row[8] if has_time_since else 0.0,
        })
    return actions

def simplify_css_selector(selector: str) -> str:
    return re.sub(r':nth-of-type\(\d+\)', '', selector).strip()

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
        return simplify_css_selector(action["xpath"])

    if action["class_name"]:
        # just the first chunk
        return f".{action['class_name'].split()[0]}"

    return "body"

def remove_ephemeral_focused(selector: str) -> str:
    """
    Remove .ant-input-affix-wrapper-focused or similar ephemeral class from the final CSS.
    """
    return selector.replace(".ant-input-affix-wrapper-focused", "")

def merge_consecutive_inputs(actions):
    """
    Merge consecutive 'input' events for the same selector into one,
    picking the *longest* input_value among them (optional).
    """
    merged = []
    buffer_action = None
    buffer_selector = None

    for a in actions:
        etype = a["event_type"].lower()
        sel = build_selector(a)
        if etype == "input":
            if buffer_action is None:
                buffer_action = dict(a)
                buffer_selector = sel
            else:
                if sel == buffer_selector:
                    old_val = buffer_action["input_value"]
                    new_val = a["input_value"]
                    if len(new_val) > len(old_val):
                        buffer_action["input_value"] = new_val
                        buffer_action["id"] = a["id"]
                else:
                    merged.append(buffer_action)
                    buffer_action = dict(a)
                    buffer_selector = sel
        else:
            if buffer_action is not None:
                merged.append(buffer_action)
                buffer_action = None
                buffer_selector = None
            merged.append(a)
    if buffer_action is not None:
        merged.append(buffer_action)
    return merged

def generate_commands(actions, site_url=None):
    """
    Given the final actions (merged if you like), produce a list of lines of code:
      "await page.goto('...')"
      "await page.click('...')"
      "await page.fill('...', '...')"
      etc.
    We'll place them in an async function for convenience.
    """
    lines = []
    lines.append("import asyncio")
    lines.append("from playwright.async_api import async_playwright, expect")
    lines.append("")
    lines.append("async def test_actions():")
    lines.append("    async with async_playwright() as p:")
    lines.append("        browser = await p.chromium.launch(headless=test_actions.headless)")
    lines.append("        page = await browser.new_page()")

    if site_url:
        lines.append(f"        await page.goto({f'https://{site_url}'!r})")

    current_url = None
    for a in actions:
        a_id   = a["id"]
        a_type = a["event_type"].lower()
        url    = a["url"]
        val    = a["input_value"] or ""
        sel    = build_selector(a)
        sel    = remove_ephemeral_focused(sel)

        # Optionally refine if it's an input container => add " input"
        # if you want it in the final code (like we do in replay)
        if a_type in ("input", "keypress", "click"):
            lowered = sel.lower()
            if ("ant-input" in lowered or "input-search" in lowered or "affix-wrapper" in lowered) and " input" not in lowered:
                sel += " input"


        if a_type == "click":
            lines.append(f"        # ID {a_id}: click => {sel}")
            lines.append(f"        await page.click({sel!r})")

        # if i != 0 and url and url != current_url:
        #     current_url = url
        #     lines.append(f"        # ID {a_id}: navigate to {url}")
        #     lines.append(f"        await page.goto({url!r})")

        elif a_type == "input":
            # Convert literal "\n" to actual newlines
            text_val = val.replace("\\n", "\n")
            lines.append(f"        # ID {a_id}: fill => {sel} with {text_val!r}")
            lines.append(f"        await page.fill({sel!r}, {text_val!r})")

        elif a_type == "keypress":
            if val:
                lines.append(f"        # ID {a_id}: keypress => {val}")
                lines.append(f"        await page.keyboard.press({val!r})")
            else:
                lines.append(f"        # ID {a_id}: keypress skipped (no val)")

        elif a_type == "navigate":
            lines.append(f"        # ID {a_id}: explicitly navigate => {url}")
            # we already did page.goto(url), so we can skip or do it again if you want

        elif a_type == "scroll":
            lines.append(f"        # ID {a_id}: scroll => {a['additional_info']}")
            scroll_info = a["xpath"]
            x_val, y_val = "0", "0"
            try:
                parts = scroll_info.split(",")
                x_val = parts[0].split(":")[1].strip()
                y_val = parts[1].split(":")[1].strip()
            except:
                pass
            lines.append(f"        await page.evaluate('window.scrollTo({x_val}, {y_val})')")

        else:
            lines.append(f"        # ID {a_id}: unhandled => {a_type}")
        
        # Insert sleep based on time_since_last_action
        time_since = float(a.get("time_since_last_action") or 0.0)
        if time_since > 0:
            lines.append(f"        await asyncio.sleep({time_since})")

    lines.append("")
    lines.append("test_actions.headless = True")
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    test_actions.headless = False")
    lines.append("    asyncio.run(test_actions())")

    return lines

def main():
    """
    Recursively find all .db under START_DIR.
    For each, read actions, merge consecutive input, generate a .py file of literal playwright commands.
    """
    parser = argparse.ArgumentParser(description="Generate playwright code from DB files.")
    parser.add_argument("--subdir", help="Optional subdirectory to look under START_DIR", default=None)
    args = parser.parse_args()

    target_dir = START_DIR
    if args.subdir:
        target_dir = os.path.join(target_dir, args.subdir)

    for root, dirs, files in os.walk(target_dir):
        for filename in files:
            if filename.endswith(".db"):
                db_path = os.path.join(root, filename)
                site_url = None
                db_basename, _ = os.path.splitext(filename)
                site_path = os.path.join(root, f"{db_basename}_site.txt")
                if os.path.exists(site_path):
                    with open(site_path, "r", encoding="utf-8") as sf:
                        site_url = sf.read().strip()
                db_basename, _ = os.path.splitext(filename)
                out_script = os.path.join(root, f"test_{db_basename}_commands.py")

                # 1) Get first table in this DB
                table_name = get_first_table_name(db_path)
                if not table_name:
                    print(f"[WARN] No user-defined table in {db_path}, skipping.")
                    continue

                # 2) Load actions
                raw_actions = load_actions_from_db(db_path, table_name)
                if not raw_actions:
                    print(f"[WARN] No actions in table {table_name} for {db_path}, skipping.")
                    continue

                # 3) Merge partial inputs (optional)
                merged_actions = merge_consecutive_inputs(raw_actions)

                # 4) Generate lines of code
                lines = generate_commands(merged_actions, site_url)

                # 5) Write them out
                with open(out_script, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")

                print(f"Generated {out_script}")

if __name__ == "__main__":
    main()
