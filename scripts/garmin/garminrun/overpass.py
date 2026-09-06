"""The OpenStreetMap basemap: the query, its cache, and its mirrors.

Overpass is free, anonymous and rate-limited per IP; there is no API key. So:
query only the tags we draw, cache every response, and try mirrors when one
endpoint fails.

The network and the clock are reached through the two module-level hooks at the
bottom, `_transport` and `_sleep`. A test swaps them; nothing else does.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from garminrun import config
from garminrun.svg import GREEN_LANDUSE, GREEN_LEISURE, ROAD_WIDTHS
from garminrun.track import Track


# OpenStreetMap basemap, fetched from Overpass at generation time and drawn as
# vector. Overpass is free, anonymous and rate-limited per IP; there is no API
# key. So: query only the tags we draw, cache every response, try mirrors when
# one endpoint fails, and fall back to a plain map only as a last resort.
# Tried in order. Probed 2026-08-14 with a small Toronto query; the times are
# that probe's round trip, and every one of these returned the same 484 ways.
#   overpass-api.de           0.6 s
#   overpass.private.coffee   3.0 s
#   overpass.kumi.systems     3.7 s
#   maps.mail.ru              9.7 s
# Deliberately absent: overpass.osm.ch answers 200 with ZERO elements outside
# Switzerland, and other regional instances behave the same way. A silent empty
# answer is worse than a failure, because it would cache an empty basemap. See
# the element check in fetch_basemap. Unreachable at probe time: overpass.osm.jp,
# overpass.openstreetmap.ru, overpass.osm.vin, overpass.nchc.org.tw.
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)


# Reports the free query slots for the main endpoint, and when the next frees up.
OVERPASS_STATUS_URL = "https://overpass-api.de/api/status"


OVERPASS_STATUS_MAX_WAIT_S = 120.0


OVERPASS_TIMEOUT_S = 90       # server-side budget, sent in the query


OVERPASS_READ_TIMEOUT_S = 180


OVERPASS_DELAY_S = 2.5        # pause after each query that hit the network


OVERPASS_ATTEMPTS = 2         # per endpoint


OVERPASS_BACKOFF_MAX_S = 60.0  # extra pause added after a refusal, per query


# Grows on refusal, decays on success. State rather than a bare global, so a
# test can reset it and one refusal cannot leak into the next test.
_penalty = 0.0


def reset_penalty() -> None:
    """Forget every refusal so far. For tests, and for a fresh run."""
    global _penalty
    _penalty = 0.0


def _overpass_query(south: float, west: float, north: float, east: float) -> str:
    """Ask only for the tags we draw; the response is several MB otherwise."""
    bbox = f"{south:.5f},{west:.5f},{north:.5f},{east:.5f}"
    roads = "|".join(ROAD_WIDTHS)
    leisure = "|".join(sorted(GREEN_LEISURE))
    landuse = "|".join(sorted(GREEN_LANDUSE))
    return f"""[out:json][timeout:{OVERPASS_TIMEOUT_S}];
(
  way["highway"~"^({roads})$"]({bbox});
  way["waterway"~"^(river|stream|canal)$"]({bbox});
  way["natural"~"^(water|coastline)$"]({bbox});
  way["leisure"~"^({leisure})$"]({bbox});
  way["landuse"~"^({landuse})$"]({bbox});
  relation["natural"="water"]({bbox});
);
out geom;"""


def _cache_path(query: str) -> Path:
    """Cache file for a query. Keyed by the query text, so changing the tag
    filters or the bounding box misses the cache automatically."""
    digest = hashlib.sha256(query.encode()).hexdigest()[:16]
    return config.PATHS.overpass_cache / f"{digest}.json.gz"


def _cache_read(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:  # noqa: BLE001 - a bad cache file must not stop us
        print(f"  ignoring unreadable cache {path.name}: {exc}")
        return None


def _cache_write(path: Path, raw: bytes) -> None:
    config.PATHS.overpass_cache.mkdir(parents=True, exist_ok=True)
    try:
        with gzip.open(path, "wb") as handle:
            handle.write(raw)
    except Exception as exc:  # noqa: BLE001
        print(f"  could not cache the response: {exc}")


# ---------------------------------------------------------------------------
# The outside world
# ---------------------------------------------------------------------------

# Every network call and every pause this module makes goes through one of
# these three. A test replaces them, which is what makes the mirror fallback
# and the cache rules testable at all: the real thing queries four endpoints
# and sleeps for tens of seconds.


def _post(url: str, query: str) -> bytes:
    """POST a query to one Overpass endpoint and return the raw body."""
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "jonalmeida.github.com route maps (personal blog)"},
    )
    with urllib.request.urlopen(request, timeout=OVERPASS_READ_TIMEOUT_S) as response:
        return response.read()


def _get(url: str) -> str:
    """GET a URL as text. Used for the status endpoint only."""
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read().decode("utf-8", "replace")


_sleep = time.sleep


def wait_for_overpass_slot() -> None:
    """Wait until the main endpoint reports a free query slot.

    The status endpoint gives the slot count and the exact reset time, so we can
    wait the right amount instead of guessing. It is advisory: any problem
    reading it means we just go ahead and query.
    """
    try:
        text = _get(OVERPASS_STATUS_URL)
    except Exception:  # noqa: BLE001
        return

    free = re.search(r"(\d+) slots? available now", text)
    if free and int(free.group(1)) > 0:
        return
    waits = [int(seconds) for seconds in re.findall(r"in (\d+) seconds", text)]
    if waits:
        wait = min(min(waits) + 1.0, OVERPASS_STATUS_MAX_WAIT_S)
        print(f"  Overpass reports no free slot; waiting {wait:.0f} s")
        _sleep(wait)


def _overpass_request(url: str, query: str) -> bytes | None:
    """One endpoint, with retries and a growing penalty. None when it fails."""
    global _penalty

    for attempt in range(1, OVERPASS_ATTEMPTS + 1):
        try:
            return _post(url, query)
        except Exception as exc:  # noqa: BLE001 - the map is worth more than the background
            # A 429, or a refused connection, means we are querying too fast.
            # Slow every later query down as well, or one rate limit strips the
            # basemap from every remaining map in the run.
            _penalty = min(OVERPASS_BACKOFF_MAX_S, _penalty * 2 + 5.0)
            host = urllib.parse.urlparse(url).netloc
            if attempt < OVERPASS_ATTEMPTS:
                wait = 15.0 * attempt + _penalty
                print(f"  {host} failed ({exc}); waiting {wait:.0f} s and retrying")
                _sleep(wait)
            else:
                print(f"  {host} failed ({exc})")
    return None


def fetch_basemap(track: Track, use_cache: bool = True) -> dict | None:
    """Fetch OSM ways for the visible area. None when every endpoint fails.

    A missing basemap only costs us the background, so failure here is a warning
    and the map still gets drawn.
    """
    global _penalty

    query = _overpass_query(*track.bounds())
    path = _cache_path(query)
    if use_cache:
        cached = _cache_read(path)
        if cached is not None:
            print(f"  basemap: from cache ({path.name}, no query needed)")
            return cached

    for index, url in enumerate(OVERPASS_URLS):
        if index == 0:
            wait_for_overpass_slot()
        else:
            print(f"  trying {urllib.parse.urlparse(url).netloc}")
        host = urllib.parse.urlparse(url).netloc
        raw = _overpass_request(url, query)
        if raw is None:
            continue

        try:
            data = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            print(f"  {host} returned something unreadable ({exc})")
            continue

        # A regional instance answers 200 with an empty element list for a bbox
        # outside its extract. Treat that as a failure: caching it would leave a
        # map with a credit line and no basemap. (A genuinely empty answer is
        # possible far from any road, and then every endpoint agrees and we draw
        # the plain route.)
        if not data.get("elements"):
            print(f"  {host} returned no elements for this area; trying the next endpoint")
            continue

        print(f"  basemap: {len(raw) / 1024:.0f} KB from {host}")
        _cache_write(path, raw)
        # Ease off the penalty once queries succeed again.
        _penalty = max(0.0, _penalty / 2 - 1.0)
        _sleep(OVERPASS_DELAY_S + _penalty)
        return data

    print("  WARNING: no basemap from any endpoint; drawing the route alone")
    return None
