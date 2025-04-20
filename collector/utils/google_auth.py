import random
import time
import os
from dotenv import load_dotenv
from . import logger

load_dotenv()  # TODO Why is this needed if you already do it in main.py?
GMAIL_USER = os.getenv("GMAIL_USER", "your_email@gmail.com")
GMAIL_PASS = os.getenv("GMAIL_PASS", "your_password")


def _human_delay(base=0.5, variance=0.3):
    """
    Sleeps for a random time between [base, base + variance].
    Simulates human-like pauses.
    """
    delay = base + variance * random.random()
    time.sleep(delay)


# TODO Add types
async def google_login(context, page):
    # Sometimes pages list might be empty if no default page was opened yet
    if not context.pages:
        page = await context.new_page()
    else:
        page = context.pages[0]

    # 2. Inject script to hide `navigator.webdriver`.
    await page.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """
    )

    # 3. Navigate to Google login page
    logger.info("Navigating to Google Login...")
    await page.goto("https://accounts.google.com/")

    # We'll assume you haven't logged in yet, so we do the steps below:
    if "accounts.google.com" in page.url:
        logger.debug("Passing in Google Auth credentials")

        # Wait for email input (there are multiple selectors; pick a stable one)
        email_input = await page.wait_for_selector('input[type="email"]', timeout=10000)

        # Type the email with random delays between keystrokes
        for char in GMAIL_USER:
            await email_input.type(char, delay=random.randint(50, 120))
        _human_delay()

        # Click "Next"
        next_button = await page.wait_for_selector("#identifierNext")
        await next_button.click()
        _human_delay()

        # Wait for password field
        password_input = await page.wait_for_selector(
            'input[type="password"]', timeout=10000
        )

        # Type the password
        for char in GMAIL_PASS:
            await password_input.type(char, delay=random.randint(50, 120))
        _human_delay()

        # Click "Next" again
        password_next_button = await page.wait_for_selector("#passwordNext")
        await password_next_button.click()

        # Possibly handle 2FA or other flows here
        _human_delay()
        # Wait a few seconds for the login to process
        await page.wait_for_timeout(5000)

    logger.info("Google Login Complete")

    # Reset to a blank page
    await page.goto("about:blank")
