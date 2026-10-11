import httpx


def get_json(url, params=None, headers=None):
    """
    GET a URL and return (data, None), or (None, reason) if it failed.
    """
    try:
        response = httpx.get(url, params=params, headers=headers, timeout=10)
    except httpx.HTTPError as e:
        return None, f"network error ({type(e).__name__})"
    if response.status_code != 200:
        return None, f"the service answered HTTP {response.status_code}"
    try:
        return response.json(), None
    except ValueError:
        return None, "the reply was not valid JSON"


def unavailable(what, reason):
    """
    The tool reply when data can't be fetched. Tell agent not to guess.
    """
    return f"{what} UNAVAILABLE: {reason}. Do not guess it; say it could not be checked."
