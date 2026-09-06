"""Formatting an activity into post markdown. Ported from selftest_posts."""

from __future__ import annotations

import pytest

from garminrun.postfmt import (
    GALLERY_SHORTCODE,
    activity_date,
    activity_to_markdown,
    format_duration,
    format_pace,
    format_pace_from_speed,
    hr_zone_percentages,
    yaml_dq,
)

LISBON = {
    "activityId": 24206823662,
    "activityName": 'Lisbon "Running"',
    "startTimeLocal": "2026-09-02 08:31:00",
    "distance": 6030.0,
    "duration": 1949.0,
    "elevationGain": 7.0,
    "description": "Burning off yesterday's wining and dining.",
}


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seconds, formatted", [
    (0, "0:00"),
    (59, "0:59"),
    (59.6, "1:00"),
    (600, "10:00"),
    (3599, "59:59"),
    (3600, "1:00:00"),
    (3602, "1:00:02"),
])
def test_format_duration(seconds, formatted):
    """MM:SS below an hour, H:MM:SS at or above it."""
    assert format_duration(seconds) == formatted


@pytest.mark.parametrize("seconds, formatted", [(295, "4:55"), (60, "1:00"), (5, "0:05")])
def test_format_pace(seconds, formatted):
    assert format_pace(seconds) == formatted


def test_pace_from_speed():
    assert format_pace_from_speed(1000 / 295) == "4:55"


@pytest.mark.parametrize("speed", [0.0, 0.1, 0.39])
def test_a_standing_watch_has_no_pace(speed):
    """Dividing by a speed near zero gives a pace of hours per km."""
    assert format_pace_from_speed(speed) == "--:--"


# ---------------------------------------------------------------------------
# YAML
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, escaped", [
    ('a "b" c', 'a \\"b\\" c'),
    ("back\\slash", "back\\\\slash"),
    ('both " and \\', 'both \\" and \\\\'),
    ("nothing to do", "nothing to do"),
])
def test_yaml_dq(raw, escaped):
    """A double-quoted YAML scalar: backslash first, then the quote."""
    assert yaml_dq(raw) == escaped


def test_the_title_is_escaped_in_the_front_matter():
    """An unescaped quote here makes Zola fail to parse the whole post."""
    assert 'title: "Lisbon \\"Running\\""' in activity_to_markdown(LISBON)


# ---------------------------------------------------------------------------
# The date
# ---------------------------------------------------------------------------

def test_the_date_comes_from_the_local_start():
    assert activity_date(LISBON) == "2026-09-02"


def test_gmt_is_the_fallback():
    """A run just after midnight local is the case that tells these apart."""
    assert activity_date({"startTimeGMT": "2026-09-03 01:15:00"}) == "2026-09-03"


def test_local_wins_over_gmt():
    assert activity_date(
        {"startTimeLocal": "2026-09-02 21:15:00", "startTimeGMT": "2026-09-03 01:15:00"}
    ) == "2026-09-02"


# ---------------------------------------------------------------------------
# Heart rate zones
# ---------------------------------------------------------------------------

def test_the_zones_add_up_and_run_from_five_down():
    zones = hr_zone_percentages({f"hrTimeInZone_{n}": 100.0 for n in range(1, 6)})
    assert [zone for zone, _ in zones] == [5, 4, 3, 2, 1]
    assert sum(pct for _, pct in zones) == pytest.approx(100.0)


def test_no_zone_data_means_no_chart():
    assert hr_zone_percentages({"activityId": 1}) == []


def test_a_run_with_no_heart_rate_still_reports_five_empty_zones():
    """Current behaviour, not desired behaviour.

    Garmin sends the hrTimeInZone_* keys as zeroes for a run recorded without
    a strap, and `total = sum(...) or 1` then yields five 0.0 entries rather
    than none. The post gets `mermaid: true` and an empty chart. Pinned here so
    the split does not change it by accident; worth fixing separately.
    """
    zones = hr_zone_percentages({f"hrTimeInZone_{n}": 0.0 for n in range(1, 6)})
    assert zones == [(5, 0.0), (4, 0.0), (3, 0.0), (2, 0.0), (1, 0.0)]


# ---------------------------------------------------------------------------
# The gallery
# ---------------------------------------------------------------------------

def test_a_photoless_post_has_no_gallery():
    assert GALLERY_SHORTCODE not in activity_to_markdown(LISBON, "/runs/maps/1.svg")


def test_the_gallery_sits_on_the_seam_before_the_stats_table():
    """Which is where every hand-made post put it."""
    text = activity_to_markdown(LISBON, "/runs/maps/1.svg", photos=3)
    assert f"\n\n{GALLERY_SHORTCODE}\n\n| Stat | Value |" in text
