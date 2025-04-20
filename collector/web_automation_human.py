import asyncio
import random
from os import makedirs
from os.path import join
from typing import List

import tempfile
import collector.utils.consts as consts
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from collector.utils.cookies import load_cookies, save_cookies
from collector.utils.error_handler import AgentException
from collector.utils.file_utils import sanitize_filename, write_file
from collector.utils.rrweb import inject_rrweb_script, save_rrweb_events_to_file
from collector.utils import logger
from collector.web_automation_base import WebAutomationBase

class WebAutomationHuman(WebAutomationBase):
    def __init__(
        self,
        site: str,
        task: str,
        darkpattern_category: str,
        site_category: str,
        agent_method: str,
        simulate_ios: bool,
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
        self.simulate_ios = simulate_ios
        self.has_adblocker = has_adblocker
        self.use_cookies = use_cookies

    async def __call__(self) -> None:
        try:
            # Ensure the order of calling these methods is appropriate
            await self.write_task()
            await self.write_site()
            await self.setup_browser()
            await self.setup_db()
            await self.initialize_event_capture()
            self.start_screen_recording()
            await self.open_site(self.original_site)
        except AgentException as e:
            logger.error(f"Agent error during initialization: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            raise

    async def setup_browser(self):
        try:
            self.playwright = await async_playwright().start()

            args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--window-size=1920,1080",
            ]
            user_agent = random.choice(consts.user_agent_strings)

            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                args=args,
                # record_video_dir=self.video_dir,  # This method does not work due to https://github.com/microsoft/playwright/issues/14813
                user_agent=user_agent,
            )

            self.context = self.browser
            self.page = self.browser.pages[0]

            # Add event listener for context close to handle manual closure
            self.context.on(
                "close", lambda: asyncio.create_task(self.on_context_close())
            )

        except Exception as e:
            await self.close_browser()
            logger.error(f"Error during browser setup: {e}")
            raise

    async def on_context_close(self):
        """
        Callback invoked when the browser context is closed.
        Ensures that close_browser is called to perform cleanup and save recordings.
        """
        logger.info("Browser context closed manually.")
        await self.close_browser()

    async def close_browser(self):
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed.")
        except Exception as e:
            logger.error(f"Error while closing the browser: {e}")

    def create_agent_specific_directories(self) -> None:
        """Create directories specific to the agent method."""
        self.user_data_dir = tempfile.mkdtemp()
        self.cookies_dir = join(self.db_directory_path, "../cookies")

        directories = [self.user_data_dir, self.cookies_dir]

        for directory in directories:
            makedirs(directory, exist_ok=True)

    def set_agent_specific_db_path(self) -> None:
        self.db_directory_path = join(self.db_directory_path, "db/human")

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
                    if self.use_cookies:
                        await save_cookies(
                            self.browser,
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

    async def open_site(self, site: str) -> None:
        try:
            # Ensure the URL has a scheme
            if not site.startswith(("http://", "https://")):
                site = "http://" + site

            if self.use_cookies:
                sanitized_site = sanitize_filename(site)
                await load_cookies(
                    self.browser, sanitized_site, self.page.context, self.cookies_dir
                )
            await self.page.goto(site)
            self.initial_url = self.page.url  # Capture the initial URL
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout while loading the site: {site}")
        except Exception as e:
            logger.error(f"Failed to open site {site}: {e}")
            raise
