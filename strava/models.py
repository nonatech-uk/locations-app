"""Strava type mapping and data transformation."""

# Map Strava sport_type / type → journal activity_type name
# None = skip (e.g. skiing, handled separately)
STRAVA_TYPE_MAP = {
    "Run": "running",
    "Trail Run": "running",
    "VirtualRun": "running",
    "Ride": "cycling",
    "VirtualRide": "cycling",
    "EBikeRide": "cycling",
    "GravelRide": "cycling",
    "MountainBikeRide": "cycling",
    "Swim": "swimming",
    "Walk": "walking",
    "Hike": "hiking",
    "AlpineSki": None,      # skip — handled separately
    "NordicSki": None,      # skip
    "BackcountrySki": None,  # skip
    "Snowboard": None,       # skip
    "Snowshoe": "walking",
    "Rowing": "rowing",
    "Canoeing": "canoeing",
    "Kayaking": "kayaking",
    "Surfing": "surfing",
    "Yoga": "yoga",
    "WeightTraining": "weights",
    "Workout": "workout",
    "Crossfit": "workout",
    "Elliptical": "workout",
    "StairStepper": "workout",
    "RockClimbing": "climbing",
    "Golf": "golf",
    "Sail": "sailing",
    "Skateboard": "skateboarding",
    "IceSkate": "skating",
    "InlineSkate": "skating",
    "Tennis": "tennis",
    "Badminton": "badminton",
    "Squash": "squash",
    "Pickleball": "pickleball",
    "TableTennis": "table_tennis",
    "Soccer": "football",
}


def map_strava_type(strava_type: str) -> str | None:
    """Map a Strava activity type to journal activity_type name.

    Returns None for types that should be skipped (e.g. skiing).
    Falls back to lowercase strava type if not in map.
    """
    if strava_type in STRAVA_TYPE_MAP:
        return STRAVA_TYPE_MAP[strava_type]
    return strava_type.lower()


def strava_to_ingest_payload(activity: dict) -> dict | None:
    """Convert a Strava API activity to journal ingest payload.

    Returns None if the type should be skipped.
    """
    activity_type = map_strava_type(activity.get("sport_type") or activity.get("type", ""))
    if activity_type is None:
        return None

    start_date = activity.get("start_date_local", "")
    date_part = start_date[:10] if start_date else None
    time_part = start_date[11:16] if len(start_date) >= 16 else None

    distance_m = activity.get("distance", 0)
    distance_km = round(distance_m / 1000, 2) if distance_m else None

    moving_time = activity.get("moving_time")
    elapsed_time = activity.get("elapsed_time")

    avg_speed = activity.get("average_speed", 0)
    avg_speed_kmh = round(avg_speed * 3.6, 1) if avg_speed else None

    max_speed = activity.get("max_speed", 0)
    max_speed_kmh = round(max_speed * 3.6, 1) if max_speed else None

    return {
        "strava_activity_id": activity["id"],
        "title": activity.get("name", ""),
        "activity_type": activity_type,
        "date": date_part,
        "start_time": time_part,
        "distance_km": distance_km,
        "duration_seconds": elapsed_time,
        "moving_time_seconds": moving_time,
        "elevation_gain": activity.get("total_elevation_gain"),
        "max_altitude": activity.get("elev_high"),
        "avg_speed_kmh": avg_speed_kmh,
        "max_speed_kmh": max_speed_kmh,
        "avg_heartrate": activity.get("average_heartrate"),
        "max_heartrate": activity.get("max_heartrate"),
        "calories": activity.get("calories"),
    }
