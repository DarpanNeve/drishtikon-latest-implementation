import time
import os
import sys
import select

from core.prompts import goodbye_p, generating_answer_p, stopping_response_p, pause_beep
from core.tts_player import tts_main

# ================================================================
# CROSS-PLATFORM NON-BLOCKING KEY READ
# ================================================================
if os.name == "nt":
    import msvcrt

    def read_key_nonblocking():
        if msvcrt.kbhit():
            return msvcrt.getwch().lower()
        return None
else:
    def read_key_nonblocking():
        try:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                return sys.stdin.read(1).lower()
        except Exception:
            return None
        return None

def wait_for_key(valid_keys=None, sleep=0.05):
    while True:
        key = read_key_nonblocking()
        if key:
            if valid_keys is None or key in valid_keys:
                return key
        time.sleep(sleep)
# ================================================================
# PLAY AUDIO (BLOCKING)
# ================================================================
def play(tts=tts_main, audio_file_name=goodbye_p):
    tts.play(audio_file_name)
    tts.wait()


# ================================================================
# NON-BLOCKING PLAY (KEYPRESS)
# ================================================================
def non_blocking_play(
    tts=tts_main,
    audio_file_name=generating_answer_p,
    cmd_to_stop_audio_file="Press 's' to stop response",
    stop_audio_file_name=stopping_response_p,
    in_a_loop = False
):
    tts.play(audio_file_name)
    print(cmd_to_stop_audio_file)

    while True:
        if not tts.is_playing():
            break

        key = read_key_nonblocking()
        if key == "s":
            if in_a_loop:
                play(tts_main, pause_beep)
                return in_a_loop
            play(tts, stop_audio_file_name)
            # time.sleep(1.5)
            break

        time.sleep(0.05)  # avoid busy loop
