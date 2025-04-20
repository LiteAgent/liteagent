import threading
import time
from os.path import join
import os

import cv2
import numpy as np
from mss import mss

from collector.utils import logger
from collector.utils.file_utils import create_video_writer

class Recorder:
    def __init__(self, video_dir, sanitized_task):
        self.video_dir = video_dir
        self.sanitized_task = sanitized_task
        self.recording = False
        self.recording_thread = None

    def start(self):
        self.recording = True
        self.recording_thread = threading.Thread(target=self._record_screen)
        self.recording_thread.start()

    def _record_screen(self):
        display = os.environ.get("DISPLAY")
        if not display:
            logger.error("DISPLAY environment variable is not set.")
            self.recording = False
            return

        with mss(display=display) as sct:
            if len(sct.monitors) < 2:
                logger.error("No monitors found to record.")
                self.recording = False
                return
            monitor = sct.monitors[1]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            # Set desired resolution
            desired_width = int(monitor["width"])
            desired_height = int(monitor["height"])
            video_path = join(self.video_dir, f"{self.sanitized_task}.mp4")
            out = create_video_writer(
                video_path, fourcc, 25.0, (desired_width, desired_height)
            )

            while self.recording:
                try:
                    img = sct.grab(monitor)
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    # Resize the frame to the desired resolution
                    frame = cv2.resize(frame, (desired_width, desired_height))
                    out.write(frame)
                except mss.exception.ScreenShotError as e:
                    logger.error(f"Screen capture failed: {e}")
                    self.recording = False
                    break
                time.sleep(0.04)
            out.release()

    def stop(self):
        self.recording = False
        if self.recording_thread:
            self.recording_thread.join()
