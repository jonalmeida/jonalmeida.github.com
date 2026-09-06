"""From a Garmin details payload to a route: parsing, geodesy, statistics.

Everything here is pure and offline. The privacy trim lives here too, because
it is geometry: it cuts a piece off each end of the track so the real start and
finish never reach a published file.
"""

from __future__ import annotations

import math
import random
from statistics import fmean


AUTO_RANGE_PCT = 10.0         # percentile clip on speed


MOVING_MIN_MS = 1.0           # below this the watch is stopped, not running


# Privacy: cut a piece off each end of the route, so the real start and finish
# never reach the file. The radius is random per activity.
PRIVACY_TRIM_MIN_M = 400.0


PRIVACY_TRIM_MAX_M = 800.0


PRIVACY_MAX_ROUTE_SHARE = 0.075  # cap the radius at this share of the route length


# A trim must leave at least this much of a run. Keep it well below half: a
# route that passes its own start in the middle gets split there, so the longest
# contiguous stretch left is under half whatever radius we choose.
PRIVACY_KEEP_FRACTION = 0.35


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
