# navigation/navigate.py

import time
from core.tts import speak, speak_cached
from core.tts_player import tts_main
from core.priority_audio import PriorityAudioManager, AudioPriority

from navigation.destination_input import get_destination
from navigation.maps_client import get_route
from navigation.location_tracker import LocationTracker
from navigation.navigation_manager import NavigationManager


def main():
    priority_audio = PriorityAudioManager(tts_main)

    # ----------------------------
    # Get destination (STT)
    # ----------------------------
    destination = get_destination(priority_audio)
    if not destination:
        priority_audio.request_play(
            speak_cached("No destination provided.", "no_dest_provided.wav"),
            AudioPriority.SYSTEM
        )
        while priority_audio.tts.is_playing():
            time.sleep(0.05)
        return

    # ----------------------------
    # Get current location
    # ----------------------------
    tracker = LocationTracker()
    origin = tracker.get_current_location()

    # ----------------------------
    # Fetch route
    # ----------------------------
    route = get_route(origin_coords=origin, destination_text=destination)
    if not route:
        priority_audio.request_play(
            speak("Sorry, I could not find a route."),
            AudioPriority.SYSTEM
        )
        return

    # ----------------------------
    # Speak ETA
    # ----------------------------
    priority_audio.request_play(
        speak(f"Estimated time {route['duration']}, distance {route['distance']}."),
        AudioPriority.NAVIGATION
    )

    # ----------------------------
    # Start navigation manager
    # ----------------------------
    nav_manager = NavigationManager(
        steps=route["steps"],
        priority_audio=priority_audio
    )
    nav_manager.start()
    nav_manager.join()


if __name__ == "__main__":
    main()
