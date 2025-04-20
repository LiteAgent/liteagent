import asyncio
import requests
import time
from os import makedirs, getenv
from os.path import dirname, join, exists
import subprocess
import tempfile
import shutil
import psutil
from typing import List
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from collector.utils.error_handler import AgentException
from collector.utils.rrweb import inject_rrweb_script, save_rrweb_events_to_file
from collector.utils.file_utils import truncate
from collector.web_automation_base import WebAutomationBase
from collector.utils import logger
import json
import threading

class AgentEWebAutomation(WebAutomationBase):
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

        self.prompt = f"Go to {self.original_site} and in that site, do the following task: {self.task}."
        self.real_site = real_site

    async def __call__(self):
        try:
            await self.write_task()
            await self.write_site()
            payload = await self.initialize_agente_payload()
            await self.run_agente()

            for _ in range(30):
                if self.is_agente_listening_on_8000():
                    break
                await asyncio.sleep(1)
            await asyncio.sleep(2)  # Ensures that agente is fully loaded

            threading.Thread(target=self.send_request, args=(payload,), daemon=True).start()
            logger.debug("Agent E request sent in a separate thread.")

            await asyncio.sleep(1)
            await self.setup_browser()
            self.start_screen_recording()
            await self.setup_db()
            await self.initialize_event_capture()
        except AgentException as e:
            logger.error(f"Agent error during initialization: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            raise

    # TODO DRY between this code and Skyvern code
    def is_agente_listening_on_8000(self) -> bool:
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port == 8000 and conn.status == psutil.CONN_LISTEN:
                    return True
        except (psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.warning(f"Error checking connections: {e}")
        return False

    def send_request(self, payload):
        headers = {
            "Content-Type": "application/json",
        }
        requests.post(
            "http://127.0.0.1:8000/execute_task", json=payload, headers=headers
        )

    async def initialize_agente_payload(self):
        if exists(self.payload_path):
            with open(self.payload_path) as file:
                payload = json.load(file)
        else:
            payload = self.generate_payload()
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            self.save_payload_to_file(payload)

        return payload

    def generate_payload(
        self,
    ):
        payload = {
            "command": self.prompt
        }
        return payload

    def save_payload_to_file(self, payload):
        with open(self.payload_path, "w") as file:
            json.dump(payload, file, indent=4)

    async def setup_browser(self):
        self.playwright = await async_playwright().start()

        cdp_endpoint = "http://localhost:9222"
        retries = 3
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
            logger.info("Created a new browser context.")
            # await self.context.tracing.start(screenshots=True, snapshots=True)

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

    def create_agent_specific_directories(self) -> None:
        self.reasoning_dir= join(
            self.db_directory_path, "reasoning",
        )

        self.payload_path = truncate(join(
            self.db_directory_path,
            "../",
            "payloads",
            f"{self.sanitized_task}_{self.sanitized_site}.json",
        ), 200)

        directories = [
            self.reasoning_dir,
            dirname(self.payload_path)
        ]

        for directory in directories:
            makedirs(directory, exist_ok=True)


    async def run_agente(self):
        try:
            subprocess.Popen(
                ["uvicorn", "ae.server.api_routes:app", "--reload", "--loop", "asyncio"],  # TODO Install uvicorn within the docker container
                cwd=join(self.script_dir, "agents/agente"),
                close_fds=True,
            )
            logger.info("Started agent E server successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start agent E server: {e}")

    def set_agent_specific_db_path(self) -> None:
        self.db_directory_path = join(self.db_directory_path, "db/agente")

    def get_tasks(self, stop_flag: List[bool]):
        return [
            save_rrweb_events_to_file(stop_flag, self.db_directory_path, self.page),
            self.monitor_page_loads(stop_flag),
            self.save_xpaths_to_db(stop_flag),
        ]

    async def close_browser(self):
        try:
            await self.kill_agente() 
        except Exception as e:
            logger.error(f"Error killing Agent E: {e}")

        if self.context and self.browser and self.context in self.browser.contexts:
            logger.info("Closing all pages manually...")
            for page in self.context.pages:
                try:
                    await page.close()
                except Exception as e:
                    logger.error(f"Error closing page: {e}")

            try:
                logger.info("Closing browser context...")
                await self.context.close()
            except Exception as e:
                logger.error(f"Error closing browser context: {e}")
        else:
            logger.warning("Browser context is already closed or not available.")

        # Stop Playwright if it's running
        if self.playwright:
            try:
                await self.playwright.stop()
                logger.info("Playwright stopped.")
                self.playwright = None
            except Exception as e:
                logger.error(f"Error stopping Playwright: {e}")

    async def kill_agente(self):
        try:
            subprocess.run(["fuser", "-k", "8000/tcp"])
            logger.info("Port 8000 killed.")

            # Wait for port 8000 to be released
            while True:
                result = subprocess.run(
                    ["fuser", "8000/tcp"], capture_output=True, text=True
                )
                if result.returncode != 0:
                    logger.info("Port 8000 is now free.")
                    break
                time.sleep(1)

        except Exception as e:
            logger.error(f"Error while closing the browser or killing the process: {e}")

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
