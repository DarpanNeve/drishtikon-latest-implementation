# navigation/destination_input.py

import time
from core.tts_player import tts_main
from core.playback_controls import play
from core.stt import listen, listen_continuous
from core.tts import speak, speak_cached
from core.prompts import *
from core.priority_audio import AudioPriority


def get_source_and_destination(priority_audio):
    # Prompt user
    # priority_audio.request_play(
    #     speak_cached(
    #         "Please tell me your current location.",
    #         "source_prompt.wav"
    #     ),
    #     AudioPriority.NAVIGATION
    # )

    play(tts_main, navigation_src_p)

    source = listen_continuous()
    if not source:
        # priority_audio.request_play(
        #     speak_cached(
        #         "I did not hear the current location.",
        #         "src_error.wav"
        #     ),
        #     AudioPriority.NAVIGATION
        # )
        play(tts_main, navigation_src_err_p)
        return "Blossom Public School", "Lakshmi Road"
        # return None, None

    # priority_audio.request_play(
    #     speak_cached(
    #         "Please tell me your destination.",
    #         "destination_prompt.wav"
    #     ),
    #     AudioPriority.NAVIGATION
    # )

    play(tts_main, navigation_dest_p)

    destination = listen_continuous()
    if not destination:
        # priority_audio.request_play(
        #     speak_cached(
        #         "I did not hear the destination.",
        #         "destination_error.wav"
        #     ),
        #     AudioPriority.NAVIGATION
        # )
        play(tts_main, navigation_dest_err_p)
        return None, None

    # Confirm destination
    # priority_audio.request_play(
    #     speak(f"You are at {source} and want to go to {destination}."),
    #     AudioPriority.NAVIGATION
    # )
    navigation_announce_audio = speak(f"You are at {source} and want to go to {destination}.")
    play(tts_main, navigation_announce_audio)

    return source, destination
