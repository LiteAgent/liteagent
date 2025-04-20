import argparse
import asyncio
import platform
import signal
import sys
import os
import glob

from dotenv import load_dotenv
from collector.utils.error_handler import stop_flag, timeout_handler
from collector.utils.logging import setup_logger, print_browser_and_js_logs
from collector.validate import validate_args
from collector.web_automation_factory import create_web_automation

from collector.utils import logger
from collector.args_parser import build_parser


async def run_task_with_semaphore(args, semaphore):
    """Control task execution with semaphore for concurrency limit."""
    async with semaphore:  # Ensure concurrency limit with semaphore
        await main_task(args)


async def main_task(args):
    """Main task logic for the web automation."""
    logger.info(f"Starting the application for site: {args.site} and task: {args.task}")

    web_automation = None  # Initialize to None for safety

    try:
        web_automation = create_web_automation(args)
        await web_automation()

        task_coroutines = web_automation.get_tasks(stop_flag)
        tasks = [asyncio.create_task(coroutine) for coroutine in task_coroutines]

        # Set a timeout handler for the task
        if platform.system() != "Windows":  # No SIGALRM on Windows
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(args.timeout)

        # Run all tasks concurrently and set a timeout
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=args.timeout)

        # Monitor the task loop and print logs
        while not stop_flag[0]:
            await asyncio.sleep(0.5)
            if web_automation and hasattr(web_automation, "page"):
                print_browser_and_js_logs(web_automation.page)

        # Stop remaining tasks when stop_flag is set
        if stop_flag[0]:
            logger.info("Stopping remaining tasks due to stop_flag.")
            try:
                await web_automation.close_browser()  # TODO May lead to issue: Closing browser twice
            except Exception as e:
                logger.exception(f"Error while closing the browser: {e}")
            for task in tasks:
                task.cancel()

    except asyncio.TimeoutError:
        logger.debug("A timeout occurred, stopping gracefully.")
    except ValueError as e:
        logger.exception(f"Value error: {e}")
        raise
    except RuntimeError as e:
        logger.exception(f"Runtime error: {e}")
        raise
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise
    finally:
        # Call cleanup_tasks instead of duplicating cleanup code
        await cleanup_tasks(web_automation, [])


async def cleanup_tasks(web_automation, pending_tasks):
    """Perform cleanup tasks and handle pending tasks."""
    logger.info("Closing database and browser resources...")

    try:
        if web_automation:
            web_automation.stop_screen_recording()
            await asyncio.shield(web_automation.database_manager.close())
            await asyncio.shield(web_automation.close_browser())
            # await asyncio.shield(web_automation.save_playwright_autogen())  # TODO Comment back when stable
    except Exception as e:
        logger.exception(f"Error during resource cleanup: {e}")

    if pending_tasks:
        logger.info("Cancelling remaining tasks...")
        for task in pending_tasks:
            task.cancel()

        # Wait for tasks to finish with timeout
        done, pending = await asyncio.wait(
            pending_tasks, timeout=10, return_when=asyncio.ALL_COMPLETED
        )

        # Log any tasks that failed to complete before timeout
        if pending:
            logger.warning(f"Timeout: {len(pending)} tasks did not complete in time.")

        for task in done:
            try:
                exc = task.exception()
                if exc and not isinstance(exc, asyncio.CancelledError):
                    logger.exception(f"Error in task: {exc}")
            except asyncio.CancelledError:
                logger.debug(f"Task {task} was cancelled.")
            except Exception as e:
                logger.exception(f"Error when checking task exception: {e}")
    else:
        logger.info("No pending tasks to clean up.")

    if web_automation and hasattr(web_automation, "db_directory_path"):
        lock_files = glob.glob(
            os.path.join(web_automation.db_directory_path, "**", "*.lock"),
            recursive=True,
        )
        for lock_file in lock_files:
            os.remove(lock_file)
        logger.info("Removed all .lock files from db_directory_path.")

    for lock_file in glob.glob("*.lock"):
        os.remove(lock_file)

    logger.info("Cleanup completed.")


async def main_cleanup(web_automation):
    """Cancel remaining tasks and initiate cleanup."""
    # Collect remaining tasks
    pending_tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    # Clean up resources and cancel tasks
    await cleanup_tasks(web_automation, pending_tasks)


def handle_sigint(loop):
    """Handle SIGINT signal for graceful shutdown."""
    logger.info("Received Ctrl + C (SIGINT), initiating graceful shutdown...")
    global stop_flag  # TODO Remove this anti-pattern (use a set and not a global)
    stop_flag[0] = True
    for task in asyncio.all_tasks(loop):
        task.cancel()


async def run_in_parallel(task_list, concurrency):
    """Run tasks in parallel with a concurrency limit."""
    semaphore = asyncio.Semaphore(concurrency)  # Control concurrency level
    # Run all tasks with the concurrency limit
    await asyncio.gather(
        *[run_task_with_semaphore(args, semaphore) for args in task_list],
        return_exceptions=True,  # To handle exceptions without stopping all tasks
    )


def shutdown(loop):
    """Handle shutdown of the event loop to avoid errors during Ctrl+C."""
    logger.info("Shutting down the event loop...")
    for task in asyncio.all_tasks(loop):
        task.cancel()


if __name__ == "__main__":
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args()
    validate_args(args, parser)

    # Initialize logger with agent_method
    setup_logger(name="liteagent", agent_method=args.agent_method)  # TODO Move this to package level __main__.py

    task_list = [
        argparse.Namespace(**vars(args)) for _ in range(getattr(args, "total_tasks", 1))
    ]

    try:
        loop = asyncio.get_event_loop()

        if platform.system() != "Windows":  # Signal handling only on Unix-like systems
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, shutdown, loop)

        loop.run_until_complete(
            run_in_parallel(task_list, getattr(args, "concurrency", 1))
        )
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
    finally:
        logger.info("Running cleanup...")
        try:
            # Ensure all tasks are completed before closing the loop
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()

            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

        finally:
            # Stop and close the loop
            loop.stop()
            loop.close()

        logger.info("Application has exited gracefully.")
        sys.stdout.flush()
        sys.exit(0)
