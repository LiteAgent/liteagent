import asyncio
import time
from sqlite3 import OperationalError
from typing import Any, List

from playwright.async_api import Page
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from collector.utils import logger
from collector.utils.html_utils import scrape_with_scrapy

class ElementInteractionDatabaseManager:
    def __init__(
        self, engine: AsyncEngine
    ) -> None:
        """
        Initializes the database manager.

        Args:
            engine (AsyncEngine): The SQLAlchemy asynchronous engine.
        """
        self.engine = engine
        self.Session = sessionmaker(
            bind=self.engine, expire_on_commit=False, class_=AsyncSession
        )
        self.session = None
        self.start_time = time.time()
        self.recorded_actions = []  # Change to store tuples of (timestamp, action)
        self.last_event_time = None
        self.page = None 
        self.db_directory_path = None
        self.click_count = 0

    def get_time_since_last_action(self) -> float:
        current_time = time.time()
        if self.last_event_time is None:
            self.last_event_time = current_time
            return 0.0
        delta = current_time - self.last_event_time
        self.last_event_time = current_time
        return delta

    async def initialize_database(self, InteractionEvent: Any) -> None:
        """Initialize the database schema, ensuring the dynamic table is created."""
        async with self.engine.begin() as conn:
            # Execute PRAGMA journal_mode=WAL using raw SQL execution
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA busy_timeout=60000"))  # Added busy_timeout
            await conn.run_sync(InteractionEvent.metadata.create_all)
        logger.info(
            f"Database schema initialized for table: {InteractionEvent.__tablename__}"
        )

    async def inject_javascript(self, page, context) -> None:
        """Inject JavaScript into the browser context to capture events."""
        await page.evaluate(self.get_injection_script())  # To log the events of the first page that has already loaded
        await context.add_init_script(self.get_injection_script())

    async def expose_functions(self, context, InteractionEvent):
        """Expose functions at the context level."""
        await context.expose_function(
            "saveClickData",
            lambda selector, class_name, element_id, url: asyncio.create_task(
                self.save_click_data(
                    selector, class_name, element_id, url, InteractionEvent
                )
            ),
        )
        await context.expose_function(
            "saveScrollData",
            lambda scrollX, scrollY: asyncio.create_task(
                self.save_scroll_data(scrollX, scrollY, InteractionEvent)
            ),
        )
        await context.expose_function(
            "saveKeyData",
            lambda key: asyncio.create_task(self.save_key_data(key, InteractionEvent)),
        )
        await context.expose_function(
            "saveInputData",
            lambda selector, value: asyncio.create_task(
                self.save_input_data(selector, value, InteractionEvent)
            ),
        )
        await context.expose_function(
            "saveNavigateData",
            lambda url: asyncio.create_task(
                self.save_navigate_data(url, InteractionEvent)
            ),
        )

    @staticmethod
    def get_injection_script():
        """Return the JavaScript code to inject into a page or context."""
        return """(function() {
            console.log('Injecting event listener JavaScript.');

            // Helper function to escape special characters in strings
            function escapeStringForSelector(str) {
                return str.replace(/["'\\\\]/g, '\\\\$&').replace(/\\\\n/g, '\\\\n').replace(/\\\\r/g, '\\\\r');
            }

            // Function to generate a unique CSS selector for an element
            function getUniqueSelector(element) {
                if (element.id) {
                    // If the element has an ID, return the ID selector
                    return `#${CSS.escape(element.id)}`;
                }
                if (element.hasAttribute('data-testid')) {
                    // If the element has a data-testid attribute, use it
                    return `[data-testid="${escapeStringForSelector(element.getAttribute('data-testid'))}"]`;
                }
                if (element.classList.length === 1) {
                    // If there's only one class, use it
                    return `${element.tagName.toLowerCase()}.${CSS.escape(element.classList[0])}`;
                }
                // Build a CSS selector path
                const parts = [];
                while (element && element.nodeType === Node.ELEMENT_NODE) {
                    let selector = element.nodeName.toLowerCase();
                    if (element.id) {
                        // If a parent has an ID, prepend it and stop
                        selector += `#${CSS.escape(element.id)}`;
                        parts.unshift(selector);
                        break;
                    } else if (element.classList.length > 0) {
                        // Add class names if available
                        selector += '.' + Array.from(element.classList).map(cls => CSS.escape(cls)).join('.');
                    }
                    // Add nth-of-type if necessary
                    const parent = element.parentNode;
                    if (parent) {
                        const siblings = Array.from(parent.children).filter(
                            (e) => e.nodeName === element.nodeName
                        );
                        if (siblings.length > 1) {
                            const index = siblings.indexOf(element) + 1;
                            selector += `:nth-of-type(${index})`;
                        }
                    }
                    parts.unshift(selector);
                    element = element.parentElement;
                }
                return parts.join(' > ');
            }

            function isMultionSite() {
                return window.location.href.includes('multion');
            }

            function getElementId(element) {
                while (element && !element.id) {
                    element = element.parentElement;
                }
                return element ? element.id : '';
            }

            // Capture clicks
            document.addEventListener('click', async function(event) {
                if (isMultionSite()) return;
                var selector = getUniqueSelector(event.target);
                var className = event.target.className || '';
                var elementId = getElementId(event.target);
                var currentUrl = window.location.href;

                // Ensure className is a string
                if (typeof className !== 'string') {
                    className = JSON.stringify(className);
                }

                console.log('Click detected! Selector:', selector, 'Class:', className, 'ID:', elementId);
                await window.saveClickData(selector, className, elementId, currentUrl);
            });

            // Capture scrolls
            window.addEventListener('scroll', async function() {
                if (isMultionSite()) return;
                var scrollX = window.scrollX;
                var scrollY = window.scrollY;
                console.log('Scroll detected! ScrollX:', scrollX, 'ScrollY:', scrollY);
                await window.saveScrollData(scrollX, scrollY);
            });

            // Capture key presses
            document.addEventListener('keydown', async function(event) {
                if (isMultionSite()) return;
                var key = event.key;
                console.log('Key down detected! Key:', key);
                await window.saveKeyData(key);
            });

            // Capture input events
            document.addEventListener('input', async function(event) {
                if (isMultionSite()) return;
                var selector = getUniqueSelector(event.target);
                var value = event.target.value;
                console.log('Input detected! Selector:', selector, 'Value:', value);
                await window.saveInputData(selector, value);
            });

            // Capture navigation events using the 'beforeunload' event
            window.addEventListener('beforeunload', async function(event) {
                if (isMultionSite()) return;
                var url = window.location.href;
                console.log('Navigation detected! URL:', url);
                await window.saveNavigateData(url);
            });
        })();"""

    async def _retry_with_backoff(
        self, operation, max_retries=10, backoff_in_seconds=1
    ):
        """Retries an operation with exponential backoff."""
        retries = 0
        while retries < max_retries:
            try:
                await operation()
                break  # Exit the loop on success
            except OperationalError as e:
                if "database is locked" in str(e):
                    retries += 1
                    backoff_time = backoff_in_seconds * (2 ** (retries - 1))
                    logger.warning(
                        f"Database is locked, retrying in {backoff_time}s... ({retries}/{max_retries})"
                    )
                    await asyncio.sleep(backoff_time)  # Exponential backoff
                else:
                    raise e

    async def save_click_data(
        self,
        selector: str,
        class_name: Any,
        element_id: str,
        url: str,
        InteractionEvent: Any,
    ) -> None:
        """Save click data to the database with retry logic and record Playwright code."""

        async def operation():
            async with self.Session() as session:
                async with session.begin():
                    time_delta = self.get_time_since_last_action()
                    clicked_element = InteractionEvent(
                        event_type="click",
                        xpath=selector,
                        class_name=str(class_name),
                        element_id=element_id,
                        input_value=None,  # No input value for click events
                        url=url,  # Store the URL
                        time_since_last_action=time_delta,
                    )
                    session.add(clicked_element)
                    await session.commit()
            logger.info(
                f"Saved clicked element: Selector={selector}, Class={class_name}, ID={element_id}, URL={url}"
            )

        await self._retry_with_backoff(operation)

        self.click_count += 1
        if self.page and self.db_directory_path:
            await scrape_with_scrapy(
                self.page, self.click_count, url, self.db_directory_path
            )

        # Escape double quotes and backslashes in the selector
        selector_escaped = selector.replace("\\", "\\\\").replace('"', '\\"')
        play_code = f'        await page.click("{selector_escaped}")\n'
        current_time = time.time() - self.start_time
        self.recorded_actions.append((current_time, play_code))
        logger.info(f"Recorded Playwright click action: {play_code.strip()}")

    async def save_input_data(
        self, selector: str, value: str, InteractionEvent: Any
    ) -> None:
        """Save input data to the database with retry logic and record Playwright code."""

        async def operation():
            async with self.Session() as session:
                async with session.begin():
                    time_delta = self.get_time_since_last_action()
                    clicked_element = InteractionEvent(
                        event_type="input",
                        xpath=selector,
                        class_name="input-event",
                        element_id="",
                        input_value=value,  # Storing the input value
                        time_since_last_action=time_delta,
                    )
                    session.add(clicked_element)
                    await session.commit()
            logger.info(f"Saved input data: Selector={selector}, Value={value}")

        await self._retry_with_backoff(operation)

        # Escape single quotes in the value to prevent syntax errors
        value_escaped = value.replace("'", "\\'")
        play_code = f"        await page.fill('{selector}', '{value_escaped}')\n"
        current_time = time.time() - self.start_time
        self.recorded_actions.append((current_time, play_code))
        logger.info(f"Recorded Playwright input action: {play_code.strip()}")

    async def save_scroll_data(
        self, scrollX: int, scrollY: int, InteractionEvent: Any
    ) -> None:
        """Save scroll data to the database with retry logic and record Playwright code."""

        async def operation():
            async with self.Session() as session:
                async with session.begin():
                    time_delta = self.get_time_since_last_action()
                    clicked_element = InteractionEvent(
                        event_type="scroll",
                        xpath=f"scrollX: {scrollX}, scrollY: {scrollY}",
                        class_name="scroll-event",
                        element_id="",
                        input_value=None,  # No input value for scroll events
                        time_since_last_action=time_delta,
                    )
                    session.add(clicked_element)
                    await session.commit()
            logger.info(f"Saved scroll data: scrollX={scrollX}, scrollY={scrollY}")

        await self._retry_with_backoff(operation)

        # Record scroll action in Playwright code
        # Correct Python syntax: pass the JavaScript as a string without arrow functions and semicolons
        play_code = (
            f"        await page.evaluate('window.scrollTo({scrollX}, {scrollY})')\n"
        )
        current_time = time.time() - self.start_time
        self.recorded_actions.append((current_time, play_code))
        logger.info(f"Recorded Playwright scroll action: {play_code.strip()}")

    async def save_key_data(self, key: str, InteractionEvent: Any) -> None:
        """Save key press data to the database with retry logic and record Playwright code."""

        async def operation():
            async with self.Session() as session:
                async with session.begin():
                    time_delta = self.get_time_since_last_action()
                    clicked_element = InteractionEvent(
                        event_type="keypress",
                        xpath=key,
                        class_name="key-event",
                        element_id="",
                        input_value=None,  # No input value for keypress events
                        time_since_last_action=time_delta,
                    )
                    session.add(clicked_element)
                    await session.commit()
            logger.info(f"Saved key press data: Key={key}")

        await self._retry_with_backoff(operation)

    async def save_navigate_data(self, url: str, InteractionEvent: Any) -> None:
        """Save navigation data to the database with retry logic and record Playwright code."""

        async def operation():
            async with self.Session() as session:
                async with session.begin():
                    time_delta = self.get_time_since_last_action()
                    clicked_element = InteractionEvent(
                        event_type="navigate",
                        xpath=None,
                        class_name=None,
                        element_id=None,
                        input_value=None,
                        additional_info=url,  # Storing the navigated URL
                        time_since_last_action=time_delta,
                    )
                    session.add(clicked_element)
                    await session.commit()
            logger.info(f"Saved navigation event: URL={url}")

        await self._retry_with_backoff(operation)
        current_time = time.time() - self.start_time

    def generate_selector(self, selector: str) -> str:
        """Ensure the selector is properly escaped."""
        return selector.replace("'", "\\'")

    async def save_xpaths_to_db(
        self, stop_flag: List[bool]
    ) -> None:
        self.session = self.Session()

        try:
            while not stop_flag[0]:
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("Task was cancelled.")
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Error occurred: {e}")
            await self.session.rollback()
        finally:
            await self.session.close()

    async def close(self) -> None:
        """Close the session if it's open."""
        if self.session:
            await self.session.close()
