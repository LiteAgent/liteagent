import asyncio
import json
import time
from os import getenv, makedirs
from os.path import dirname, exists, join
from typing import List
import psutil
import requests
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from collector.utils.error_handler import AgentException
from collector.utils.file_utils import truncate
from collector.utils.rrweb import inject_rrweb_script, save_rrweb_events_to_file
from collector.web_automation_base import WebAutomationBase
import subprocess
from collector.webhook_server_skyvern import create_webhook_server
from collector.utils import logger


class SkyvernWebAutomation(WebAutomationBase):
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
            self.start_webhook_server()
            await self.write_task()
            await self.write_site()
            payload = await self.initialize_skyvern_payload()
            await self.run_skyvern()

            for _ in range(30):
                if self.is_skyvern_listening_on_8000():
                    break
                await asyncio.sleep(1)
            await asyncio.sleep(2)  # Around how much it takes for skyvern to fully load

            res = self.send_request(payload)
            logger.debug(f"Skyvern response: {res}")

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

    async def run_skyvern(self):
        try:
            subprocess.Popen(
                ["./run_skyvern.sh"],
                cwd=join(self.script_dir, "agents/skyvern"),
                close_fds=True,
            )
            logger.info("Started run_skyvern.sh script successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to execute run_skyvern.sh: {e}")

    # TODO Change this to make sure skyvern specifically is listening, since it may be any process running on port 8000
    def is_skyvern_listening_on_8000(self) -> bool:
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port == 8000 and conn.status == psutil.CONN_LISTEN:
                    return True
        except (psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.warning(f"Error checking connections: {e}")
        return False

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

    async def kill_skyvern(self):
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

    async def close_browser(self):
        try:
            await self.kill_skyvern()  # Existing call to kill_skyvern
        except Exception as e:
            logger.error(f"Error killing Skyvern: {e}")

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

    def create_agent_specific_directories(self) -> None:
        self.payload_path = truncate(join(
            self.db_directory_path,
            "../",
            "payloads",
            f"{self.sanitized_task}_{self.sanitized_site}.json",
        ), 200)
        makedirs(dirname(self.payload_path), exist_ok=True)

    def set_agent_specific_db_path(self) -> None:
        self.db_directory_path = join(self.db_directory_path, "db/skyvern")

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

    def send_request(self, payload):
        headers = {
            "Content-Type": "application/json",
            "x-api-key": getenv("X_API_KEY"),
        }
        response = requests.post(
            "http://localhost:8000/api/v1/tasks", json=payload, headers=headers
        )
        return response.json()

    async def initialize_skyvern_payload(self):
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
        url = self.original_site
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url

        payload = {
            "title": f"run-through of {self.task} on {self.original_site}",
            "url": url,
            "navigation_goal": self.task,
            "webhook_callback_url": getenv("SKYVERN_WEBHOOK_CALLBACK_URL", None),
        }
        return payload

    def save_payload_to_file(self, payload):
        with open(self.payload_path, "w") as file:
            json.dump(payload, file, indent=4)

    def start_webhook_server(self):
        """Start the webhook server in a separate thread."""
        create_webhook_server(self.db_directory_path)
