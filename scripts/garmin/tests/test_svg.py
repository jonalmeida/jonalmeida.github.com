"""Drawing the route. Ported from the map half of the old run_selftest."""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from statistics import fmean

import pytest

from garminrun.ramp import RAMP_BUCKETS, bucket_of
from garminrun.svg import merge_runs, route_map_svg
from garminrun.synthetic import synthetic_points
from garminrun.track import prepare_track

SVG_NS = "{http://www.w3.org/2000/svg}"


@pytest.fixture(scope="module")
def points():
    return synthetic_points()


@pytest.fixture(scope="module")
def track(points):
    return prepare_track(points)


# ---------------------------------------------------------------------------
# Speed handling
# ---------------------------------------------------------------------------

def test_a_speed_spike_does_not_stretch_the_colour_range(track):
    """The synthetic profile tops out at 4.0 m/s and plants 12.0 m/s spikes.

    Clamping happens before smoothing, so a spike cannot leak into its
    neighbours through the window and drag the whole legend with it.
    """
    assert track.hi < 4.2, track.hi


def test_the_colour_runs_share_their_seam_vertices(track):
    """Each polyline must start on the previous one's last point.

    Otherwise the map shows a hairline gap at every colour change.
    """
    buckets = [
        bucket_of(fmean((track.speeds[i], track.speeds[i + 1])), track.lo, track.hi)
        for i in range(len(track.px) - 1)
    ]
    runs = merge_runs(track.px, buckets)
    for earlier, later in zip(runs, runs[1:]):
        assert earlier[1][-1] == later[1][0], "colour runs do not share a vertex"


# ---------------------------------------------------------------------------
# Degenerate input
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, route", [
    ("empty", []),
    ("a single point", [(43.65, -79.38, 3.0)]),
    ("the same point repeated", [(43.65, -79.38, 3.0)] * 50),
])
def test_nothing_worth_drawing_returns_none(name, route):
    """None, never an exception: a missing map must not cost the post."""
    assert route_map_svg(route) is None, name


def test_a_route_with_no_speed_data_still_draws(points):
    """An older watch, or a lost heart-rate pairing. The route is still a route."""
    assert route_map_svg([(lat, lon, None) for lat, lon, _ in points]) is not None


# ---------------------------------------------------------------------------
# The output
# ---------------------------------------------------------------------------

def test_the_svg_parses(points):
    """A malformed SVG renders as nothing at all; substring counting misses that."""
    root = ElementTree.fromstring(route_map_svg(points, label="10.1 km"))
    assert root.tag == f"{SVG_NS}svg"


def test_the_route_is_drawn_as_polylines(points):
    root = ElementTree.fromstring(route_map_svg(points, label="10.1 km"))
    route = [e for e in root.iter(f"{SVG_NS}polyline")
             if (e.get("class") or "").startswith("s")]
    assert len(route) > 1


def test_every_bucket_has_a_dark_theme_rule(points):
    """The light palette rides on the stroke attribute and is the fallback.

    Dark mode is CSS inside the file, so a missing rule means an invisible
    stretch of route for readers on a dark background.
    """
    svg = route_map_svg(points, label="10.1 km")
    assert "@media (prefers-color-scheme:dark)" in svg
    for bucket in range(RAMP_BUCKETS):
        assert f".s{bucket}{{stroke:" in svg, bucket


def test_the_label_reaches_the_title_and_the_aria_label(points):
    """What a screen reader announces, and what --backfill-maps used to drop."""
    svg = route_map_svg(points, label="10.1 km")
    root = ElementTree.fromstring(svg)
    assert "10.1 km" in root.get("aria-label")
    assert "10.1 km" in root.find(f"{SVG_NS}title").text


def test_a_route_without_a_basemap_stays_small(points):
    """No basemap means no Overpass query and a much smaller file."""
    assert len(route_map_svg(points).encode()) < 40_000
