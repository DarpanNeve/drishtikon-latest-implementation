import sys
import os
import subprocess
import threading
import time

from core.stt import listen
from core.logger import log
from core.utils import absolute_path
from core.tts_player import tts_main
from core.prompts import *
from core.playback_controls import play
from core.priority_audio import AudioPriority, PriorityAudioManager

from core.navigation.destination_input import get_destination
from core.navigation.maps_client import get_route
from core.navigation.navigation_manager import NavigationManager
from core.navigation.location_tracker import LocationTracker

# ================================================================
# PROCESS TRACKING
# ================================================================
active_processes = []

priority_audio = PriorityAudioManager(tts_main)

# ================================================================
# EMERGENCY STOP
# ================================================================

def kill_all_processes():
    for p in active_processes[:]:
        try:
            p.terminate()
            p.kill()
        except:
            pass
    active_processes.clear()

def linux_stop_listener():
    while True:
        if os.path.exists("/tmp/stop.txt"):
            play(tts_main, emergency_stop_p)
            kill_all_processes()
            os._exit(0)
        time.sleep(1)

# ================================================================
# SUBPROCESS LAUNCHER
# ================================================================

def start_module(module_name: str):
    p = subprocess.Popen(
        [sys.executable, "-m", module_name]
    )
    active_processes.append(p)

    while p.poll() is None:
        time.sleep(0.1)

    active_processes.remove(p)


# ================================================================
# MAIN LOOP
# ================================================================

def main():
    threading.Thread(target=linux_stop_listener, daemon=True).start()
    play(tts_main, system_ready_p)

    attempt = 0
    while attempt < 3:
        cmd = listen()
        if not cmd:
            attempt += 1
            continue

        cmd = cmd.lower()

        # -----------------------------
        # READING
        # -----------------------------
        if "read" in cmd:
            attempt = 0
            play(tts_main, opening_reading_p)
            start_module("reading.read")

        # -----------------------------
        # OBJECT DETECTION
        # -----------------------------
        elif "detect" in cmd or "object" in cmd:
            attempt = 0
            play(tts_main, opening_detection_p)
            start_module("yolo.detect")

        # -----------------------------
        # NAVIGATION (NEW)
        # -----------------------------
        elif "navigate" in cmd or "navigation" in cmd:
            attempt = 0
            play(tts_main, navigation_p)

            destination = get_destination()
            if not destination:
                continue

            location_tracker = LocationTracker()
            current_location = location_tracker.get_current_location()

            route = get_route(
                origin_coords=current_location,
                destination_text=destination
            )

            if not route:
                priority_audio.request_play(
                    "Sorry, I could not find a route to that destination.",
                    AudioPriority.SYSTEM
                )
                continue

            # Speak ETA first
            priority_audio.request_play(
                f"Starting navigation. Estimated time {route['duration']}, distance {route['distance']}.",
                AudioPriority.NAVIGATION
            )

            nav_manager = NavigationManager(
                steps=route["steps"],
                priority_audio=priority_audio
            )

            nav_manager.start()
            nav_manager.join()

        # -----------------------------
        # EXIT
        # -----------------------------
        elif "exit" in cmd or "quit" in cmd:
            play(tts_main, goodbye_p)
            kill_all_processes()
            break

        else:
            attempt += 1
            play(tts_main, did_not_understand_p)
    if attempt >= 3:
        play(tts_main, goodbye_p)
if __name__ == "__main__":
    main()
