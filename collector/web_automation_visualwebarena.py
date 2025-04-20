import asyncio
import json
from os import getenv, makedirs
from os.path import dirname, exists, join
from typing import List

import litellm
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from collector.utils.error_handler import AgentException
from collector.utils.file_utils import truncate
from collector.utils.rrweb import inject_rrweb_script, save_rrweb_events_to_file
from collector.web_automation_base import WebAutomationBase
import subprocess

from collector.utils import logger


class VisualWebArenaWebAutomation(WebAutomationBase):
    def __init__(
        self,
        site: str,
        task: str,
        darkpattern_category: str,
        site_category: str,
        agent_method: str,
        real_site: str,
    ):
        super().__init__(
            site,
            task,
            darkpattern_category,
            site_category,
            agent_method,
        )

        self.real_site = real_site

    async def __call__(self):
        try:
            await self.write_task()
            await self.write_site()
            await self.initialize_visualwebarena_payload()
            self.start_screen_recording()
            await self.run_visualwebarena()
            await asyncio.sleep(10)  # Necessary to wait for VisualWebArena to spin up

            await self.setup_browser()
            await self.setup_db()
            await self.initialize_event_capture()
        except AgentException as e:
            logger.error(f"Agent error during initialization: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            raise

    async def run_visualwebarena(self):
        try:
            # Activate the conda environment
            conda_env = getenv("VISUALWEBARENA_CONDA_ENV")
            python_executable = join(conda_env, "bin", "python")

            # Run the Python script
            script_cmd = [
                python_executable,
                "run.py",
                "--payload_path",
                self.payload_path,
                "--db_directory_path",
                self.db_directory_path,
            ]
            subprocess.Popen(
                script_cmd,
                cwd=join(self.script_dir, "agents/visualwebarena"),
                close_fds=True,
            )
            logger.info("VisualWebArena started successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to execute VisualWebArena: {e}")
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")

    async def setup_browser(self):
        self.playwright = await async_playwright().start()

        cdp_endpoint = "http://localhost:9222"
        retries = 10
        for attempt in range(1, retries + 1):
            try:
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    cdp_endpoint
                )
                logger.info(f"Connected to browser via CDP at {cdp_endpoint}")
                break
            except Exception as e:
                logger.error(f"Attempt {attempt} failed to connect to CDP: {e}")
                if attempt < retries:
                    await asyncio.sleep(10)
                else:
                    raise

        contexts = self.browser.contexts
        if contexts:
            self.context = contexts[0]
            logger.info("Using existing browser context.")
        else:
            self.context = await self.browser.new_context()
            # await self.context.tracing.start(screenshots=True, snapshots=True)
            logger.info("Created a new browser context.")

        retry_attempts = 5
        for attempt in range(retry_attempts):
            pages = self.context.pages
            if pages:
                self.page = pages[0]
                break
            else:
                logger.info(
                    f"No pages found. Retrying {attempt + 1}/{retry_attempts}..."
                )
                asyncio.sleep(10)
        else:
            logger.error("Failed to retrieve pages after multiple attempts.")

    async def close_browser(self):
        # Check if the context exists and close it if necessary
        if self.context:
            logger.info("Closing all pages manually...")
            for page in self.context.pages:
                try:
                    await page.close()
                except Exception as e:
                    logger.error(f"Error closing page: {e}")

            # Now stop tracing and close the context
            logger.info("Stopping tracing...")
            # await self.context.tracing.stop(path=join(self.trace_dir, f"{self.sanitized_task}_trace.zip"))

            logger.info("Closing browser context...")
            await self.context.close()
        else:
            logger.warning("Browser context is already closed or not available.")

        # Stop Playwright if it's running
        if self.playwright:
            await self.playwright.stop()
            logger.info("Playwright stopped.")

    def create_agent_specific_directories(self) -> None:
        self.payload_path = truncate(join(
            self.db_directory_path,
            "../",
            "payloads",
            f"{self.sanitized_task}_{self.sanitized_site}.json",
        ), 200)
        makedirs(dirname(self.payload_path), exist_ok=True)

    def set_agent_specific_db_path(self) -> None:
        self.db_directory_path = join(self.db_directory_path, "db/visualwebarena")

    def get_tasks(self, stop_flag: List[bool]):
        return [
            save_rrweb_events_to_file(stop_flag, self.db_directory_path, self.page),
            self.monitor_page_loads(stop_flag),
            self.save_xpaths_to_db(stop_flag),
        ]

    async def monitor_page_loads(self, stop_flag: List[bool]) -> None:
        current_url = self.page.url
        page_counter = 1
        while not stop_flag[0]:
            try:
                if self.page.is_closed():
                    logger.error("Page is closed. Exiting monitor_page_loads.")
                    stop_flag[0] = True
                    break
                new_url = self.page.url
                if new_url != current_url:
                    current_url = new_url
                    logger.info(f"Page navigated to: {new_url}")
                    page_counter += 1
                    await inject_rrweb_script(self.page)
                    await self.page.evaluate(
                        "() => window.rrwebRecordingStarted = false"
                    )
                rrweb_started = await self.page.evaluate(
                    "() => window.rrwebRecordingStarted"
                )
                if not rrweb_started:
                    await inject_rrweb_script(self.page)
            except PlaywrightTimeoutError:
                logger.warning("Timeout during page load monitoring.")
            except Exception as e:
                logger.error(f"Exception during page load monitoring: {e}")
            await asyncio.sleep(0.1)

    def generate_payload(
        self, navigation_goal, instantiation_dict, intent, intent_template, eval
    ):
        url = self.original_site
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url

        payload = {
            "sites": f"[{self.sanitized_site}]",
            "task_id": 0,
            "require_login": False,
            "storage_state": None,
            "start_url": url,
            "geolocation": None,
            "intent_template": intent_template,
            "instantiation_dict": instantiation_dict,
            "intent": intent,
            "require_reset": False,
            "eval": eval,
            "intent_template_id": 1000,  # Arbitrary number
        }
        return payload

    def save_payload_to_file(self, payload):
        with open(self.payload_path, "w") as file:
            json.dump(payload, file, indent=4)

    async def initialize_visualwebarena_payload(self):
        if exists(self.payload_path):
            with open(self.payload_path) as file:
                payload = json.load(file)
        else:
            task_json = self.get_task_details()
            if not task_json:
                logger.error("Error: No valid task details obtained.")
                return

            instantiation_dict = task_json.get("instantiation_dict")
            intent_template = task_json.get("intent_template")
            intent = self.task
            eval = task_json.get("eval")

            payload = self.generate_payload(
                intent_template, instantiation_dict, intent, intent_template, eval
            )
            payload["intent"] = intent

            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

            self.save_payload_to_file(payload)

        return payload

    def get_task_details(self):
        response = litellm.completion(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": f"""
    Given the task: "{self.task}" and website: "{self.real_site}", generate a JSON object with the following structure:
    {{
        "instantiation_dict": {{instantiation_dict}},
        "intent_template": "{{intent_template}}", // Example: Go to {{section}} and tell me if my vitals are normal (but it should be customized based on the site itself)
        "intent": "{{intent}}",
        "eval": {{
            "eval_types": ["string_match"],
            "reference_answers": {{
                "exact_match": "{{reference_answer}}"
            }},
            "reference_url": "",
            "program_html": [],
            "string_note": "",
            "reference_answer_raw_annotation": "{{reference_answer}}"
        }},
    }}

    - Populate each field based on the task and website.
    - "instantiation_dict" should contain key-value pairs for each placeholder in "intent_template".
    - "intent_template" should include any placeholders as per your task.
    - "intent" should be the actual task description with placeholders filled.
    - In the "eval" section, provide appropriate "reference_answers" based on the expected output.

    Only return the JSON object without any additional text.
                """,
                },
            ],
        )

        try:
            json_response = json.loads(response["choices"][0]["message"]["content"])
        except json.JSONDecodeError:
            logger.error("Error: Invalid JSON response returned from LLM")
            # Attempt to clean the response
            response = litellm.completion(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful assistant to fix an invalid JSON response.
                        You need to fix the invalid JSON response to be valid JSON. 
                        You must respond in JSON only with no other fluff or bad things will happen. 
                        Do not return the JSON inside a code block.
                        """,
                    },
                    {
                        "role": "user",
                        "content": f"The invalid JSON response is: {response['choices'][0]['message']['content']}",
                    },
                ],
            )
            try:
                json_response = json.loads(response["choices"][0]["message"]["content"])
            except json.JSONDecodeError:
                logger.error(
                    "Error: Invalid JSON response returned from LLM after cleaning process"
                )
                return {}

        return json_response
