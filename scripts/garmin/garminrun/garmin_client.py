"""Talking to Garmin. The only module that imports garminconnect.

Each call has its own retry policy, because the consequences differ. A failed
details fetch costs a map, so it degrades to no map. A failed photo list could
cost the photos for good, so it raises.
"""

from __future__ import annotations

import time
from garminconnect import Garmin, GarminConnectAuthenticationError

from garminrun import config
from garminrun.config import START_DATE
from garminrun.geo import Point, extract_points

_sleep = time.sleep



DETAILS_DELAY_S = 0.75


def fetch_running_activities(client: Garmin) -> list[dict]:
    """Fetch all running activities on or after START_DATE, oldest first.

    get_activities_by_date returns the whole range in one response, so there is
    no pagination to do. (There used to be a `while True` around this with an
    unused limit and start, which never looped.)
    """
    try:
        activities = client.get_activities_by_date(START_DATE, None, "running")
    except GarminConnectAuthenticationError as exc:
        # client.load() only reads a file, so it succeeds even when Garmin has
        # stopped accepting the token. The first real call is where we find out.
        raise NeedsLogin(
            "the cached Garmin tokens are no longer accepted. Delete "
            "scripts/garmin/.garmin_tokens/ and run this once in a terminal."
        ) from exc

    # Oldest first, so --max-new imports the backlog in order.
    activities.sort(key=lambda a: a.get("startTimeLocal") or a.get("startTimeGMT") or "")
    return activities


def fetch_activity_points(client: Garmin, activity_id: int) -> list[Point]:
    """Return GPS+speed samples for an activity ([] if none, or on error).

    A missing map must never cost us the markdown post, so every failure here
    is a warning. garth raises for 429/5xx and the details payload shape is not
    contractual, hence the broad excepts.
    """
    details = None
    for attempt in (1, 2):
        try:
            details = client.get_activity_details(activity_id, maxchart=2000, maxpoly=4000)
            break
        except Exception as exc:  # noqa: BLE001 - never abort the import
            if attempt == 1:
                print(f"  details fetch failed for {activity_id} ({exc}); retrying")
                _sleep(5)
            else:
                print(f"  WARNING: details fetch failed for {activity_id}: {exc}")
                return []

    try:
        return extract_points(details or {})
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: could not parse GPS metrics for {activity_id}: {exc}")
        return []


class NeedsLogin(Exception):
    """Garmin wants an MFA code and there is nobody to type it."""


def authenticate(email: str, password: str, interactive: bool = True) -> Garmin:
    client = Garmin(email, password)
    tokenstore = config.PATHS.tokenstore
    if (tokenstore / "garmin_tokens.json").exists():
        client.client.load(str(tokenstore))
    else:
        if not interactive:
            raise NeedsLogin(
                "no cached Garmin tokens in scripts/garmin/.garmin_tokens/, and "
                "MFA needs a person at a keyboard. Run this once in a terminal:\n"
                "  uv run scripts/garmin/import_garmin_runs.py"
            )
        client.client.login(email, password, prompt_mfa=lambda: input("Enter MFA code: "))
        tokenstore.mkdir(parents=True, exist_ok=True)
        client.client.dump(str(tokenstore))
    print("Authenticated with Garmin Connect.")
    return client
