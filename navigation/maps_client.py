# navigation/maps_client.py

import os
import googlemaps

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def get_route(origin_coords, destination_text):
    """
    Fetch walking route and return simplified structure.
    """
    try:
        directions = gmaps.directions(
            origin=origin_coords,
            destination=destination_text,
            mode="walking"
        )

        if not directions:
            return None

        leg = directions[0]["legs"][0]

        steps = []
        for step in leg["steps"]:
            instruction = step["html_instructions"]
            distance = step["distance"]["text"]
            steps.append({
                "instruction": f"{instruction}. Walk for {distance}."
            })

        return {
            "steps": steps,
            "duration": leg["duration"]["text"],
            "distance": leg["distance"]["text"],
        }

    except Exception as e:
        print(f"[Maps Error] {e}")
        return None
