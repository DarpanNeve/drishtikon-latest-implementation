import sys
import os
import subprocess
import threading
import time

# Ensure project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.stt import listen
from core.logger import log
from core.utils import absolute_path
from core.tts_player import tts_main
from core.prompts_main_controller import (
    system_ready_p,
    opening_reading_p,
    opening_detection_p,
    goodbye_p,
    did_not_understand_p,
    emergency_stop_p,
    module_not_found_p,
    launch_error_p
)

# ================================================================
# PROCESS TRACKING
# ================================================================
active_processes = []

# ================================================================
# EMERGENCY STOP (RPi Safe)
# ================================================================

def kill_all_processes():
    """Force-kills all active subprocesses."""
    print("[STOP] Terminating subprocesses...")

    for p in active_processes[:]:
        try:
            p.terminate()
            time.sleep(0.3)
            p.kill()
        except:
            pass

    active_processes.clear()

    # Close OpenCV windows (if any)
    try:
        import cv2
        cv2.destroyAllWindows()
    except:
        pass

    print("[STOP] Subprocesses terminated.")


def linux_stop_listener():
    """
    On Raspberry Pi, there is no global keyboard hook.
    Trigger emergency stop by creating /tmp/stop.txt.
    """
    print("[STOP] Linux STOP listener active (create /tmp/stop.txt to force stop).")

    while True:
        if os.path.exists("/tmp/stop.txt"):
            print("[STOP] Emergency stop signal detected via /tmp/stop.txt.")

            tts_main.stop()
            time.sleep(1.0)

            tts_main.play(emergency_stop_p)
            while tts_main.is_playing():
                time.sleep(0.05)

            kill_all_processes()
            os._exit(0)

        time.sleep(1)


# ================================================================
# MODULE LAUNCHER
# ================================================================

def start_process(relative_path):
    """Launch reading/yolo modules as subprocesses."""
    target = absolute_path(relative_path)

    if not os.path.exists(target):
        print(f"[MAIN] Missing module: {relative_path}")

        tts_main.stop()
        time.sleep(1.0)

        tts_main.play(module_not_found_p)
        while tts_main.is_playing():
            time.sleep(0.05)

        log("MAIN", relative_path, "Missing module")
        return

    try:
        p = subprocess.Popen([sys.executable, target])
        active_processes.append(p)

        # Wait until the process exits
        while p.poll() is None:
            time.sleep(0.1)

        active_processes.remove(p)

    except Exception as e:
        log("MAIN", relative_path, f"Launch error: {e}")

        tts_main.stop()
        time.sleep(1.0)

        tts_main.play(launch_error_p)
        while tts_main.is_playing():
            time.sleep(0.05)


# ================================================================
# MAIN LOOP
# ================================================================

def main():
    # Start STOP listener thread
    threading.Thread(target=linux_stop_listener, daemon=True).start()

    # Speak intro
    tts_main.stop()
    time.sleep(1.0)
    tts_main.play(system_ready_p)

    print("[MAIN] Awaiting commands...")

    while True:
        cmd = listen()
        if not cmd:
            continue

        cmd = cmd.lower().strip()
        print(f"[MAIN] Heard: {cmd}")

        # -----------------------------
        # READING MODULE
        # -----------------------------
        if "read" in cmd:
            tts_main.stop()
            time.sleep(1.0)
            tts_main.play(opening_reading_p)
            while tts_main.is_playing():
                time.sleep(0.05)

            log("MAIN", "-", "Launch reading")
            start_process("reading/read.py")
            continue

        # -----------------------------
        # OBJECT DETECTION MODULE
        # -----------------------------
        if "detect" in cmd or "object" in cmd:
            tts_main.stop()
            time.sleep(1.0)
            tts_main.play(opening_detection_p)
            while tts_main.is_playing():
                time.sleep(0.05)

            log("MAIN", "-", "Launch YOLO")
            start_process("yolo/detect.py")
            continue

        # -----------------------------
        # EXIT SYSTEM
        # -----------------------------
        if "exit" in cmd or "quit" in cmd:
            tts_main.stop()
            time.sleep(1.0)

            tts_main.play(goodbye_p)
            while tts_main.is_playing():
                time.sleep(0.05)

            kill_all_processes()
            break

        # -----------------------------
        # UNKNOWN COMMAND
        # -----------------------------
        tts_main.stop()
        time.sleep(1.0)

        tts_main.play(did_not_understand_p)
        while tts_main.is_playing():
            time.sleep(0.05)

        log("MAIN", "-", f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
