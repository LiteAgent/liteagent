import asyncio
import json
import random
import tempfile
from os import getenv, makedirs
from os.path import basename, join
from typing import List

import collector.utils.consts as consts
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from collector.utils.cookies import load_cookies, save_cookies
from collector.utils.error_handler import AgentException
from collector.utils.file_utils import sanitize_filename
from collector.utils.rrweb import inject_rrweb_script, save_rrweb_events_to_file
from collector.web_automation_base import WebAutomationBase
from collector.utils import logger


class MultiOnExtensionWebAutomation(WebAutomationBase):
    def __init__(
        self,
        site: str,
        task: str,
        darkpattern_category: str,
        site_category: str,
        agent_method: str,
        has_adblocker: bool,
        use_cookies: bool,
    ):
        super().__init__(
            site,
            task,
            darkpattern_category,
            site_category,
            agent_method,
        )
        self.prompt = f"Go to {self.original_site} and in that site, do the following task: {self.task}."
        self.has_adblocker = has_adblocker
        self.use_cookies = use_cookies

    async def __call__(self) -> None:
        try:
            await self.write_task()
            await self.write_site()
            await self.setup_browser()
            await self.initialize_extension()
            self.start_screen_recording()
            await self.setup_db()
            await self.initialize_event_capture()
        except AgentException as e:
            logger.error(f"Agent error during initialization: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            raise

    async def setup_browser(self):
        try:
            self.playwright = await async_playwright().start()
            extension_path = join(
                self.script_dir, "extensions", "multion", "multion.chromium"
            )

            args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                f"--disable-extensions-except={extension_path}",
                f"--load-extension={extension_path}",
                "--window-size=1920,1080",
            ]

            user_agent = random.choice(consts.user_agent_strings)

            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                args=args,
                user_agent=user_agent,
            )

            self.context.on(
                "page",
                lambda page: asyncio.create_task(self.close_extra_pages(page)),
            )

            self.page = self.context.pages[0]
            await self.page.bring_to_front()
            await self.context.tracing.start(screenshots=True, snapshots=True)

        except Exception as e:
            await self.close_browser()
            logger.error(f"Error during browser setup: {e}")
            raise

    async def close_browser(self):
        try:
            logger.info("Closing browser")
            if self.context:
                await self.context.tracing.stop(
                    path=join(self.trace_dir, f"{self.sanitized_task}_trace.zip")
                )
                for page in self.context.pages:
                    try:
                        await page.close()
                    except Exception as e:
                        logger.error(f"Error closing page: {e}")

                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
        except AttributeError as e:
            logger.error(f"Attribute error while closing the browser: {e}")
        except Exception as e:
            logger.error(f"Error while closing the browser: {e}")

    def create_agent_specific_directories(self) -> None:
        """Create directories specific to the agent method."""
        self.reasoning_dir = join(self.db_directory_path, "reasoning")
        self.user_data_dir = tempfile.mkdtemp()
        self.cookies_dir = join(self.db_directory_path, "../cookies")
        self.trace_dir = join(self.db_directory_path, "trace")

        directories = [
            self.reasoning_dir,
            self.user_data_dir,
            self.cookies_dir,
            self.trace_dir,
        ]

        for directory in directories:
            makedirs(directory, exist_ok=True)

    def set_agent_specific_db_path(self) -> None:
        self.db_directory_path = join(self.db_directory_path, "db/multion")

    def get_tasks(self, stop_flag: List[bool]):
        return [
            save_rrweb_events_to_file(stop_flag, self.db_directory_path, self.page),
            self.monitor_page_loads(stop_flag),
            self.process_browser_logs_for_network_events(stop_flag),
            self.save_xpaths_to_db(stop_flag),
        ]

    async def close_extra_pages(self, page):
        """Close any newly opened page that is not needed."""
        try:
            # Delay to allow page URL to load and check if it's a popup/extra page
            await page.wait_for_load_state()
            if page.url != self.page.url:  # If the new page is not the main one
                logger.info(f"Closing extra page with URL: {page.url}")
                await page.close()
        except Exception as e:
            logger.error(f"Failed to close extra page: {e}")

    async def monitor_page_loads(self, stop_flag: List[bool]) -> None:
        current_url = self.page.url
        page_counter = 0
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
                    if self.use_cookies:
                        await save_cookies(
                            self.context,
                            self.original_site,
                            self.page.context,
                            self.cookies_dir,
                        )
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

    async def input_text_and_submit(self) -> None:
        await self.page.fill(".TextArea", self.prompt)
        await self.page.click('button[type="submit"]')
        logger.info("Submitted task")

    async def initialize_extension(self) -> None:
        email = getenv("MULTION_EMAIL")
        password = getenv("MULTION_PASSWORD")

        await self.open_site(
            "https://platform.multion.ai/login?callbackUrl=https%3A%2F%2Fplatform.multion.ai%2Fbeta"
        )

        if not email or not password:
            logger.error("MULTION_EMAIL and MULTION_PASSWORD must be set in .env file.")
            await self.close_browser()
            raise AgentException("Missing login credentials")

        try:
            await self.page.wait_for_selector('input[type="email"]', timeout=5000)
            await self.page.fill('input[type="email"]', email)
            await self.page.fill('input[type="password"]', password)
            await self.page.click("#submit")
        except PlaywrightTimeoutError:
            logger.warning("Timeout during login, possibly already logged in.")
        except Exception as e:
            logger.error(f"Error during login process: {e}")
            raise AgentException("Login failed")

        retry_attempts = 3
        for attempt in range(retry_attempts):
            try:
                close_button = await self.page.wait_for_selector(
                    "#radix-\\:r0\\: > button > svg", timeout=5000
                )
                await close_button.click()
                break
            except PlaywrightTimeoutError:  # Hotfix to ensure the popup is closed
                if attempt < retry_attempts - 1:
                    logger.info(
                        f"No popup to close, retrying... ({attempt + 1}/{retry_attempts})"
                    )
                else:
                    logger.info("No popup to close after multiple attempts.")
                    # Click outside the selector by coordinates
                    await self.page.mouse.click(10, 10)  # Adjust coordinates as needed

        await asyncio.sleep(1)
        await self.input_text_and_submit()

    async def open_site(self, site: str) -> None:
        try:
            # Ensure the URL has a scheme
            if not site.startswith(("http://", "https://")):
                site = "http://" + site

            if self.use_cookies:
                sanitized_site = sanitize_filename(site)
                await load_cookies(
                    self.context, sanitized_site, self.page.context, self.cookies_dir
                )
            await self.page.goto(site)
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout while loading the site: {site}")
        except Exception as e:
            logger.error(f"Failed to open site {site}: {e}")
            raise

    async def process_browser_logs_for_network_events(
        self, stop_flag: List[bool]
    ) -> None:
        # Function to handle network responses
        def log_network_response(response):
            try:
                request = response.request
                request_url = request.url
                if (
                    request_url
                    == "https://backend.platform.multion.ai/api/v1/text-to-speech"
                ):
                    # Extract the post data
                    request_payload = request.post_data

                    # Parse the payload
                    parsed_payload = json.loads(request_payload)

                    # Extract the 'text' part of the payload
                    if "text" in parsed_payload:
                        self.write_to_reasoning(parsed_payload["text"])
                        logger.info("Reasoning saved")

                if (
                    request_url
                    == "https://multion-vercel-git-main-multion.vercel.app/api/suggestions"
                ):
                    stop_flag[0] = True
                    logger.info("Exiting after detecting the required network event.")
            except Exception as e:
                logger.error(f"Error processing network response: {e}")

        self.page.on("response", log_network_response)

        while not stop_flag[
            0
        ]:  # TODO Switch to using synchronzation primitives such as asyncio.Event
            await asyncio.sleep(0.1)

    def write_to_reasoning(self, reasoning: str) -> None:
        """Write reasoning steps taken by the agent"""
        with open(
            join(
                self.reasoning_dir, f"{basename(self.db_directory_path)}_reasoning.txt"
            ),
            "a",
        ) as f:
            f.write(reasoning + "\n")
