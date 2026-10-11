from .fetch import get_json, unavailable


URL = "https://api-open.data.gov.sg/v2/real-time/api/psi"

# NEA's PSI bands: (upper limit, label). Anything above 300 is Hazardous.
PSI_BANDS = [(50, "Good"), (100, "Moderate"), (200, "Unhealthy"), (300, "Very unhealthy")]


def psi_band(value):
    """
    NEA's label for a PSI reading, e.g. 156 -> "Unhealthy".
    """
    for limit, label in PSI_BANDS:
        if value <= limit:
            return label
    return "Hazardous"


def haze(_: str = "") -> str:
    """
    Returns the 24-hour PSI (haze) reading for each region
    """
    data, error = get_json(URL)
    if error:
        return unavailable("Haze (PSI)", error)

    try:
        item = data["data"]["items"][0]
        psi = item["readings"]["psi_twenty_four_hourly"]
    except (KeyError, IndexError, TypeError):
        return unavailable("Haze (PSI)", "the reply was not in the expected format")

    lines = [f"24-hour PSI at {item['timestamp'][11:16]} (higher is worse):"]
    lines += [f"- {region}: {value} ({psi_band(value)})" for region, value in psi.items()]
    return "\n".join(lines)
