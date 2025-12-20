import threading
import time
import subprocess
import sys
import os

from core.priority_audio import AudioPriority
from core.logger import log
from core.utils import absolute_path


class NavigationManager(threading.Thread):
    """
    Orchestrates navigation guidance + object detection concurrently.
    Object detection audio ALWAYS has higher priority.
    """

    def __init__(self, steps, priority_audio):
        super().__init__(daemon=True)
        self.steps = steps
        self.priority_audio = priority_audio
        self.running = True
        self.yolo_process = None

    # --------------------------------------------------
    # START YOLO OBJECT DETECTION (Subprocess)
    # --------------------------------------------------
    def start_object_detection(self):
        """
        Starts YOLO detect.py as a subprocess.
        """
        detect_path = absolute_path("yolo/detect.py")

        if not os.path.exists(detect_path):
            log("NAV", "-", "YOLO detect.py not found")
            return

        try:
            self.yolo_process = subprocess.Popen(
                [sys.executable, detect_path]
            )
            log("NAV", "-", "YOLO detection started")
        except Exception as e:
            log("NAV", "-", f"Failed to start YOLO: {e}")

    # --------------------------------------------------
    # STOP YOLO OBJECT DETECTION
    # --------------------------------------------------
    def stop_object_detection(self):
        if self.yolo_process:
            try:
                self.yolo_process.terminate()
                time.sleep(0.3)
                self.yolo_process.kill()
                log("NAV", "-", "YOLO detection stopped")
            except:
                pass

    # --------------------------------------------------
    # NAVIGATION LOOP
    # --------------------------------------------------
    def run(self):
        """
        Runs navigation instructions while YOLO runs in parallel.
        """
        # Start object detection FIRST
        self.start_object_detection()

        self.priority_audio.request_play(
            "Navigation started. Follow the instructions.",
            AudioPriority.SYSTEM
        )

        for step in self.steps:
            if not self.running:
                break

            instruction = step.get("instruction")
            if not instruction:
                continue

            # Navigation instructions → lower priority than detection
            self.priority_audio.request_play(
                instruction,
                AudioPriority.NAVIGATION
            )

            # Simulated walking delay
            # Later replace with GPS-based distance tracking
            time.sleep(5)

        self.stop()

    # --------------------------------------------------
    # STOP EVERYTHING CLEANLY
    # --------------------------------------------------
    def stop(self):
        self.running = False
        self.stop_object_detection()

        self.priority_audio.request_play(
            "Navigation stopped.",
            AudioPriority.SYSTEM
        )
