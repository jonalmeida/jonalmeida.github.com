"""Argument parsing and the crontab helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from garminrun.cli import filter_rules, parse_args, print_crontab
from garminrun.filters import PRIVATE_MARKERS
from garminrun.photos import PHOTO_TARGET_WIDTH

WRAPPER = Path(__file__).resolve().parent.parent / "run_import.sh"


# ---------------------------------------------------------------------------
# Post-processing that argparse cannot express
# ---------------------------------------------------------------------------

def test_the_defaults():
    args = parse_args([])
    assert args.private_marker == PRIVATE_MARKERS
    assert args.allowed_privacy == frozenset()
    assert args.photo_width == PHOTO_TARGET_WIDTH
    assert args.max_new == 0


def test_no_photo_resize_zeroes_the_width():
    """Two flags for one setting; the width is what the code actually reads."""
    assert parse_args(["--no-photo-resize"]).photo_width == 0


def test_an_explicit_width_wins_over_the_default():
    assert parse_args(["--photo-width", "1200"]).photo_width == 1200


def test_private_markers_replace_the_defaults_and_repeat():
    args = parse_args(["--private-marker", "#skip", "--private-marker", "#hide"])
    assert args.private_marker == ("#skip", "#hide")


def test_allowed_privacy_is_split_lowered_and_deduped():
    args = parse_args(["--allowed-privacy", " Public , groups ,, PUBLIC "])
    assert args.allowed_privacy == frozenset({"public", "groups"})


def test_activity_ids_repeat_and_stay_integers():
    assert parse_args(["--activity", "1", "--activity", "2"]).activity == [1, 2]


def test_the_sample_map_flag_has_a_default_path():
    assert parse_args(["--sample-map"]).sample_map == "/tmp/route_sample.svg"


def test_selftest_is_still_accepted_as_an_alias():
    """It is in the README and in muscle memory."""
    assert parse_args(["--selftest", "/tmp/x.svg"]).sample_map == "/tmp/x.svg"


# ---------------------------------------------------------------------------
# The rules the flags describe
# ---------------------------------------------------------------------------

def test_filter_rules_are_built_from_the_flags():
    rules = filter_rules(parse_args(
        ["--no-content-filter", "--allowed-privacy", "groups", "--private-marker", "#x"]
    ))
    assert rules.no_content_filter
    assert rules.allowed_privacy == frozenset({"groups"})
    assert rules.private_markers == ("#x",)


# ---------------------------------------------------------------------------
# The crontab line a human copy-pastes
# ---------------------------------------------------------------------------

def test_the_crontab_line_points_at_the_wrapper(capsys):
    print_crontab("8,20")
    out = capsys.readouterr().out
    assert f"40 8,20 * * * /bin/bash {WRAPPER}" in out


@pytest.mark.parametrize("given, slots", [
    ("8,20", "8,20"),
    (" 6 , 18 ,", "6,18"),
    ("7", "7"),
])
def test_the_hours_are_tidied(given, slots, capsys):
    print_crontab(given)
    assert f"40 {slots} * * *" in capsys.readouterr().out
