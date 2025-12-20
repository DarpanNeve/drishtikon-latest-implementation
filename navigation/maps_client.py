import googlemaps
import os

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def get_route(origin_coords, destination_text):
    """
    Fetch walking route with turn-by-turn steps
    """
    try:
        directions = gmaps.directions(
            origin=origin_coords,
            destination=destination_text,
            mode="walking"
        )

        if not directions:
            return None

        route = directions[0]
        leg = route["legs"][0]

        return {
            "steps": leg["steps"],
            "duration": leg["duration"]["text"],
            "distance": leg["distance"]["text"]
        }

    except Exception as e:
        print(f"[Maps Error] {e}")
        return None