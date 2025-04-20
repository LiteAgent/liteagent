import asyncio
import random
import shutil
import tempfile
from os import makedirs
from os.path import join
from typing import List
from collector.utils.file_utils import sanitize_filename, write_file
import collector.utils.consts as consts
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from collector.utils.cookies import load_cookies, save_cookies
from collector.utils.error_handler import AgentException
from collector.utils.rrweb import save_rrweb_events_to_file, inject_rrweb_script
from collector.utils.screen_utils import click_screen_coordinates, press_keys
from collector.web_automation_base import WebAutomationBase
from collector.utils import logger


class DoBrowserExtensionWebAutomation(WebAutomationBase):
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
            await self.setup_db()
            await self.initialize_event_capture()
            self.start_screen_recording()
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
                self.script_dir,
                "extensions",
                "dobrowser",
                "dobrowser.chromium"
            )

            args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                f"--disable-extensions-except={extension_path}",
                f"--load-extension={extension_path}",
                "--window-position=100,100",
                "--window-size=1920,1080",
            ]

            user_agent = random.choice(consts.user_agent_strings)

            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                args=args,
                user_agent=user_agent,
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
    
        self.original_user_data_dir = join(
            self.data_path, "browser_data", "dobrowser"
        )
    
        temp_dir = tempfile.mkdtemp()
        self.user_data_dir = temp_dir
        self.cookies_dir = join(self.db_directory_path, "../cookies")
        self.trace_dir = join(self.db_directory_path, "trace")
    
        directories = [
            self.reasoning_dir,
            self.user_data_dir,
            # self.cookies_dir,
            self.trace_dir,
        ]
    
        for directory in directories:
            makedirs(directory, exist_ok=True)
    
        shutil.copytree(self.original_user_data_dir, self.user_data_dir, dirs_exist_ok=True)

    def set_agent_specific_db_path(self) -> None:
        self.db_directory_path = join(self.db_directory_path, "db/dobrowser")

    def get_tasks(self, stop_flag: List[bool]):
        return [
            save_rrweb_events_to_file(stop_flag, self.db_directory_path, self.page),
            self.monitor_page_loads(stop_flag),
            # self.process_browser_logs_for_network_events(stop_flag),
            self.periodically_sum_time_since_last_action(stop_flag),
            self.save_xpaths_to_db(stop_flag),
        ]

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

    async def setup_cdp_session(self):
        self.cdp_session = await self.page.context.new_cdp_session(self.page)

    # TODO Find a much less hacky way to achieve this
    async def input_text_and_submit(self) -> None:
        await press_keys([["ctrl", "l"]])
        await press_keys(["do ", self.prompt])
        await press_keys([["enter"]])

    async def initialize_extension(self) -> None:
        # await google_login(self.context, self.page) # The extension requires google login
        # TODO Find a less hacky way to get the dobrowser extension to launch
        await click_screen_coordinates(
            1669, 261
        )  # The exact coordinate with which to open the extension popup, thereby enabling it
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
