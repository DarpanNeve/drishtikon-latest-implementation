# navigation/maps_client.py

import os
import googlemaps

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def find_nearest_place(source, query):
    """
    Uses Places API to find nearest matching place.
    """
    places = gmaps.places(
        query=source + " " + query,
        location=source,
        radius=2000
    )

    if not places["results"]:
        return None

    place = places["results"][0]
    location = place["geometry"]["location"]

    return {
        "name": place["name"],
        "coords": (location["lat"], location["lng"])
    }


def get_route(origin_coords, nearby_query):
    """
    1. Find nearest place
    2. Fetch walking route to it
    """
    try:
        nearest = find_nearest_place(origin_coords, nearby_query)
        if not nearest:
            return None

        directions = gmaps.directions(
            origin=origin_coords,
            destination=nearest["coords"],
            mode="walking"
        )

        if not directions:
            return None

        leg = directions[0]["legs"][0]

        steps = []
        for step in leg["steps"]:
            steps.append({
                "instruction": step["html_instructions"],
                "distance": step["distance"]["text"]
            })

        return {
            "place_name": nearest["name"],
            "steps": steps,
            "duration": leg["duration"]["text"],
            "distance": leg["distance"]["text"]
        }

    except Exception as e:
        print(f"[Maps Error] {e}")
        return None
