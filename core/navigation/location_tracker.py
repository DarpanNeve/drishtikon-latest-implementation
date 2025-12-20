import time

class LocationTracker:
    """
    Mock location tracker for testing navigation logic.
    Uses hardcoded coordinates.
    """

    def __init__(self):
        # Pune Railway Station
        self.latitude = 18.5286
        self.longitude = 73.8746

    def get_current_location(self):
        """
        Returns current location as (lat, lon)
        """
        return (self.latitude, self.longitude)

    def simulate_movement(self):
        """
        Fake movement for testing
        """
        time.sleep(5)
        self.latitude += 0.00005
        self.longitude += 0.00005
