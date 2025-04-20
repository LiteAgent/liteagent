import json
import os
from os.path import exists, join

from playwright.async_api import Browser, BrowserContext
from collector.utils.file_utils import sanitize_filename

from . import logger


async def load_cookies(
    browser: Browser, url: str, context: BrowserContext, cookies_dir: str
) -> None:
    """Load cookies for the current site if available."""
    if browser:
        # Sanitize the URL for filename
        sanitized_url = sanitize_filename(url)
        # Check if a cookies file exists for this domain in the cookies directory
        cookies_file = join(cookies_dir, f"{sanitized_url}_cookies.json")
        if exists(cookies_file):
            try:
                with open(cookies_file, "r") as f:
                    cookies = json.load(f)

                # Add the cookies to the browser context
                await context.add_cookies(cookies)
                logger.info(f"Cookies for {url} loaded from {cookies_file}")
            except Exception as e:
                logger.error(f"Failed to load cookies from {cookies_file}: {e}")
        else:
            logger.info(f"No cookies found for {url}")


async def save_cookies(
    browser: Browser, url: str, context: BrowserContext, cookies_dir: str
) -> None:
    """Save cookies for the current site."""
    if browser:
        # Ensure the cookies directory exists
        if not os.path.exists(cookies_dir):
            os.makedirs(cookies_dir)

        # Sanitize the URL for filename
        sanitized_url = sanitize_filename(url)
        # Save cookies to the cookies directory if the file does not already exist
        cookies_file = join(cookies_dir, f"{sanitized_url}_cookies.json")
        cookies = await context.cookies()
        if not cookies:
            logger.info("No cookies to save.")
            return
        with open(cookies_file, "w") as f:
            json.dump(cookies, f, indent=4)

        logger.info(f"Cookies for {url} saved to {cookies_file}")
    else:
        logger.error("Browser is not available. Cannot save cookies.")
