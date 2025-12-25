# navigation/navigate.py

from core.playback_controls import play
from core.tts import speak
from core.tts_player import tts_main
from core.priority_audio import PriorityAudioManager
from core.prompts import dest_not_p, path_not_found_p

from navigation.destination_input import get_source_and_nearby_place
from navigation.maps_client import get_route
from navigation.navigation_logic import build_direction_gist


def main():
    priority_audio = PriorityAudioManager(tts_main)

    source, nearby_request = get_source_and_nearby_place(priority_audio)
    if not nearby_request:
        play(tts_main, dest_not_p)
        return

    route = get_route(origin_coords=source, nearby_query=nearby_request)
    if not route:
        play(tts_main, path_not_found_p)
        return

    # Speak ETA
    eta_audio = speak(
        f"The nearest {nearby_request} is {route['distance']} away. "
        f"It will take approximately {route['duration']} by walking."
    )
    play(tts_main, eta_audio)

    # Speak gist
    gist_text = build_direction_gist(route["steps"])
    gist_audio = speak(
        f"To reach {route['place_name']}, {gist_text}"
    )
    play(tts_main, gist_audio)


if __name__ == "__main__":
    main()
