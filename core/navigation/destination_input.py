from core.stt import listen
from core.priority_audio import AudioPriority
from core.tts import speak, speak_cached
from core.playback_controls import play
from core.tts_player import tts_main

def get_destination():
    destination_prompt = speak_cached(
        "Please tell me your destination",
        "destination_prompt.wav"
    )

    play(tts_main, destination_prompt)

    destination = listen()

    if not destination:
        destination_error =speak_cached(
            "I did not hear the destination. Please try again.",
            "destination_error.wav"
        )
        play(tts_main, destination_error)
        return None

    destination_success = speak(
        f"You want to go to {destination}. Starting navigation.",
    )

    play(tts_main, destination_success)

    return destination