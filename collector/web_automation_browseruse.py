import asyncio
from os import makedirs
from os.path import dirname, join
import tempfile
import shutil
from typing import List
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from collector.utils.error_handler import AgentException
from collector.utils.rrweb import inject_rrweb_script, save_rrweb_events_to_file
from collector.web_automation_base import WebAutomationBase
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from browser_use import Agent, Browser, BrowserConfig
from collector.utils import logger

class BrowserUseWebAutomation(WebAutomationBase):
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
            await self.setup_browser()
            await self.setup_browseruse()
            asyncio.create_task(self.run_agent_and_close())
            await asyncio.sleep(1)
            self.start_screen_recording()
            await self.setup_db()
            await self.initialize_event_capture()
        except AgentException as e:
            logger.error(f"Agent error during initialization: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            raise

    async def setup_browseruse(self):
        config = BrowserConfig(
            cdp_url="http://localhost:9222",
        )
        self.browseruse = Browser(config=config)
        self.agent = Agent(
            task=self.prompt,
            llm=ChatOpenAI(
                model="gpt-4o",
            ),
            # llm=ChatOllama(
            #     model="qwen2.5:7b",
            #     num_ctx=32000,
            #     base_url="https://kraken.ngrok.dev",
            # ),
            browser=self.browseruse,
            save_conversation_path=self.reasoning_dir
        )

    async def run_agent_and_close(self):
        await self.agent.run()
        await self.close_browser()

    async def setup_browser(self):
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            args=["--remote-debugging-port=9222"]
        )
        logger.info("Launched a new persistent context")
        self.page = self.context.pages[0]

    async def close_browser(self):
        try:
            await self.browseruse.close()
        except Exception as e:
            logger.error(f"Error killing Browseruse: {e}")

    def create_agent_specific_directories(self) -> None:
        self.reasoning_dir= join(
            self.db_directory_path, "reasoning",
        )
        self.original_user_data_dir = join(
            self.data_path, "browser_data", "browseruse"
        )
        temp_dir = tempfile.mkdtemp()
        self.user_data_dir = temp_dir

        directories = [
            self.reasoning_dir,
            self.user_data_dir,
        ]

        for directory in directories:
            makedirs(directory, exist_ok=True)

        shutil.copytree(self.original_user_data_dir, self.user_data_dir, dirs_exist_ok=True)

    def set_agent_specific_db_path(self) -> None:
        self.db_directory_path = join(self.db_directory_path, "db/browseruse")

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
