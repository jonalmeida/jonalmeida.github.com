"""A fake route with known properties, for --sample-map and the tests.

Real GPS traces are a home address, so nothing in the repo may hold one. This
figure-eight carries the awkward cases on purpose: a speed spike that must be
clipped away, and a gap that must be filled.
"""

from __future__ import annotations

import math

from garminrun.geo import Point


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
