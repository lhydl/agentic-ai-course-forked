from datetime import datetime, timedelta, timezone

from .fetch import get_json, unavailable


URL = "https://api-open.data.gov.sg/v2/real-time/api/twenty-four-hr-forecast"
SGT = timezone(timedelta(hours=8))


def weather(_: str = "") -> str:
    """
    Returns NEA's 24-hour forecast for Singapore: the current time, the overall
    outlook, then each part of the day for the five regions (north, south, east,
    west, central), marked today or tomorrow.
    """
    data, error = get_json(URL)
    if error:
        return unavailable("Weather forecast", error)

    # Without the current time, the model can't tell which period is "this afternoon".
    now = datetime.now(SGT)
    lines = [f"Now: {now:%A %d %b, %I:%M %p} (Singapore time)."]

    try:
        record = data["data"]["records"][0]
        general = record["general"]
        temp = general["temperature"]
        lines.append(f"24-hour forecast ({general['validPeriod']['text']}): "
                     f"{general['forecast']['text']}, {temp['low']}-{temp['high']} C.")
        for period in record["periods"]:
            start = datetime.fromisoformat(period["timePeriod"]["start"])
            day = "Tomorrow" if start.date() > now.date() else "Today"
            regions = "; ".join(f"{name} {r['text']}" for name, r in period["regions"].items())
            lines.append(f"- {day}, {period['timePeriod']['text']}: {regions}")
    except (KeyError, IndexError, TypeError, ValueError):
        return unavailable("Weather forecast", "the reply was not in the expected format")

    return "\n".join(lines)
