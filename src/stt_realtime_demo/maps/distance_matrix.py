import googlemaps
from datetime import datetime
import dotenv
import os

dotenv.load_dotenv()

gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))


def calculate_distance_matrix(origins, destinations, mode="driving", language="en", avoid="tolls", units="metric", departure_time=datetime.now()):
    return gmaps.distance_matrix(
        origins=origins,
        destinations=destinations,
        mode=mode,
        language=language,
        avoid=avoid,
        units=units,
        departure_time=departure_time,
    )


