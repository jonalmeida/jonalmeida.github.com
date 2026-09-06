"""A route in pixel space: fit it to the panel, then thin it.

Track is the shared transform. The route and the OSM basemap have to agree
about where a latitude and longitude land, so both go through Track.to_px.
"""

from __future__ import annotations

import math
from statistics import fmean
from typing import NamedTuple

from garminrun.geo import (
    EARTH_R,
    Point,
    fill_none,
    project,
    rolling_mean,
    speed_range,
)


# Route map tuning
SVG_WIDTH, SVG_PAD, LEGEND_H = 640, 14, 46


MAP_MIN_H, MAP_MAX_H = 200, 560


MAX_MAP_POINTS = 600          # after decimation


MIN_STEP_PX = 0.6             # drop points closer than this (stopped at a light)


SPEED_SMOOTH_WINDOW = 5       # samples, odd, centred


MIN_BBOX_M = 20.0             # smaller than this is not a real route


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
