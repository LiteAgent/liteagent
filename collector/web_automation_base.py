from abc import ABC, abstractmethod
from os import makedirs
from os.path import basename, dirname, join, realpath
from typing import List
from urllib.parse import urlparse

from collector.db_model import create_interaction_event_class
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine
from collector.utils.database import ElementInteractionDatabaseManager
from collector.utils.file_utils import get_new_db_path, sanitize, shorten_url, write_file

from collector.utils import logger
from collector.utils.recorder import Recorder

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from evaluation.consts import prompt_helper
import asyncio

class WebAutomationBase(ABC):
    def __init__(
        self,
        site: str,
        task: str,
        darkpattern_category: str,
        site_category: str,
        agent_method: str,
    ):
        self.original_site = site
        self.script_dir = dirname(realpath(__file__))
        self.task = f"{task} {prompt_helper}"
        self.sanitized_task = sanitize(task)
        self.agent_method = agent_method

        self.playwright = self.browser = self.context = self.page = None

        self.data_path = join(self.script_dir, "../", "data")
        self.db_directory_path = self.data_path
        parsed_url = urlparse(self.original_site)
        self.domain = parsed_url.netloc

        self.sanitized_domain = sanitize(self.domain)
        if len(site) > 100:
            site = shorten_url(self.original_site)
        self.sanitized_site = sanitize(site)

        self.set_db_path(darkpattern_category, site_category)
        self.create_directories()
        self.initialize_db()
        self.recorder = None  # Initialize the Recorder attribute

    @abstractmethod
    async def __call__(self) -> None:
        pass

    @abstractmethod
    async def setup_browser(self) -> None:
        """Set up the browser"""

    @abstractmethod
    async def close_browser(self) -> None:
        """Close browser and clean up resources"""

    @abstractmethod
    def create_agent_specific_directories(self) -> None:
        """Create directories specific to the agent method."""

    @abstractmethod
    def set_agent_specific_db_path(self) -> None:
        """Make db path specific to the agent method"""

    @abstractmethod
    def get_tasks(self, stop_flag: List[bool]):
        """Get coroutines to run specific to the agent method"""

    def set_db_path(self, darkpattern_category: str, site_category: str):
        """Set up database paths based on common conditions."""
        self.set_agent_specific_db_path()
        if getattr(self, "has_adblocker", False):
            self.db_directory_path = join(self.db_directory_path, "adblocked")
        if site_category:
            self.db_directory_path = join(self.db_directory_path, site_category)
        if darkpattern_category:
            self.db_directory_path = join(self.db_directory_path, darkpattern_category)
        self.db_directory_path = join(self.db_directory_path, self.sanitized_task)

    def create_directories(self):
        """Create necessary directories for database"""
        self.db_directory_path = get_new_db_path(self.db_directory_path)
        makedirs(self.db_directory_path, exist_ok=True)
        self.video_dir = join(self.db_directory_path, "video")
        makedirs(self.video_dir, exist_ok=True)

        self.create_agent_specific_directories()

    async def setup_db(self):
        # Create InteractionEvent and initialize the database before setting up the browser
        self.InteractionEvent = await create_interaction_event_class(
            sanitize(self.task), self.engine
        )
        await self.database_manager.initialize_database(self.InteractionEvent)

    def initialize_db(self):
        """Initialize the database engine"""
        try:
            self.engine = create_async_engine(
                f"sqlite+aiosqlite:///{self.db_directory_path}/{basename(self.db_directory_path)}.db",
                connect_args={"timeout": 30}
            )
            self.database_manager = ElementInteractionDatabaseManager(
                self.engine,
            )
        except SQLAlchemyError as e:
            logger.error(
                f"An SQLAlchemy error occurred while initializing the database: {e}"
            )
            raise
        except OSError as e:
            logger.error(f"An OS error occurred while initializing the database: {e}")
            raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while initializing the database: {e}"
            )
            raise

    async def initialize_event_capture(self):
        """Initialize event capture by exposing functions and injecting JavaScript."""
        self.database_manager.page = self.page
        self.database_manager.db_directory_path = self.db_directory_path
        await self.database_manager.expose_functions(self.context, self.InteractionEvent)
        await self.database_manager.inject_javascript(self.page, self.context)
        
    async def save_xpaths_to_db(self, stop_flag: List[bool]) -> None:
        """Delegate to the XPathDatabaseManager for saving XPath data to the database."""
        await self.database_manager.save_xpaths_to_db(
            stop_flag
        )

    async def write_site(self) -> None:
        site_file_path = join(
            self.db_directory_path, f"{basename(self.db_directory_path)}_site.txt"
        )
        write_file(site_file_path, self.original_site, mode="w")

    async def write_task(self) -> None:
        task_file_path = join(
            self.db_directory_path, f"{basename(self.db_directory_path)}_task.txt"
        )
        write_file(task_file_path, self.task, mode="w")

    def start_screen_recording(self):
        self.recorder = Recorder(self.video_dir, self.sanitized_task)
        self.recorder.start()

    def stop_screen_recording(self):
        if self.recorder:
            self.recorder.stop()

    def set_page(self, new_page):
        self.page = new_page
        if self.database_manager:
            self.database_manager.page = new_page

    async def periodically_sum_time_since_last_action(self, stop_flag: List[bool]) -> None:
        """
        Every X seconds, sums the 'time_since_last_action' column from the InteractionEvent table,
        logs the total, and if unchanged since the last check, sets the stop flag.
        """
        Session = sessionmaker(bind=self.engine, expire_on_commit=False, class_=AsyncSession)
        previous_total = None
        while True:
            async with Session() as session:
                result = await session.execute(
                    select(func.sum(self.InteractionEvent.__table__.c.time_since_last_action))
                )
                total = result.scalar() or 0
                logger.info(f"Total time since last action: {total}")
            if previous_total is not None and total == previous_total:
                stop_flag[0] = True
                break
            previous_total = total
            await asyncio.sleep(60)