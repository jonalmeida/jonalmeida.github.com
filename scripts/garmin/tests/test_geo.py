"""Geodesy, statistics and the privacy trim.

The trim tests are the important ones in this file: trim_route_ends is what
keeps a home address out of a public repo, and git history is forever.
Ported from the old run_selftest.
"""

from __future__ import annotations

import math

import pytest

from garminrun.geo import (
    PRIVACY_KEEP_FRACTION,
    PRIVACY_TRIM_MAX_M,
    distance_m,
    fill_none,
    percentile,
    trim_route_ends,
)
from garminrun.synthetic import synthetic_points


@pytest.fixture(scope="module")
def points():
    return synthetic_points()


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def test_percentile_interpolates():
    assert percentile([1, 2, 3, 4], 50) == 2.5


@pytest.mark.parametrize("pct, expected", [(0, 1), (100, 4)])
def test_percentile_at_the_ends(pct, expected):
    assert percentile([1, 2, 3, 4], pct) == expected


def test_fill_none_fills_backwards_into_a_leading_gap():
    """The watch reports nothing for the first samples more often than not."""
    assert fill_none([None, None, 3.0, None]) == [3.0, 3.0, 3.0, 3.0]


def test_fill_none_on_all_none_gives_zeroes():
    assert fill_none([None, None]) == [0.0, 0.0]


# ---------------------------------------------------------------------------
# Geodesy
# ---------------------------------------------------------------------------

def test_distance_over_a_known_span():
    """One degree of latitude is about 111.2 km on a sphere of EARTH_R."""
    metres = distance_m((43.0, -79.0, None), (44.0, -79.0, None))
    assert 111_100 < metres < 111_300, metres


def test_distance_to_itself_is_zero():
    assert distance_m((43.65, -79.38, None), (43.65, -79.38, None)) == 0.0


# ---------------------------------------------------------------------------
# The privacy trim
# ---------------------------------------------------------------------------

def test_the_real_ends_do_not_survive(points):
    kept, cut = trim_route_ends(points, 42)
    assert 0 < cut <= PRIVACY_TRIM_MAX_M, cut
    assert kept[0] != points[0], "the real start survived"
    assert kept[-1] != points[-1], "the real finish survived"


def test_what_is_kept_is_one_contiguous_stretch(points):
    """A gap would draw a straight line across whatever is between the pieces."""
    kept, _ = trim_route_ends(points, 42)
    first = points.index(kept[0])
    assert points[first:first + len(kept)] == kept


def test_both_ends_are_cut_by_at_least_the_radius(points):
    kept, cut = trim_route_ends(points, 42)
    steps = [distance_m(a, b) for a, b in zip(points, points[1:])]
    first = points.index(kept[0])
    assert sum(steps[:first]) >= cut * 0.9, "the start was barely cut"
    tail = first + len(kept)
    assert sum(steps[tail - 1:]) >= cut * 0.9, "the end was barely cut"


def test_the_cut_is_stable_for_one_activity(points):
    """Seeded from the activity id, so a redraw reproduces the same map.

    This is also what makes `--backfill-maps --force` a no-op diff, which is
    how a change to the drawing code gets verified.
    """
    assert trim_route_ends(points, 42)[1] == trim_route_ends(points, 42)[1]


def test_the_cut_varies_between_activities(points):
    """A fixed radius would be a fixed offset from the real start."""
    assert trim_route_ends(points, 42)[1] != trim_route_ends(points, 43)[1]


def test_the_trim_can_be_turned_off(points):
    kept, cut = trim_route_ends(points, 42, False)
    assert kept == points
    assert cut == 0


def test_enough_of_the_run_is_left(points):
    kept, _ = trim_route_ends(points, 42)
    assert len(kept) >= len(points) * PRIVACY_KEEP_FRACTION


def test_a_lap_run_still_gets_a_trim():
    """Every sample sits inside the start radius, which a radius trim alone
    cannot handle: the route passes its own start over and over."""
    laps = [
        (43.65 + 0.0004 * math.sin(i / 40), -79.38 + 0.0005 * math.cos(i / 40), 3.0)
        for i in range(1500)
    ]
    kept, cut = trim_route_ends(laps, 7)
    assert len(kept) >= 2
    assert cut > 0


@pytest.mark.parametrize("route", [[], [(43.65, -79.38, 3.0)]])
def test_a_route_too_short_to_trim_is_returned_untouched(route):
    kept, cut = trim_route_ends(route, 1)
    assert kept == route
