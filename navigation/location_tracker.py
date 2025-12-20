# navigation/location_tracker.py

class LocationTracker:
    """
    Mock location tracker (replace later with GPS).
    """

    def __init__(self):
        # Pune Railway Station (example)
        self.latitude = 18.5286
        self.longitude = 73.8746

    def get_current_location(self):
        return (self.latitude, self.longitude)
