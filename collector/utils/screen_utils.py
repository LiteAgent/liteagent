import pyautogui
from . import logger


async def click_screen_coordinates(x: int, y: int) -> None:
    pyautogui.click(x, y)
    logger.info(f"Clicked on screen coordinates ({x}, {y})")


async def press_keys(keys: list) -> None:
    hotkeys = []
    single_keys = []
    for key in keys:
        if isinstance(key, list):
            hotkeys.append(key)
        else:
            single_keys.append(key)

    # Press hotkeys
    for hotkey in hotkeys:
        pyautogui.hotkey(*hotkey)
        logger.info(f"Pressed hotkey combination: {'+'.join(hotkey)}")

    # Press single keys
    for key in single_keys:
        if isinstance(key, str):
            pyautogui.typewrite(key)
            logger.info(f"Typed string: {key}")
        else:
            pyautogui.press(key.name)
            logger.info(f"Pressed key: {key.name}")
