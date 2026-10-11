import os
from datetime import datetime, timedelta, timezone
from .fetch import get_json, unavailable


SEARCH_URL = "https://www.onemap.gov.sg/api/common/elastic/search"
ROUTE_URL = "https://www.onemap.gov.sg/api/public/routingsvc/route"

# Singapore time is UTC+8 all year.
SGT = timezone(timedelta(hours=8))


def find_place(name, token):
    """
    Look up a place with OneMap search.
    Returns ((place name, "lat,lon"), None) or (None, reason).
    """
    params = {"searchVal": name, "returnGeom": "Y", "getAddrDetails": "N", "pageNum": 1}
    data, error = get_json(SEARCH_URL, params=params, headers={"Authorization": token})
    if error:
        return None, error
    results = data.get("results") or []
    if not results:
        return None, f"OneMap found no place called '{name}'"
    top = results[0]
    return (top["SEARCHVAL"].title(), f"{top['LATITUDE']},{top['LONGITUDE']}"), None


def describe_leg(leg):
    """
    One leg of a trip, e.g. "bus 15 from Tampines Int to Bedok Int (20 min)".
    """
    minutes = max(1, round(leg["duration"] / 60))
    if leg["mode"] == "WALK":
        return f"walk {minutes} min to {leg['to']['name']}"
    mode = {"BUS": "bus", "SUBWAY": "MRT"}.get(leg["mode"], leg["mode"].lower())
    return f"{mode} {leg.get('route', '')} from {leg['from']['name']} to {leg['to']['name']} ({minutes} min)"


def journey(request: str = "") -> str:
    """
    Plans public transport (bus and MRT) between two places, leaving now.
    Input: "start -> destination", e.g. "Tampines Mall -> Gardens by the Bay".
    """
    start, arrow, end = request.partition("->")
    if not arrow or not start.strip() or not end.strip():
        return "Journey request not understood: write it as start -> destination, e.g. Tampines Mall -> Gardens by the Bay."

    # OneMap's route planner token
    token = os.getenv("ONEMAP_TOKEN", "").strip()
    if not token:
        return unavailable("Journey planning", "OneMap is not set up (ONEMAP_TOKEN is missing from .env)")

    # Get places
    places = []
    for name in (start.strip(), end.strip()):
        place, error = find_place(name, token)
        if error:
            return unavailable("Journey planning", error)
        places.append(place)
    (from_name, from_coords), (to_name, to_coords) = places

    # Build payload
    now = datetime.now(SGT)
    params = {
        "start": from_coords, "end": to_coords,
        "routeType": "pt", "mode": "TRANSIT",
        "date": now.strftime("%m-%d-%Y"), "time": now.strftime("%H:%M:%S"),
        "maxWalkDistance": 1000, "numItineraries": 3,
    }
    
    # Send request
    data, error = get_json(ROUTE_URL, params=params, headers={"Authorization": token})
    if error and "401" in error:
        return unavailable("Journey planning", "OneMap rejected ONEMAP_TOKEN (HTTP 401); it may have expired")
    if error:
        return unavailable("Journey planning", error)

    # Unpack 
    try:
        lines = [f"Public transport from {from_name} to {to_name}, leaving now ({now:%H:%M}):"]
        for number, trip in enumerate(data["plan"]["itineraries"][:3], 1):
            lines.append(f"Option {number}: {round(trip['duration'] / 60)} min")
            lines += [f"  - {describe_leg(leg)}" for leg in trip["legs"]]
    except (KeyError, IndexError, TypeError):
        return unavailable("Journey planning", "the reply was not in the expected format")

    if len(lines) == 1:
        return f"OneMap found no public transport route from {from_name} to {to_name}."
    return "\n".join(lines)
