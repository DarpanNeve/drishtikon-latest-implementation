# navigation/navigation_manager.py

import threading
import time

from core.playback_controls import non_blocking_play, play
from core.tts_player import tts_main
# from core.priority_audio import AudioPriority
from core.tts import speak
from core.prompts import navigation_stop_p


class NavigationManager(threading.Thread):
    """
    Runs navigation instructions while object detection
    runs in parallel as a subprocess.

    Audio priority rules:
    - DETECTION > NAVIGATION
    - SYSTEM can interrupt everything
    """

    def __init__(self, steps, priority_audio):
        super().__init__(daemon=True)

        self.steps = steps                    # list of navigation steps
        self.priority_audio = priority_audio  # PriorityAudioManager
        self.running = True
        self.yolo_process = None

    # --------------------------------------------------
    # START YOLO OBJECT DETECTION (SUBPROCESS)
    # --------------------------------------------------
    # def start_object_detection(self):
    #     """
    #     Starts YOLO detect.py as a separate process.
    #     """
    #     detect_module = "yolo.detect"

    #     try:
    #         self.yolo_process = subprocess.Popen(
    #             [sys.executable, "-m", detect_module]
    #         )
    #         log("NAV", "-", "YOLO object detection started")
    #     except Exception as e:
    #         log("NAV", "-", f"Failed to start YOLO detection: {e}")
    #         self.yolo_process = None

    # --------------------------------------------------
    # STOP YOLO OBJECT DETECTION
    # --------------------------------------------------
    # def stop_object_detection(self):
    #     """
    #     Terminates YOLO subprocess cleanly.
    #     """
    #     if not self.yolo_process:
    #         return

    #     try:
    #         self.yolo_process.terminate()
    #         time.sleep(0.3)
    #         self.yolo_process.kill()
    #         log("NAV", "-", "YOLO object detection stopped")
    #     except Exception as e:
    #         log("NAV", "-", f"Error stopping YOLO: {e}")
    #     finally:
    #         self.yolo_process = None

    # --------------------------------------------------
    # MAIN NAVIGATION LOOP
    # --------------------------------------------------
    def run(self):
        """
        Main thread execution.
        """
        # Start object detection first
        # self.start_object_detection()

        # Announce navigation start
        # self.priority_audio.request_play(
        #     speak_cached(
        #         "Navigation started. Follow the instructions.",
        #         "nav_started.wav"
        #     ),
        #     AudioPriority.SYSTEM
        # )

        # Iterate through navigation steps
        for step in self.steps:
            if not self.running:
                break

            instruction = step.get("instruction")
            if not instruction:
                continue

            # Navigation audio (lower priority than detection)
            # self.priority_audio.request_play(
            #     speak(instruction),
            #     AudioPriority.NAVIGATION
            # )

            instruction_audio = speak(instruction)
            wants_to_break_loop = non_blocking_play(tts_main, instruction_audio, in_a_loop=True)
            if wants_to_break_loop:
                self.stop()
                return

            # Simulated walking delay
            # (Later replaced by GPS / distance tracking)
            # time.sleep(5)

        # Navigation finished
        self.stop()

    # --------------------------------------------------
    # STOP EVERYTHING CLEANLY
    # --------------------------------------------------
    def stop(self):
        """
        Stops navigation and object detection.
        """
        self.running = False

        # self.stop_object_detection()

        # self.priority_audio.request_play(
        #     speak_cached(
        #         "Navigation stopped.",
        #         "nav_stopped.wav"
        #     ),
        #     AudioPriority.SYSTEM
        # )
        # while self.priority_audio.tts.is_playing():
        #     time.sleep(0.05)

        play(tts_main, navigation_stop_p)
