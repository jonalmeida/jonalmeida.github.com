"""Speed to colour. Ported from the old run_selftest."""

from __future__ import annotations

import pytest

from garminrun.ramp import (
    DARK_SPAN,
    LIGHT_SPAN,
    RAMP_BUCKETS,
    RAMP_DARK_HEX,
    RAMP_LIGHT_HEX,
    bucket_of,
    ramp_hex,
)


def luminance(hex_colour: str) -> int:
    """Rough perceived brightness, weighted 2:5:1. Enough to compare two blues."""
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return 2 * r + 5 * g + b


def test_the_ramp_ends_where_it_says_it_does():
    assert ramp_hex(0.0) == "#001A66"
    assert ramp_hex(1.0) == "#D9EBFF"


def test_both_themes_have_a_full_table():
    assert len(RAMP_LIGHT_HEX) == RAMP_BUCKETS
    assert len(RAMP_DARK_HEX) == RAMP_BUCKETS


@pytest.mark.parametrize("table, name", [(RAMP_LIGHT_HEX, "light"), (RAMP_DARK_HEX, "dark")])
def test_darker_is_faster(table, name):
    """The ramp is walked backwards, so the fastest bucket is the darkest.

    Getting this the wrong way round would be legible but wrong: the legend
    says 'slower -> faster' and the map would contradict it.
    """
    assert luminance(table[-1]) < luminance(table[0]), name


@pytest.mark.parametrize("table", [RAMP_LIGHT_HEX, RAMP_DARK_HEX])
def test_each_theme_stays_inside_its_own_span(table):
    """Near-white blue vanishes on the light background and navy on the dark one.

    Each theme samples a sub-range of the same ramp, which is only useful if
    the sub-ranges really differ.
    """
    assert LIGHT_SPAN != DARK_SPAN
    assert len(set(table)) > 1


def test_a_speed_maps_into_the_table():
    assert bucket_of(5.0, 0.0, 10.0) == RAMP_BUCKETS // 2


@pytest.mark.parametrize("value", [-5.0, 0.0])
def test_at_or_below_the_slow_bound_is_the_first_bucket(value):
    assert bucket_of(value, 0.0, 10.0) == 0


@pytest.mark.parametrize("value", [10.0, 99.0])
def test_at_or_above_the_fast_bound_is_the_last_bucket(value):
    """Clamped, not wrapped: an index past the end would raise on lookup."""
    assert bucket_of(value, 0.0, 10.0) == RAMP_BUCKETS - 1
