# navigation/destination_input.py

import time
from core.stt import listen
from core.tts import speak, speak_cached
from core.priority_audio import AudioPriority


def get_destination(priority_audio):
    # Prompt user
    priority_audio.request_play(
        speak_cached(
            "Please tell me your destination.",
            "destination_prompt.wav"
        ),
        AudioPriority.NAVIGATION
    )

    while priority_audio.tts.is_playing():
        time.sleep(0.05)

    destination = listen()
    if not destination:
        priority_audio.request_play(
            speak_cached(
                "I did not hear the destination.",
                "destination_error.wav"
            ),
            AudioPriority.NAVIGATION
        )
        return None

    # Confirm destination
    priority_audio.request_play(
        speak(f"You want to go to {destination}."),
        AudioPriority.NAVIGATION
    )

    return destination
