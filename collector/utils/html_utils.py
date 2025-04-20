import os
from typing import Optional
from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from scrapy.http import HtmlResponse
from scrapy.selector import Selector
from collector.utils.file_utils import sanitize_filename, write_file
from collector.utils import logger
from os import makedirs
from os.path import join


def get_html_structure(soup, indent=0) -> str:
    structure = ""
    for element in soup.children:
        if isinstance(element, str):
            continue
        class_attr = (
            f' class="{" ".join(element.get("class"))}"' if element.get("class") else ""
        )
        structure += " " * indent + f"<{element.name}{class_attr}>\n"
        structure += get_html_structure(element, indent + 2)
    return structure


async def extract_html_elements(
    input_path: str,
    output_path: Optional[str] = None,
    unique: bool = False,
    output_format: str = "html",  # 'text' or 'html'
) -> str:
    """
    Extracts HTML structure from the given HTML file.

    Args:
        input_path (str): Path to the input HTML file.
        output_path (Optional[str]): Path to save the output list. If None, the list is not saved to a file.
        unique (bool): If True, only unique elements are listed.
        output_format (str): Format of the output file. 'text' for plain text, 'html' for HTML formatted list.

    Returns:
        str: The HTML structure extracted from the input file.
    """
    # Validate input file
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"The input file '{input_path}' does not exist.")

    # Read HTML content
    with open(input_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    structure = get_html_structure(soup)

    # If output_path is provided, write to the specified file
    if output_path:
        with open(output_path, "w", encoding="utf-8") as out_file:
            out_file.write(structure)

    return structure


async def extract_elements_from_string(html_content: str, unique: bool = False) -> str:
    """
    Extracts HTML structure from a given HTML string.

    Args:
        html_content (str): The HTML content as a string.
        unique (bool): If True, only unique elements are listed.

    Returns:
        str: The HTML structure extracted from the HTML string.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    structure = get_html_structure(soup)
    return structure


async def scrape_with_scrapy(
    page,
    html_counter: int,
    current_url: str,
    db_directory_path: str
) -> None:
    """
    A unified 'scrape_with_scrapy' method moved here from various web automation classes.
    """
    try:
        # Skip scraping if current_url contains "multion"
        if "multion" in current_url:
            logger.info("Current URL is a multion site; skipping scrape_with_scrapy.")
            return

        # Check if the page is already closed
        if page.is_closed():
            logger.error("Page is closed. Exiting scrape_with_scrapy.")
            return

        # Wait for network to be idle, log warning on timeout
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except PlaywrightTimeoutError:
            logger.warning(
                f"Timeout while waiting for network idle at {page.url}, proceeding with scraping."
            )

        # Get the page HTML and parse it
        page_html = await page.content()
        response = HtmlResponse(url=current_url, body=page_html, encoding="utf-8")
        selector = Selector(response)
        title = selector.xpath("//title/text()").get()
        logger.info(f"Page title: {title}")

        # Save the HTML to a file
        sanitized_url = sanitize_filename(current_url)
        html_dir = join(db_directory_path, "html")
        makedirs(html_dir, exist_ok=True)
        html_filename = join(html_dir, f"{sanitized_url}_{html_counter}.html")
        write_file(html_filename, page_html, mode="w", encoding="utf-8")
        logger.debug(f"HTML content saved to {html_filename}")

    except PlaywrightTimeoutError:
        logger.warning(f"Timeout during scraping process for {current_url}.")
    except Exception as e:
        logger.error(f"Failed to scrape page content: {e}")
        raise
