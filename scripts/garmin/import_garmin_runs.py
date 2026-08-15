# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "garminconnect==0.3.2",
#   "python-dotenv",
# ]
# ///

"""Import Garmin running activities to Zola markdown files.

Usage:
    uv run scripts/garmin/import_garmin_runs.py                   # import new runs + maps
    uv run scripts/garmin/import_garmin_runs.py --no-maps         # skip route maps
    uv run scripts/garmin/import_garmin_runs.py --backfill-maps   # maps for imported runs
    uv run scripts/garmin/import_garmin_runs.py --selftest        # no credentials needed

Credentials: set GARMIN_EMAIL and GARMIN_PASSWORD in environment or
scripts/garmin/.env. On first run, Garmin MFA will prompt interactively;
subsequent runs use the cached tokens in scripts/garmin/.garmin_tokens/.

Key behaviours:
  - First run prompts for MFA interactively; later runs use the cached tokens
  - Fetches all running activities since 2026-03-07 via get_activities_by_date
  - Skips IDs in garmin_ignore.txt or already in garmin_imported.json
  - Writes content/runs/YYYY-MM-DD-run-YYYY-MM-DD.md (or -2, -3 for several
    runs on the same day)
  - Writes static/runs/maps/<activity_id>.svg: the GPS route, coloured by speed,
    over an OpenStreetMap basemap. This costs one get_activity_details call and
    one Overpass query per imported activity.
  - Cuts a random 400-800 m off each end of the route, so the real start and
    finish never reach the file. Use --no-privacy-trim to keep the whole track.
  - Saves imported IDs back to garmin_imported.json after each run
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import random
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import NamedTuple

from dotenv import load_dotenv
from garminconnect import Garmin

SCRIPTS_DIR = Path(__file__).parent
CONTENT_RUNS_DIR = SCRIPTS_DIR.parent.parent / "content" / "runs"
IMPORTED_FILE = SCRIPTS_DIR / "garmin_imported.json"
IGNORE_FILE = SCRIPTS_DIR / "garmin_ignore.txt"
TOKENSTORE = str(SCRIPTS_DIR / ".garmin_tokens")
START_DATE = "2026-03-07"

# Route map output
MAPS_DIR = SCRIPTS_DIR.parent.parent / "static" / "runs" / "maps"
MAP_URL_PREFIX = "/runs/maps"
MAP_EMBED_WIDTH = 640

# Route map tuning
SVG_WIDTH, SVG_PAD, LEGEND_H = 640, 14, 46
MAP_MIN_H, MAP_MAX_H = 200, 560
MAX_MAP_POINTS = 600          # after decimation
MIN_STEP_PX = 0.6             # drop points closer than this (stopped at a light)
STROKE_WIDTH = 3.2
SPEED_SMOOTH_WINDOW = 5       # samples, odd, centred
AUTO_RANGE_PCT = 10.0         # percentile clip on speed
MOVING_MIN_MS = 1.0           # below this the watch is stopped, not running
MIN_BBOX_M = 20.0             # smaller than this is not a real route
DETAILS_DELAY_S = 0.75

# Privacy: cut a piece off each end of the route, so the real start and finish
# never reach the file. The radius is random per activity.
PRIVACY_TRIM_MIN_M = 400.0
PRIVACY_TRIM_MAX_M = 800.0
PRIVACY_MAX_ROUTE_SHARE = 0.075  # cap the radius at this share of the route length
# A trim must leave at least this much of a run. Keep it well below half: a
# route that passes its own start in the middle gets split there, so the longest
# contiguous stretch left is under half whatever radius we choose.
PRIVACY_KEEP_FRACTION = 0.35
MAX_SVG_WARN_BYTES = 160_000  # basemap detail budget, and the "too big" warning

# Blue speed ramp, from moresamwilson/running-heatmap (cmap_speed_rgb):
# dark navy for the slow parts, near-white blue for the fast parts.
SPEED_RAMP: tuple[tuple[float, tuple[float, float, float]], ...] = (
    (0.00, (0.00, 0.10, 0.40)),
    (0.35, (0.05, 0.30, 0.80)),
    (0.65, (0.20, 0.55, 1.00)),
    (0.85, (0.55, 0.75, 1.00)),
    (1.00, (0.85, 0.92, 1.00)),
)
RAMP_BUCKETS = 16
# The full ramp fails at one end on each theme: near-white blue disappears on the
# light #fff background, and navy disappears on the dark #01242e one. So sample
# the same ramp over a different sub-range per theme.
LIGHT_SPAN = (0.00, 0.72)
DARK_SPAN = (0.42, 1.00)

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
OVERPASS_CACHE_DIR = SCRIPTS_DIR / ".overpass_cache"
OVERPASS_TIMEOUT_S = 90       # server-side budget, sent in the query
OVERPASS_READ_TIMEOUT_S = 180
OVERPASS_DELAY_S = 2.5        # pause after each query that hit the network
OVERPASS_ATTEMPTS = 2         # per endpoint
OVERPASS_BACKOFF_MAX_S = 60.0  # extra pause added after a refusal, per query
_overpass_penalty = 0.0        # grows on refusal, decays on success
BASEMAP_MIN_STEP_PX = 1.2     # thin dense node runs
MIN_GREEN_AREA_PX = 40.0      # drop tiny pitches and playgrounds

# Detail levels, tried in order until the file fits MAX_SVG_WARN_BYTES:
# (draw tertiary roads, thinning step px, min green area px2, min way extent px).
# Thinning drops vertices that sit close together and leaves the rest where they
# are. Do NOT snap coordinates to a coarse grid instead: snapping moves every
# vertex off its true position, and straight roads come out visibly wobbly for
# no real saving.
BASEMAP_DETAIL_LEVELS = (
    (True, BASEMAP_MIN_STEP_PX, MIN_GREEN_AREA_PX, 2.0),
    (False, BASEMAP_MIN_STEP_PX, MIN_GREEN_AREA_PX, 2.0),
    (False, 2.5, 200.0, 3.0),
)

# Road classes we draw, and their stroke width: the major street network only.
# Residential, unclassified, living streets, pedestrian ways, footways,
# cycleways, tracks, service roads and driveways are all left out on purpose:
# in a city they are most of the ways, and they cost both clutter and bytes.
ROAD_WIDTHS: dict[str, float] = {
    "motorway": 2.6, "motorway_link": 1.8, "trunk": 2.6, "trunk_link": 1.8,
    "primary": 2.4, "primary_link": 1.6, "secondary": 2.0, "secondary_link": 1.4,
    "tertiary": 1.7, "tertiary_link": 1.2,
}
BIG_ROADS = {
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
}
GREEN_LEISURE = {"park", "garden", "pitch", "golf_course", "playground"}
GREEN_LANDUSE = {
    "grass", "forest", "recreation_ground", "cemetery", "meadow",
    "village_green", "allotments",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_ignore_set() -> set[int]:
    if not IGNORE_FILE.exists():
        return set()
    ids: set[int] = set()
    for line in IGNORE_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.add(int(line))
    return ids


def load_imported_set() -> set[int]:
    if not IMPORTED_FILE.exists():
        return set()
    data = json.loads(IMPORTED_FILE.read_text())
    return set(data.get("imported", []))


def save_imported_set(imported: set[int]) -> None:
    IMPORTED_FILE.write_text(
        json.dumps({"imported": sorted(imported)}, indent=2) + "\n"
    )


def format_duration(seconds: float) -> str:
    """Return MM:SS or H:MM:SS string."""
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_pace(seconds_per_km: float) -> str:
    """Return M:SS string for pace."""
    total = int(round(seconds_per_km))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


def format_pace_from_speed(mps: float) -> str:
    """Return M:SS pace per km for a speed in m/s ('--:--' if implausible)."""
    if not mps or mps < 0.4:
        return "--:--"
    return format_pace(1000.0 / mps)


ZONE_NAMES = {1: "Warm Up", 2: "Easy", 3: "Aerobic", 4: "Threshold", 5: "Maximum"}


def hr_zones_mermaid(activity: dict) -> str:
    """Return a mermaid xychart shortcode for time in HR zones, or empty string."""
    # Collect all hrTimeInZone_N keys (e.g. hrTimeInZone_1 … hrTimeInZone_5)
    zone_data: list[tuple[int, int]] = []
    for key, value in activity.items():
        if key.startswith("hrTimeInZone_"):
            suffix = key[len("hrTimeInZone_"):]
            if suffix.isdigit():
                zone_data.append((int(suffix), int(value or 0)))

    if not zone_data:
        return ""

    # Display zone 5 → 1 (top to bottom, matching Garmin UI)
    zone_data.sort(key=lambda x: -x[0])

    total = sum(s for _, s in zone_data) or 1
    n = len(zone_data)
    labels = ", ".join(f'"Zone {z} {ZONE_NAMES.get(z, "")}"' for z, _ in zone_data)

    # One bar series per zone so each picks up its own palette color from the
    # plotColorPalette defined in mermaid.html (gray, orange, green, blue, lightgray).
    bar_lines = []
    for i, (_, secs) in enumerate(zone_data):
        values = ["0.0"] * n
        values[i] = f"{secs / total * 100:.1f}"
        bar_lines.append(f"    bar [{', '.join(values)}]")

    lines = [
        "{% mermaid() %}",
        """---
config:
  themeVariables:
    xyChart:
      plotColorPalette: "#555555,#FF8200,#56CC3C,#4090D4,#AAAAAA"
      backgroundColor: "transparent"
---
        """,
        "xychart horizontal",
        '    title "Time in Heart Rate Zones (%)"',
        f"    x-axis [{labels}]",
        # Start at 2 because of a weird mermaid rendering issue that shows
        # a bar even for zero values.
        '    y-axis "%" 2 --> 100',
        *bar_lines,
        "{% end %}",
    ]
    return "\n".join(lines)


def activity_to_markdown(activity: dict, map_url: str | None = None) -> str:
    distance_m: float = activity.get("distance", 0) or 0
    distance_km = round(distance_m / 1000, 2)

    duration_s: float = activity.get("duration", 0) or 0
    duration_str = format_duration(duration_s)

    pace_str = "N/A"
    if distance_km > 0 and duration_s > 0:
        pace_s = duration_s / distance_km
        pace_str = format_pace(pace_s)

    elevation_gain = activity.get("elevationGain") or activity.get("gainElevation")
    elevation_str = str(int(elevation_gain)) if elevation_gain else "N/A"

    activity_id = activity["activityId"]

    # Parse start time to get date
    start_local = activity.get("startTimeLocal") or activity.get("startTimeGMT", "")
    date_str = start_local[:10] if start_local else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    run_date = datetime.strptime(date_str, "%Y-%m-%d")
    activity_name = activity["activityName"]

    # Alternative title. Example: "8 March, 2026: Toronto - Easy Run"
    #title = f"{run_date.day} {run_date.strftime('%B')}, {run_date.year}: {activity_name}"
    title = f"{activity_name}"

    description = activity.get("description", "")
    mermaid_chart = hr_zones_mermaid(activity)
    chart_section = f"\n## Heart Rate Zones\n\n{mermaid_chart}\n" if mermaid_chart else ""
    mermaid_flag = "\n  mermaid: true" if mermaid_chart else ""
    route_section = f"\n## Route\n\n{route_shortcode(map_url)}\n" if map_url else ""

    frontmatter = f"""---
title: "{title}"
date: {date_str}
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: {activity_id}
  distance_km: {distance_km}
  duration: "{duration_str}"
  pace_per_km: "{pace_str}"
  elevation_gain_m: {elevation_str}
  mermaid: {mermaid_flag}
---"""

    table = f"""
| Stat | Value |
|------|-------|
| Distance | {distance_km} km |
| Duration | {duration_str} |
| Pace | {pace_str} /km |
| Elevation Gain | {elevation_str} m |
"""

    return frontmatter + "\n" + description + "\n" + table + route_section + chart_section


def output_path(date_str: str) -> Path:
    """Return a unique path for the given date, appending -2, -3, etc. if needed."""
    CONTENT_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    base = CONTENT_RUNS_DIR / f"{date_str}-run-{date_str}.md"
    if not base.exists():
        return base
    n = 2
    while True:
        candidate = CONTENT_RUNS_DIR / f"{date_str}-run-{date_str}-{n}.md"
        if not candidate.exists():
            return candidate
        n += 1


# ---------------------------------------------------------------------------
# Existing posts (backfill support)
# ---------------------------------------------------------------------------

ACTIVITY_ID_RE = re.compile(r"^\s*garmin_activity_id:\s*(\d+)\s*$", re.MULTILINE)


def index_posts_by_activity_id() -> dict[int, Path]:
    """Map each post's garmin_activity_id to its path."""
    index: dict[int, Path] = {}
    for path in sorted(CONTENT_RUNS_DIR.glob("*.md")):
        match = ACTIVITY_ID_RE.search(path.read_text())
        if match:
            index[int(match.group(1))] = path
    return index


def insert_route_shortcode(path: Path, shortcode: str) -> bool:
    """Insert a '## Route' block into an existing post. Insert only, idempotent.

    Returns True when the file changed. Posts carry hand-written prose and
    photos, so this never rewrites a line - it only inserts a block, before the
    '## Heart Rate Zones' heading when there is one, or at the end.
    """
    text = path.read_text()
    if MAP_URL_PREFIX in text:
        return False

    block = f"## Route\n\n{shortcode}\n\n"
    anchor = "## Heart Rate Zones"
    at = text.find(anchor)
    if at == -1:
        path.write_text(text.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n")
    else:
        path.write_text(text[:at] + block + text[at:])
    return True


def route_shortcode(map_url: str) -> str:
    """Return the image() shortcode line for a map URL."""
    return f'{{{{ image(path="{map_url}", width={MAP_EMBED_WIDTH}) }}}}'


# ---------------------------------------------------------------------------
# Route map (SVG)
# ---------------------------------------------------------------------------

# lat, lon, speed in m/s (None where the watch reported nothing)
Point = tuple[float, float, float | None]

EARTH_R = 6_371_000.0


def _metric_index(details: dict) -> dict[str, int]:
    """Map metric key -> index into each activityDetailMetrics row."""
    index: dict[str, int] = {}
    for descriptor in details.get("metricDescriptors") or []:
        key = descriptor.get("key")
        position = descriptor.get("metricsIndex")
        if isinstance(key, str) and isinstance(position, int):
            index[key] = position
    return index


def _unit_key(details: dict, metric_key: str) -> str:
    """Return the unit key Garmin reports for a metric (e.g. 'kilometer')."""
    for descriptor in details.get("metricDescriptors") or []:
        if descriptor.get("key") == metric_key:
            return str((descriptor.get("unit") or {}).get("key") or "")
    return ""


def _at(row: list, index: int | None) -> float | None:
    """Read row[index] as a float, or None when it is absent or not a number."""
    if index is None or index >= len(row):
        return None
    value = row[index]
    # bool is an int subclass, and no metric is ever a bool.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _speed_from_distance_time(
    dist_m: list[float | None], ts_ms: list[float | None]
) -> list[float | None]:
    """Derive speed from cumulative distance and timestamps.

    Uses a central difference over a +/-2 sample window, so it never divides by
    a near-zero time delta.
    """
    n = len(dist_m)
    out: list[float | None] = []
    for i in range(n):
        a, b = max(0, i - 2), min(n - 1, i + 2)
        d0, d1, t0, t1 = dist_m[a], dist_m[b], ts_ms[a], ts_ms[b]
        if d0 is None or d1 is None or t0 is None or t1 is None:
            out.append(None)
            continue
        delta_d = d1 - d0
        delta_t = (t1 - t0) / 1000.0
        out.append(delta_d / delta_t if delta_t > 0.5 and delta_d >= 0 else None)
    return out


def _points_from_metrics(details: dict) -> list[Point]:
    """Read lat/lon/speed from the activityDetailMetrics rows."""
    index = _metric_index(details)
    lat_i, lon_i = index.get("directLatitude"), index.get("directLongitude")
    if lat_i is None or lon_i is None:
        return []

    speed_i = index.get("directSpeed")
    dist_i = index.get("sumDistance")
    time_i = index.get("directTimestamp")
    dist_scale = 1000.0 if _unit_key(details, "sumDistance") == "kilometer" else 1.0

    lats: list[float] = []
    lons: list[float] = []
    speeds: list[float | None] = []
    dists: list[float | None] = []
    times: list[float | None] = []

    for row in details.get("activityDetailMetrics") or []:
        metrics = row.get("metrics") or []
        lat, lon = _at(metrics, lat_i), _at(metrics, lon_i)
        # Test for None, not truthiness: latitude 0.0 is a real coordinate.
        if lat is None or lon is None:
            continue
        # Garmin emits (0, 0) for a sample with no fix.
        if abs(lat) < 1e-7 and abs(lon) < 1e-7:
            continue
        lats.append(lat)
        lons.append(lon)
        speeds.append(_at(metrics, speed_i))
        distance = _at(metrics, dist_i)
        dists.append(distance * dist_scale if distance is not None else None)
        times.append(_at(metrics, time_i))

    if all(speed is None for speed in speeds):
        speeds = _speed_from_distance_time(dists, times)

    return list(zip(lats, lons, speeds))


def _points_from_polyline(details: dict) -> list[Point]:
    """Fall back to geoPolylineDTO, which is denser and always has coordinates."""
    polyline = (details.get("geoPolylineDTO") or {}).get("polyline") or []

    lats: list[float] = []
    lons: list[float] = []
    speeds: list[float | None] = []
    dists: list[float | None] = []
    times: list[float | None] = []

    for point in polyline:
        lat, lon = point.get("lat"), point.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        if abs(lat) < 1e-7 and abs(lon) < 1e-7:
            continue
        lats.append(float(lat))
        lons.append(float(lon))
        speed = point.get("speed")
        speeds.append(float(speed) if isinstance(speed, (int, float)) else None)
        distance = point.get("distance")
        dists.append(float(distance) if isinstance(distance, (int, float)) else None)
        moment = point.get("time")
        times.append(float(moment) if isinstance(moment, (int, float)) else None)

    if all(speed is None for speed in speeds):
        speeds = _speed_from_distance_time(dists, times)

    return list(zip(lats, lons, speeds))


def extract_points(details: dict) -> list[Point]:
    """Return [(lat, lon, speed_ms | None), ...] from get_activity_details.

    Returns [] for an activity with no GPS track (a treadmill run).
    """
    points = _points_from_metrics(details)
    if len(points) < 2:
        points = _points_from_polyline(details)
    return points


def distance_m(a: Point, b: Point) -> float:
    """Great-circle distance between two samples, in metres."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_R * math.asin(math.sqrt(h))


def trim_route_ends(
    points: list[Point], activity_id: int, enabled: bool = True
) -> tuple[list[Point], float]:
    """Drop a piece from each end of the route, measured along the path.

    Randomising the two end coordinates alone would protect nothing: the next
    sample along the track still sits at the real place. So cut a whole piece
    off each end, and let the drawn route start somewhere along the way.

    The distance is random per activity. It is seeded from the activity id, so a
    regeneration gives the same file, and it differs between runs, so the cut
    ends of several posts cannot be intersected to find the centre.

    Measuring along the path, rather than as a radius around the start, matters
    for lap runs. On a running track every sample sits within 100 m of the
    start, so a radius removes the whole activity, while a path cut removes the
    first and last few hundred metres and leaves the laps.

    Returns the kept samples and the distance cut (0.0 when nothing was cut).
    """
    if not enabled or len(points) < 3:
        return points, 0.0

    steps = [distance_m(a, b) for a, b in zip(points, points[1:])]
    length = sum(steps)
    cut = random.Random(activity_id).uniform(PRIVACY_TRIM_MIN_M, PRIVACY_TRIM_MAX_M)
    # Cap by route length, so a short run keeps enough to be worth drawing.
    cut = min(cut, length * PRIVACY_MAX_ROUTE_SHARE)
    if cut <= 0.0:
        return points, 0.0

    travelled = 0.0
    kept: list[Point] = []
    for point, step in zip(points, [0.0] + steps):
        travelled += step
        if cut < travelled < length - cut:
            kept.append(point)

    if len(kept) < max(2, int(len(points) * PRIVACY_KEEP_FRACTION)):
        return points, 0.0
    return kept, cut


def fill_none(values: list[float | None]) -> list[float]:
    """Forward-fill, then back-fill the leading gap. All-None becomes all-zero."""
    out: list[float] = []
    last = 0.0
    for value in values:
        if value is not None:
            last = value
        out.append(last)

    first = next((i for i, v in enumerate(values) if v is not None), None)
    if first is None:
        return [0.0] * len(values)
    for i in range(first):
        out[i] = out[first]
    return out


def rolling_mean(values: list[float], window: int) -> list[float]:
    """Centred rolling mean, with the window shrinking at both ends.

    Raw GPS speed is noisy enough to flip colour bucket every sample, which
    would defeat the segment merging in merge_runs().
    """
    if window <= 1 or len(values) < 2:
        return list(values)
    half = window // 2
    n = len(values)
    return [fmean(values[max(0, i - half):min(n, i + half + 1)]) for i in range(n)]


def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolated percentile. Pure Python, no numpy."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    k = (len(ordered) - 1) * pct / 100.0
    low, high = math.floor(k), math.ceil(k)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (k - low)


def speed_range(speeds: list[float], pct: float = AUTO_RANGE_PCT) -> tuple[float, float]:
    """Return the clipped (slow, fast) bounds used to normalise the colour.

    Standing samples are left out of the range. A workout with long recoveries
    would otherwise put its low bound at a walking pace, which pushes all the
    real running into the light end of the ramp and hides the whole point of
    the map. Stops still get drawn: they clamp to the dark end.
    """
    moving = [speed for speed in speeds if speed >= MOVING_MIN_MS]
    sample = moving if len(moving) >= 20 and len(moving) >= len(speeds) / 4 else speeds
    lo = percentile(sample, pct)
    hi = percentile(sample, 100.0 - pct)
    if hi - lo < 0.05:
        hi = lo + 0.05
    return lo, hi


def ramp_rgb(t: float) -> tuple[int, int, int]:
    """Interpolate SPEED_RAMP at t in 0..1."""
    t = min(1.0, max(0.0, t))
    for (p0, c0), (p1, c1) in zip(SPEED_RAMP, SPEED_RAMP[1:]):
        if t <= p1:
            span = p1 - p0
            f = (t - p0) / span if span else 0.0
            return tuple(round((a + (b - a) * f) * 255) for a, b in zip(c0, c1))
    return tuple(round(c * 255) for c in SPEED_RAMP[-1][1])


def ramp_hex(t: float) -> str:
    r, g, b = ramp_rgb(t)
    return f"#{r:02X}{g:02X}{b:02X}"


def ramp_at_speed(t: float, span: tuple[float, float]) -> str:
    """Colour for a normalised speed t, where 0 is slowest and 1 is fastest.

    The ramp is walked backwards on purpose: darker means faster.
    """
    lo, hi = span
    return ramp_hex(hi - (hi - lo) * t)


def _bucket_table(span: tuple[float, float]) -> list[str]:
    """Bucket colours, slowest first."""
    return [
        ramp_at_speed((i + 0.5) / RAMP_BUCKETS, span)
        for i in range(RAMP_BUCKETS)
    ]


def bucket_of(value: float, lo: float, hi: float) -> int:
    """Quantise a speed into 0 … RAMP_BUCKETS-1."""
    t = (value - lo) / (hi - lo)
    return min(RAMP_BUCKETS - 1, max(0, int(t * RAMP_BUCKETS)))


def project(points: list[Point]) -> list[tuple[float, float]]:
    """Equirectangular projection into metres, centred on the route."""
    lat0 = fmean(p[0] for p in points)
    lon0 = fmean(p[1] for p in points)
    k = math.cos(math.radians(lat0))
    return [
        (
            EARTH_R * math.radians(lon - lon0) * k,
            # Negate: SVG y grows downward, latitude grows north.
            -EARTH_R * math.radians(lat - lat0),
        )
        for lat, lon, _ in points
    ]


def fit_box(xy: list[tuple[float, float]]) -> tuple[float, int, float, float] | None:
    """Return (scale px/m, map height, x offset, y offset), or None if too small."""
    xs = [p[0] for p in xy]
    ys = [p[1] for p in xy]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    w_m, h_m = max_x - min_x, max_y - min_y
    if max(w_m, h_m) < MIN_BBOX_M:
        return None

    map_w = SVG_WIDTH - 2 * SVG_PAD
    aspect = h_m / w_m if w_m > 0 else 10.0
    map_h = int(min(MAP_MAX_H, max(MAP_MIN_H, round(map_w * aspect))))

    # min() keeps the aspect ratio; the height clamp above only letterboxes.
    scale = min(
        map_w / w_m if w_m > 0 else float("inf"),
        map_h / h_m if h_m > 0 else float("inf"),
    )
    off_x = SVG_PAD + (map_w - w_m * scale) / 2 - min_x * scale
    off_y = SVG_PAD + (map_h - h_m * scale) / 2 - min_y * scale
    return scale, map_h, off_x, off_y


def decimate(
    px: list[tuple[float, float]], speeds: list[float]
) -> tuple[list[tuple[float, float]], list[float]]:
    """Thin the track: stride to MAX_MAP_POINTS, then drop near-coincident points."""
    n = len(px)
    step = max(1, math.ceil(n / MAX_MAP_POINTS))
    keep = list(range(0, n, step))
    if keep[-1] != n - 1:
        keep.append(n - 1)

    out_px: list[tuple[float, float]] = []
    out_speeds: list[float] = []
    for j, i in enumerate(keep):
        if out_px:
            last_x, last_y = out_px[-1]
            x, y = px[i]
            close = max(abs(x - last_x), abs(y - last_y)) < MIN_STEP_PX
            # Always keep the final point so the finish marker lands on the end,
            # unless it is an exact duplicate of the point before it.
            if close and (j != len(keep) - 1 or (x, y) == (last_x, last_y)):
                continue
        out_px.append(px[i])
        out_speeds.append(speeds[i])
    return out_px, out_speeds


def merge_runs(
    px: list[tuple[float, float]], buckets: list[int]
) -> list[tuple[int, list[tuple[float, float]]]]:
    """Group consecutive same-bucket segments into one polyline each.

    Each new run restarts on the previous run's last vertex. Together with
    stroke-linecap="round" that shared vertex hides the seam: both strokes put a
    half-disc on it, so no background shows through at a colour change.
    """
    runs: list[tuple[int, list[tuple[float, float]]]] = []
    current_bucket = buckets[0]
    current = [px[0], px[1]]
    for i in range(1, len(buckets)):
        if buckets[i] == current_bucket:
            current.append(px[i + 1])
        else:
            runs.append((current_bucket, current))
            current_bucket = buckets[i]
            current = [px[i], px[i + 1]]
    runs.append((current_bucket, current))
    return runs


def _num(value: float) -> str:
    """Compact number for SVG output ('18.4', '201' rather than '201.0')."""
    return f"{value:g}"


def _gradient(gradient_id: str, span: tuple[float, float]) -> str:
    """A 5-stop legend gradient, sampled from the same ramp as the route.

    Left to right is slow to fast, so the bar runs light to dark.
    """
    stops = "".join(
        f'<stop offset="{_num(offset)}" stop-color="{ramp_at_speed(offset, span)}"/>'
        for offset in (0.0, 0.25, 0.5, 0.75, 1.0)
    )
    return f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient>'


class Track(NamedTuple):
    """A route ready to draw, plus the transform the basemap has to share."""

    px: list[tuple[float, float]]
    speeds: list[float]
    lo: float
    hi: float
    map_h: int
    lat0: float
    lon0: float
    scale: float
    off_x: float
    off_y: float

    @property
    def panel_h(self) -> int:
        return SVG_PAD + self.map_h + SVG_PAD

    def to_px(self, lat: float, lon: float) -> tuple[float, float]:
        k = math.cos(math.radians(self.lat0))
        return (
            EARTH_R * math.radians(lon - self.lon0) * k * self.scale + self.off_x,
            -EARTH_R * math.radians(lat - self.lat0) * self.scale + self.off_y,
        )

    def to_latlon(self, x: float, y: float) -> tuple[float, float]:
        k = math.cos(math.radians(self.lat0))
        return (
            self.lat0 + math.degrees(-(y - self.off_y) / self.scale / EARTH_R),
            self.lon0 + math.degrees((x - self.off_x) / self.scale / EARTH_R / k),
        )

    def bounds(self) -> tuple[float, float, float, float]:
        """Visible (south, west, north, east) of the whole panel."""
        north, west = self.to_latlon(0, 0)
        south, east = self.to_latlon(SVG_WIDTH, self.panel_h)
        return south, west, north, east


def prepare_track(points: list[Point]) -> Track | None:
    """Project, thin and normalise a track. None when there is nothing to draw."""
    if len(points) < 2:
        return None

    raw = fill_none([p[2] for p in points])
    lo, hi = speed_range(raw)
    # Clamp before smoothing. The other order lets one GPS spike leak into its
    # neighbours through the window and stretch the whole colour range.
    clamped = [min(hi, max(lo, speed)) for speed in raw]
    speeds = rolling_mean(clamped, SPEED_SMOOTH_WINDOW)

    xy = project(points)
    box = fit_box(xy)
    if box is None:
        return None
    scale, map_h, off_x, off_y = box

    # One decimal is sub-pixel at this width, and it roughly halves the bytes.
    px = [(round(x * scale + off_x, 1), round(y * scale + off_y, 1)) for x, y in xy]
    px, speeds = decimate(px, speeds)
    if len(px) < 2:
        return None

    return Track(
        px=px, speeds=speeds, lo=lo, hi=hi, map_h=map_h,
        lat0=fmean(p[0] for p in points), lon0=fmean(p[1] for p in points),
        scale=scale, off_x=off_x, off_y=off_y,
    )


# ---------------------------------------------------------------------------
# OpenStreetMap basemap
# ---------------------------------------------------------------------------

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
    return OVERPASS_CACHE_DIR / f"{digest}.json.gz"


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
    OVERPASS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with gzip.open(path, "wb") as handle:
            handle.write(raw)
    except Exception as exc:  # noqa: BLE001
        print(f"  could not cache the response: {exc}")


def wait_for_overpass_slot() -> None:
    """Wait until the main endpoint reports a free query slot.

    The status endpoint gives the slot count and the exact reset time, so we can
    wait the right amount instead of guessing. It is advisory: any problem
    reading it means we just go ahead and query.
    """
    try:
        with urllib.request.urlopen(OVERPASS_STATUS_URL, timeout=20) as response:
            text = response.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return

    free = re.search(r"(\d+) slots? available now", text)
    if free and int(free.group(1)) > 0:
        return
    waits = [int(seconds) for seconds in re.findall(r"in (\d+) seconds", text)]
    if waits:
        wait = min(min(waits) + 1.0, OVERPASS_STATUS_MAX_WAIT_S)
        print(f"  Overpass reports no free slot; waiting {wait:.0f} s")
        time.sleep(wait)


def _overpass_request(url: str, query: str) -> bytes | None:
    """One endpoint, with retries and a growing penalty. None when it fails."""
    global _overpass_penalty

    for attempt in range(1, OVERPASS_ATTEMPTS + 1):
        try:
            request = urllib.request.Request(
                url,
                data=urllib.parse.urlencode({"data": query}).encode(),
                headers={"User-Agent": "jonalmeida.github.com route maps (personal blog)"},
            )
            with urllib.request.urlopen(request, timeout=OVERPASS_READ_TIMEOUT_S) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001 - the map is worth more than the background
            # A 429, or a refused connection, means we are querying too fast.
            # Slow every later query down as well, or one rate limit strips the
            # basemap from every remaining map in the run.
            _overpass_penalty = min(OVERPASS_BACKOFF_MAX_S, _overpass_penalty * 2 + 5.0)
            host = urllib.parse.urlparse(url).netloc
            if attempt < OVERPASS_ATTEMPTS:
                wait = 15.0 * attempt + _overpass_penalty
                print(f"  {host} failed ({exc}); waiting {wait:.0f} s and retrying")
                time.sleep(wait)
            else:
                print(f"  {host} failed ({exc})")
    return None


def fetch_basemap(track: Track, use_cache: bool = True) -> dict | None:
    """Fetch OSM ways for the visible area. None when every endpoint fails.

    A missing basemap only costs us the background, so failure here is a warning
    and the map still gets drawn.
    """
    global _overpass_penalty

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
        _overpass_penalty = max(0.0, _overpass_penalty / 2 - 1.0)
        time.sleep(OVERPASS_DELAY_S + _overpass_penalty)
        return data

    print("  WARNING: no basemap from any endpoint; drawing the route alone")
    return None


def _edge_crossing(
    outside: tuple[float, float], inside: tuple[float, float], width: float, height: float
) -> tuple[int, int] | None:
    """Where the segment enters the panel rectangle (Liang-Barsky clip)."""
    x0, y0 = outside
    dx, dy = inside[0] - x0, inside[1] - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0), (dx, width - x0), (-dy, y0), (dy, height - y0)):
        if p == 0:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            if r > t1:
                return None
            t0 = max(t0, r)
        else:
            if r < t0:
                return None
            t1 = min(t1, r)
    return (round(x0 + t0 * dx), round(y0 + t0 * dy))


def _basemap_path(
    track: Track, geometry: list[dict], min_step: float
) -> list[list[tuple[int, int]]]:
    """Project a way to whole pixels. Return only the parts inside the panel.

    Whole pixels keep the file small without the wobble a coarser grid causes.
    Cutting at the panel edge matters for privacy as well as size: a clipPath
    hides off-panel geometry on screen, but leaves every coordinate in the file
    for anyone who opens it. Each crossing gets an exact boundary point, so a
    road still reaches the edge of the panel.
    """
    out: list[tuple[int, int]] = []
    for node in geometry:
        lat, lon = node.get("lat"), node.get("lon")
        if lat is None or lon is None:
            continue
        x, y = track.to_px(lat, lon)
        candidate = (round(x), round(y))
        if out:
            last_x, last_y = out[-1]
            if candidate == out[-1]:
                continue
            if min_step and max(abs(candidate[0] - last_x), abs(candidate[1] - last_y)) < min_step:
                continue
        out.append(candidate)

    # Put back the closing node of a ring, if thinning dropped it.
    if len(out) > 2 and geometry[0].get("lat") == geometry[-1].get("lat") and out[0] != out[-1]:
        out.append(out[0])
    if len(out) < 2:
        return []

    width, height = float(SVG_WIDTH), float(track.panel_h)

    def inside(point: tuple[int, int]) -> bool:
        return 0 <= point[0] <= width and 0 <= point[1] <= height

    # Keep each run of vertices inside the panel, plus its boundary crossings.
    # A segment with both ends outside that clips a corner is dropped; for road
    # and park data that sliver is not worth the code.
    runs: list[list[tuple[int, int]]] = []
    current: list[tuple[int, int]] = []
    previous: tuple[int, int] | None = None
    for point in out:
        if inside(point):
            if previous is not None and not inside(previous):
                entry = _edge_crossing(previous, point, width, height)
                if entry and entry != point:
                    current.append(entry)
            current.append(point)
        elif previous is not None and inside(previous):
            exit_point = _edge_crossing(point, previous, width, height)
            if exit_point and exit_point != previous:
                current.append(exit_point)
            if len(current) >= 2:
                runs.append(current)
            current = []
        previous = point
    if len(current) >= 2:
        runs.append(current)
    return runs


def basemap_layers(
    track: Track,
    data: dict,
    tertiary_roads: bool = True,
    min_step: float = BASEMAP_MIN_STEP_PX,
    min_green: float = MIN_GREEN_AREA_PX,
    min_extent: float = 2.0,
) -> str:
    """Return the SVG for the green, water and road layers, in draw order.

    Only major streets are drawn. With tertiary_roads off, that narrows further
    to the arterials: a long run covers a much wider area, where even the
    tertiary network is both too much detail and too many bytes.
    """
    greens: list[list[dict]] = []
    waters: list[list[dict]] = []
    water_lines: list[list[dict]] = []
    roads: list[tuple[str, list[dict]]] = []

    for element in data.get("elements") or []:
        tags = element.get("tags") or {}
        if element.get("type") == "relation":
            # Approximate a multipolygon by its member rings; good enough here.
            for member in element.get("members") or []:
                if member.get("geometry"):
                    waters.append(member["geometry"])
            continue
        geometry = element.get("geometry")
        if not geometry:
            continue
        if tags.get("natural") in ("water", "coastline"):
            waters.append(geometry)
        elif tags.get("waterway"):
            water_lines.append(geometry)
        elif tags.get("leisure") in GREEN_LEISURE or tags.get("landuse") in GREEN_LANDUSE:
            greens.append(geometry)
        elif tags.get("highway") in ROAD_WIDTHS:
            roads.append((tags["highway"], geometry))

    def shapes(geometries, css_class: str, close: bool, min_area: float = 0.0) -> str:
        out = []
        for geometry in geometries:
            for pts in _basemap_path(track, geometry, min_step):
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                width, height = max(xs) - min(xs), max(ys) - min(ys)
                if min_area and width * height < min_area:
                    continue
                # Overpass splits ways at every junction, so a dense area yields
                # thousands of fragments too short to see.
                if max(width, height) < min_extent:
                    continue
                points = " ".join(f"{x},{y}" for x, y in pts)
                out.append(
                    f'<{"polygon" if close else "polyline"} class="{css_class}" points="{points}"/>'
                )
        return "\n".join(out)

    layers = [
        shapes(greens, "gr", True, min_green),
        shapes(waters, "wa", True),
        shapes(water_lines, "wl", False),
    ]
    # Widest roads first, so the small ones draw on top of the big ones.
    for name, width in sorted(ROAD_WIDTHS.items(), key=lambda kv: -kv[1]):
        if not tertiary_roads and name not in BIG_ROADS:
            continue
        group = [g for cls, g in roads if cls == name]
        body = shapes(group, "rd" if name in BIG_ROADS else "rn", False) if group else ""
        if body:
            layers.append(f'<g stroke-width="{width}">\n{body}\n</g>')

    return "\n".join(layer for layer in layers if layer)


def route_map_svg(
    points: list[Point], label: str = "", basemap: dict | None = None
) -> str | None:
    """Return a standalone SVG of the route, coloured by speed.

    Returns None (and never raises) when there is nothing worth drawing. Takes
    already-fetched basemap data, so it stays free of network calls.
    """
    track = prepare_track(points)
    if track is None:
        return None
    return render_route_svg(track, label=label, basemap=basemap)


def render_route_svg(track: Track, label: str = "", basemap: dict | None = None) -> str:
    """Draw a prepared track, optionally over an OSM basemap."""
    px, speeds, lo, hi = track.px, track.speeds, track.lo, track.hi
    buckets = [
        bucket_of(fmean((speeds[i], speeds[i + 1])), lo, hi)
        for i in range(len(px) - 1)
    ]
    runs = merge_runs(px, buckets)

    panel_h = track.panel_h
    legend_y = panel_h + 8
    total_h = panel_h + LEGEND_H + 12
    slow_label = format_pace_from_speed(lo)
    fast_label = format_pace_from_speed(hi)
    title = f"Route map{f' — {label}' if label else ''}"
    where = " on a street map" if basemap else ""
    aria = (
        f"Route map{where}{f', {label}' if label else ''}, "
        f"pace {slow_label} to {fast_label} per km"
    )

    # Firefox and Safari honour prefers-color-scheme for an SVG in an <img>;
    # older Chromium does not (crbug.com/1252199). The light palette rides on
    # the stroke attribute, so it is the graceful fallback and it matches the
    # site default. currentColor does not resolve in an <img>, hence .lg/.mk/.mkf.
    dark_rules = "".join(
        f".s{i}{{stroke:{RAMP_DARK_HEX[i]}}}" for i in range(RAMP_BUCKETS)
    )
    style = (
        f".rt{{fill:none;stroke-width:{STROKE_WIDTH};stroke-linecap:round;stroke-linejoin:round}}\n"
        ".lg{font:11px system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;fill:#555}\n"
        ".at{font:9px system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;fill:#8a8578}\n"
        ".mk{fill:none;stroke:#333;stroke-width:2}\n"
        ".mkf{fill:#333}\n"
        ".bar{fill:url(#rampL);stroke:#8884;stroke-width:.5}\n"
        ".bg{fill:#f4f1ea}\n"
        ".gr{fill:#e3ebdb;stroke:none}\n"
        ".wa{fill:#cfe0ea;stroke:none}\n"
        ".wl{fill:none;stroke:#cfe0ea;stroke-width:1.4}\n"
        ".rn{fill:none;stroke:#e2ddd2;stroke-linecap:round}\n"
        ".rd{fill:none;stroke:#d5cec0;stroke-linecap:round}\n"
        "@media (prefers-color-scheme:dark){\n"
        ".lg{fill:#c9d6da}.at{fill:#5c7580}.mk{stroke:#eee}.mkf{fill:#eee}.bar{fill:url(#rampD)}\n"
        ".bg{fill:#04202a}.gr{fill:#0a2c2c}.wa{fill:#062c3a}.wl{stroke:#062c3a}\n"
        ".rn{stroke:#0e3340}.rd{stroke:#14404e}\n"
        f"{dark_rules}\n"
        "}"
    )

    # The <g> carries fill, stroke-width and the caps once; all are inherited,
    # so each polyline costs only class, stroke and points.
    polylines = "\n".join(
        '<polyline class="s{b}" stroke="{hex}" points="{pts}"/>'.format(
            b=bucket,
            hex=RAMP_LIGHT_HEX[bucket],
            pts=" ".join(f"{_num(x)},{_num(y)}" for x, y in run),
        )
        for bucket, run in runs
    )

    panel = (
        f'<rect class="bg" x="0" y="0" width="{SVG_WIDTH}" height="{panel_h}" rx="6"/>\n'
        if basemap else ""
    )
    # ODbL requires the credit whenever OSM data is shown.
    attribution = (
        f'<text class="at" x="{SVG_WIDTH - 2 * SVG_PAD}" y="14" text-anchor="end">'
        "Map data &#169; OpenStreetMap contributors</text>\n"
        if basemap else ""
    )
    start_x, start_y = px[0]
    end_x, end_y = px[-1]

    def compose(layers: str) -> str:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_WIDTH} {total_h}" width="{SVG_WIDTH}" height="{total_h}" role="img" aria-label="{aria}">
<title>{title}</title>
<style>
{style}
</style>
<defs>
{_gradient("rampL", LIGHT_SPAN)}
{_gradient("rampD", DARK_SPAN)}
<clipPath id="panel"><rect x="0" y="0" width="{SVG_WIDTH}" height="{panel_h}" rx="6"/></clipPath>
</defs>
{panel}<g clip-path="url(#panel)">
{layers}<g class="rt">
{polylines}
</g>
<circle class="mk" cx="{_num(start_x)}" cy="{_num(start_y)}" r="5"/>
<circle class="mkf" cx="{_num(end_x)}" cy="{_num(end_y)}" r="2.2"/>
</g>
<g transform="translate({SVG_PAD},{legend_y})">
<rect class="bar" x="0" y="6" width="150" height="8" rx="4"/>
<text class="lg" x="0" y="30">{slow_label}/km</text>
<text class="lg" x="150" y="30" text-anchor="end">{fast_label}/km</text>
<text class="lg" x="166" y="14" dominant-baseline="middle">slower &#8594; faster</text>
{attribution}</g>
</svg>
"""

    if not basemap:
        return compose("")

    # Drop detail until the file fits the budget. Wide-area maps lose their
    # tertiary roads first, which is what a map at that scale should do anyway.
    svg = ""
    for level, (tertiary, step, green, extent) in enumerate(BASEMAP_DETAIL_LEVELS):
        svg = compose(
            basemap_layers(track, basemap, tertiary, step, green, extent) + "\n"
        )
        size = len(svg.encode())
        if size <= MAX_SVG_WARN_BYTES:
            if level:
                print(f"  basemap thinned to detail level {level} ({size / 1024:.0f} KB)")
            return svg
    print(f"  basemap still {len(svg.encode()) / 1024:.0f} KB at the lowest detail level")
    return svg


def write_route_map(
    activity_id: int,
    points: list[Point],
    label: str = "",
    basemap: bool = True,
    privacy_trim: bool = True,
    refresh_basemap: bool = False,
) -> str | None:
    """Write static/runs/maps/<id>.svg. Return its site path, or None."""
    path = MAPS_DIR / f"{activity_id}.svg"

    def give_up(reason: str) -> None:
        """Report, and remove any earlier map for this activity.

        Leaving the previous file in place would be the worst outcome: it was
        drawn before the privacy trim existed, so it still shows the real start
        and finish.
        """
        print(f"  no map for {activity_id}: {reason}")
        if path.exists():
            path.unlink()
            print(f"  removed the earlier {path.name}, which was not trimmed")

    trimmed, radius = trim_route_ends(points, activity_id, privacy_trim)
    if len(trimmed) < 2:
        give_up("the privacy trim leaves too little of the route")
        return None
    if radius:
        print(
            f"  privacy trim: {radius:.0f} m off each end, "
            f"keeping {len(trimmed)} of {len(points)} samples"
        )
    points = trimmed

    track = prepare_track(points)
    if track is None:
        give_up("the route is too small to draw")
        return None
    data = fetch_basemap(track, use_cache=not refresh_basemap) if basemap else None
    svg = render_route_svg(track, label=label, basemap=data)

    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(svg)
    size = len(svg.encode())
    # Count only the route's polylines; the basemap has its own.
    segments = svg.count('<polyline class="s')
    print(f"  Wrote map {path.name} ({size / 1024:.1f} KB, {segments} segments)")
    if size > MAX_SVG_WARN_BYTES:
        print(
            f"  WARNING: {path.name} is large even at the lowest basemap detail; "
            "consider --no-basemap for this one"
        )
    return f"{MAP_URL_PREFIX}/{activity_id}.svg"


RAMP_LIGHT_HEX: list[str] = _bucket_table(LIGHT_SPAN)
RAMP_DARK_HEX: list[str] = _bucket_table(DARK_SPAN)


# ---------------------------------------------------------------------------
# Garmin fetch
# ---------------------------------------------------------------------------

def fetch_running_activities(client: Garmin) -> list[dict]:
    """Fetch all running activities on or after START_DATE, oldest first."""
    all_activities: list[dict] = []
    limit = 100
    start = 0
    while True:
        batch = client.get_activities_by_date(
            START_DATE,
            None,
            "running",
        )
        # get_activities_by_date returns all at once (no pagination needed for
        # most users); fall back to paginated get_activities if needed.
        all_activities = batch
        break

    # Sort oldest first
    all_activities.sort(key=lambda a: a.get("startTimeLocal") or a.get("startTimeGMT") or "")
    return all_activities


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
                time.sleep(5)
            else:
                print(f"  WARNING: details fetch failed for {activity_id}: {exc}")
                return []

    try:
        return extract_points(details or {})
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: could not parse GPS metrics for {activity_id}: {exc}")
        return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Garmin running activities to Zola markdown files."
    )
    parser.add_argument(
        "--no-maps", action="store_true",
        help="skip route map generation (no extra API calls)",
    )
    parser.add_argument(
        "--backfill-maps", action="store_true",
        help="generate route maps for already-imported activities and insert a "
             "'## Route' block into their posts; imports nothing new",
    )
    parser.add_argument(
        "--no-basemap", action="store_true",
        help="draw the route without the OpenStreetMap background "
             "(no Overpass queries, and a much smaller file)",
    )
    parser.add_argument(
        "--refresh-basemap", action="store_true",
        help="ignore the cached Overpass responses and query again "
             "(use when the OpenStreetMap data has changed)",
    )
    parser.add_argument(
        "--no-privacy-trim", action="store_true",
        help=f"draw the whole track, including the real start and finish "
             f"(default: cut a random {PRIVACY_TRIM_MIN_M:.0f}-{PRIVACY_TRIM_MAX_M:.0f} m "
             f"off each end)",
    )
    parser.add_argument(
        "--activity", type=int, action="append", metavar="ID",
        help="with --backfill-maps, limit to these activity IDs (repeatable)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="with --backfill-maps, overwrite an SVG that exists already",
    )
    parser.add_argument(
        "--delay", type=float, default=DETAILS_DELAY_S, metavar="SECONDS",
        help="pause between activity-details API calls (default: %(default)s)",
    )
    parser.add_argument(
        "--selftest", nargs="?", const="/tmp/route_selftest.svg", metavar="PATH",
        help="render a synthetic route and exit (no Garmin credentials needed)",
    )
    return parser.parse_args()


def authenticate(email: str, password: str) -> Garmin:
    client = Garmin(email, password)
    tokenstore_path = Path(TOKENSTORE)
    if (tokenstore_path / "garmin_tokens.json").exists():
        client.client.load(TOKENSTORE)
    else:
        client.client.login(email, password, prompt_mfa=lambda: input("Enter MFA code: "))
        tokenstore_path.mkdir(parents=True, exist_ok=True)
        client.client.dump(TOKENSTORE)
    print("Authenticated with Garmin Connect.")
    return client


def run_import(client: Garmin, args: argparse.Namespace) -> None:
    ignore_set = load_ignore_set()
    imported_set = load_imported_set()
    print(f"Loaded {len(ignore_set)} ignored IDs, {len(imported_set)} already-imported IDs.")

    activities = fetch_running_activities(client)
    print(f"Fetched {len(activities)} running activities since {START_DATE}.")

    count_imported = 0
    count_ignored = 0
    count_already = 0

    for activity in activities:
        activity_id = int(activity["activityId"])

        if activity_id in ignore_set:
            count_ignored += 1
            continue

        if activity_id in imported_set:
            count_already += 1
            continue

        start_local = activity.get("startTimeLocal") or activity.get("startTimeGMT", "")
        date_str = start_local[:10] if start_local else datetime.now(timezone.utc).strftime("%Y-%m-%d")

        map_url = None
        if not args.no_maps:
            points = fetch_activity_points(client, activity_id)
            time.sleep(args.delay)
            if len(points) >= 2:
                distance_km = round((activity.get("distance") or 0) / 1000, 2)
                map_url = write_route_map(
                    activity_id, points,
                    label=f"{distance_km} km", basemap=not args.no_basemap,
                    privacy_trim=not args.no_privacy_trim,
                    refresh_basemap=args.refresh_basemap,
                )
            if len(points) < 2:
                print(f"  no GPS data for {activity_id} (treadmill?) - map skipped")

        path = output_path(date_str)
        path.write_text(activity_to_markdown(activity, map_url))
        imported_set.add(activity_id)
        count_imported += 1
        print(f"  Wrote {path.name}  (activity {activity_id})")

    save_imported_set(imported_set)

    print(
        f"\nDone. Imported: {count_imported}, "
        f"skipped (ignored): {count_ignored}, "
        f"skipped (already imported): {count_already}."
    )


def run_backfill(client: Garmin, args: argparse.Namespace) -> None:
    targets = sorted(args.activity or load_imported_set())
    posts = index_posts_by_activity_id()
    print(f"Backfilling maps for {len(targets)} activities.")

    count_written = 0
    count_existing = 0
    count_no_gps = 0
    count_inserted = 0

    for i, activity_id in enumerate(targets):
        destination = MAPS_DIR / f"{activity_id}.svg"
        map_url: str | None = None

        if destination.exists() and not args.force:
            print(f"  {activity_id}: map exists (use --force to regenerate)")
            count_existing += 1
            map_url = f"{MAP_URL_PREFIX}/{activity_id}.svg"
        else:
            points = fetch_activity_points(client, activity_id)
            if i < len(targets) - 1:
                time.sleep(args.delay)
            if len(points) >= 2:
                map_url = write_route_map(
                    activity_id, points, basemap=not args.no_basemap,
                    privacy_trim=not args.no_privacy_trim,
                    refresh_basemap=args.refresh_basemap,
                )
            if map_url is None:
                count_no_gps += 1
                continue
            count_written += 1

        post = posts.get(activity_id)
        if post is None:
            print(f"  {activity_id}: no post found; add manually: {route_shortcode(map_url)}")
        elif insert_route_shortcode(post, route_shortcode(map_url)):
            print(f"  {activity_id}: inserted into {post.name}")
            count_inserted += 1
        else:
            print(f"  {activity_id}: already linked in {post.name}")

    print(
        f"\nDone. Maps written: {count_written}, "
        f"already present: {count_existing}, "
        f"no GPS: {count_no_gps}, "
        f"posts updated: {count_inserted}."
    )


def synthetic_points() -> list[Point]:
    """A figure-eight with a known speed profile, a spike, and a gap."""
    points: list[Point] = []
    for i in range(1200):
        a = i / 1199 * 4 * math.pi
        lat = 43.6532 + 0.010 * math.sin(a)
        lon = -79.3832 + 0.014 * math.sin(a / 2)
        speed: float | None = 2.4 + 1.6 * math.sin(a / 2) ** 2  # 2.4-4.0 m/s
        if i % 97 == 0:
            speed = 12.0          # spike: must be clipped away
        if 400 <= i < 410:
            speed = None          # gap: must be filled
        points.append((lat, lon, speed))
    return points


def run_selftest(path: Path) -> None:
    """Check the map maths and write a sample SVG. Needs no credentials."""
    assert percentile([1, 2, 3, 4], 50) == 2.5, "percentile is wrong"
    assert ramp_hex(0.0) == "#001A66", ramp_hex(0.0)
    assert ramp_hex(1.0) == "#D9EBFF", ramp_hex(1.0)
    assert len(RAMP_LIGHT_HEX) == len(RAMP_DARK_HEX) == RAMP_BUCKETS
    assert fill_none([None, None, 3.0, None]) == [3.0, 3.0, 3.0, 3.0]

    # Darker is faster: the fastest bucket must be darker than the slowest.
    def luminance(hex_colour: str) -> int:
        r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
        return 2 * r + 5 * g + b
    for table, name in ((RAMP_LIGHT_HEX, "light"), (RAMP_DARK_HEX, "dark")):
        assert luminance(table[-1]) < luminance(table[0]), f"{name} ramp is not inverted"

    # Privacy trim: the real ends must be gone, the result must stay contiguous,
    # and the same activity id must always give the same cut.
    points = synthetic_points()
    kept, cut = trim_route_ends(points, 42)
    assert 0 < cut <= PRIVACY_TRIM_MAX_M, cut
    assert kept[0] != points[0] and kept[-1] != points[-1], "the real ends survived"
    first_index = points.index(kept[0])
    assert points[first_index:first_index + len(kept)] == kept, "kept run is not contiguous"
    # Both ends must be cut by at least `cut` metres along the path.
    steps = [distance_m(a, b) for a, b in zip(points, points[1:])]
    assert sum(steps[:first_index]) >= cut * 0.9, "the start was barely cut"
    tail = first_index + len(kept)
    assert sum(steps[tail - 1:]) >= cut * 0.9, "the end was barely cut"
    assert trim_route_ends(points, 42)[1] == cut, "the cut is not stable per activity"
    assert trim_route_ends(points, 43)[1] != cut, "the cut does not vary per activity"
    assert trim_route_ends(points, 42, False)[0] == points, "--no-privacy-trim ignored"
    # A lap run: every sample near the start, which a radius trim cannot handle.
    laps = [(43.65 + 0.0004 * math.sin(i / 40), -79.38 + 0.0005 * math.cos(i / 40), 3.0)
            for i in range(1500)]
    lap_kept, lap_cut = trim_route_ends(laps, 7)
    assert len(lap_kept) >= 2 and lap_cut > 0, "a lap run must still get a trim"
    print(f"  privacy trim: {cut:.0f} m cut {len(points) - len(kept)} of {len(points)} samples")

    track = prepare_track(points)
    px, sm, lo, hi = track.px, track.speeds, track.lo, track.hi
    # The synthetic profile tops out at 4.0 m/s; the 12.0 spikes must not leak
    # into the range through the smoothing window.
    assert hi < 4.2, f"speed spike was not clipped: {hi}"

    # Seam invariant: every run must start on the previous run's last vertex.
    buckets = [bucket_of(fmean((sm[i], sm[i + 1])), lo, hi) for i in range(len(px) - 1)]
    runs = merge_runs(px, buckets)
    for a, b in zip(runs, runs[1:]):
        assert a[1][-1] == b[1][0], "colour runs do not share a vertex (seams!)"

    # Degenerate inputs must return None, not raise.
    for name, bad in (
        ("empty", []),
        ("single point", [(43.65, -79.38, 3.0)]),
        ("identical points", [(43.65, -79.38, 3.0)] * 50),
    ):
        assert route_map_svg(bad) is None, f"{name} should not produce a map"
    assert route_map_svg([(lat, lon, None) for lat, lon, _ in points]) is not None

    svg = route_map_svg(points, label="10.1 km")
    assert svg is not None
    path.write_text(svg)

    print(f"Wrote {path} ({len(svg.encode()) / 1024:.1f} KB)")
    print(f"  points after decimation: {len(px)}")
    print(f"  polylines: {svg.count('<polyline')}")
    print(f"  buckets used: {min(buckets)}..{max(buckets)}")
    print(f"  legend: {format_pace_from_speed(lo)}/km (slow) → {format_pace_from_speed(hi)}/km (fast)")
    print("All self-test assertions passed.")


def main() -> None:
    args = parse_args()

    # Before the credential check: the self-test never talks to Garmin.
    if args.selftest:
        run_selftest(Path(args.selftest))
        return

    load_dotenv(SCRIPTS_DIR / ".env")
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    if not email or not password:
        raise SystemExit(
            "GARMIN_EMAIL and GARMIN_PASSWORD must be set in environment or scripts/.env"
        )

    client = authenticate(email, password)

    if args.backfill_maps:
        run_backfill(client, args)
    else:
        run_import(client, args)


if __name__ == "__main__":
    main()
