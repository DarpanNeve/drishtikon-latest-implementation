import time
import os
import sys
import select

from core.prompts import goodbye_p, generating_answer_p, stopping_summary_p
from core.tts_player import tts_main

# PLAY AUDIO
def play(tts=tts_main, audio_file_name=goodbye_p):
    tts.play(audio_file_name)
    tts.wait()

# NON-BLOCKING PLAY (KEYPRESS)
def non_blocking_play(tts=tts_main, audio_file_name=generating_answer_p, cmd_to_stop_audio_file="Press 's' to stop response", stop_audio_file_name=stopping_summary_p):
    tts_main.play(audio_file_name)
    print(cmd_to_stop_audio_file)
    while True:
        if not tts_main.is_playing():
            break
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.readline().strip().lower() == "s":
                play(tts_main, stop_audio_file_name)
                break