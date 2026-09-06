"""The publish rules and the marker stripping.

Ported from the old selftest_filter, which had to hand-build argparse.Namespace
objects with exactly the right attribute names. publish_decision now takes a
FilterRules, so the rules a test wants are the rules it writes.
"""

from __future__ import annotations

import pytest

from garminrun.filters import (
    PRIVATE_MARKERS,
    FilterRules,
    publish_decision,
    strip_markers,
)
from garminrun.postfmt import activity_to_markdown

DEFAULT = FilterRules(private_markers=PRIVATE_MARKERS)
STRICT = FilterRules(
    private_markers=PRIVATE_MARKERS,
    allowed_privacy=frozenset({"public", "subscribers", "groups"}),
)
LOOSE = FilterRules(private_markers=PRIVATE_MARKERS, no_content_filter=True)


def decide(rules: FilterRules = DEFAULT, **fields):
    return publish_decision({"activityName": "Run", **fields}, rules)


# ---------------------------------------------------------------------------
# What publishes
# ---------------------------------------------------------------------------

def test_a_run_with_prose_publishes():
    """Real posts must keep publishing."""
    assert decide(description="Nice day, flat route.") == (True, "")


def test_garmins_own_auto_name_is_not_a_signal():
    """'Lisbon Running' is Garmin's auto-name and is a published post.

    The name is never the signal by itself - only a marker in it is.
    """
    assert decide(activityName="Lisbon Running", description="Prose.") == (True, "")


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field, text, reason", [
    ("description", "Great run #nopost", "marker #nopost"),
    ("description", "Great run #NoPost", "marker #nopost"),
    ("description", "Great run #PRIVATE", "marker #private"),
    ("activityName", "Run #private", "marker #private"),
    ("activityName", "Run #nopost", "marker #nopost"),
])
def test_a_marker_anywhere_stops_the_post(field, text, reason):
    """Typed on the phone, in either box, in any case."""
    fields = {"description": "x", field: text}
    assert decide(**fields) == (False, reason)


def test_a_longer_word_does_not_fire():
    """'#' is not a word character, so only the trailing guard matters."""
    assert decide(description="Sent a #nopostcard from Lisbon") == (True, "")


# ---------------------------------------------------------------------------
# The empty-description rule
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("description", ["", "   \n  "])
def test_nothing_written_means_it_was_not_written_for_the_blog(description):
    assert decide(description=description) == (False, "no description")


def test_a_missing_description_key_is_the_same_as_an_empty_one():
    assert decide() == (False, "no description")


def test_an_empty_description_is_not_a_retraction():
    """for_retract asks a different question: has consent been withdrawn?

    An absence is not a withdrawal, and prose is often written into the post
    rather than into Garmin. content/runs/2026-08-14-run-2026-08-14.md is
    exactly that post, and it must not be flagged twice a day forever.
    """
    assert publish_decision(
        {"activityName": "Run", "description": ""}, DEFAULT, for_retract=True
    ) == (True, "")


def test_a_marker_still_retracts():
    assert publish_decision(
        {"activityName": "Run", "description": "x #nopost"}, DEFAULT, for_retract=True
    ) == (False, "marker #nopost")


# ---------------------------------------------------------------------------
# Garmin's own privacy setting
# ---------------------------------------------------------------------------

def test_privacy_is_ignored_unless_asked_for():
    """Every activity is 'groups' today, so an allow-list would skip everything."""
    assert decide(description="x", privacy={"typeKey": "private"}) == (True, "")


def test_an_allow_list_rejects_a_value_outside_it():
    assert decide(STRICT, description="x", privacy={"typeKey": "private"}) \
        == (False, "privacy=private")


def test_an_allow_list_accepts_a_value_inside_it():
    assert decide(STRICT, description="x", privacy={"typeKey": "groups"}) == (True, "")


# ---------------------------------------------------------------------------
# The bypass
# ---------------------------------------------------------------------------

def test_no_content_filter_bypasses_everything():
    assert publish_decision({"activityName": "R", "description": ""}, LOOSE) == (True, "")


# ---------------------------------------------------------------------------
# Stripping
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, tidy", [
    ("Great run #nopost", "Great run"),
    ("#nopost\n\nStill prose.", "Still prose."),
    ("a #nopost b", "a  b"),
    ("trailing   \nspaces  ", "trailing\nspaces"),
    ("keep #nopostcard", "keep #nopostcard"),
])
def test_strip_markers(raw, tidy):
    assert strip_markers(raw) == tidy


def test_the_marker_never_survives_into_a_published_post():
    """A --no-content-filter rescue run publishes a marked activity.

    The marker is the private signal. A post is public forever once pushed, so
    this is the assertion that matters most in this file.
    """
    published = activity_to_markdown({
        "activityId": 1,
        "activityName": "Run #nopost",
        "startTimeLocal": "2026-09-06 08:00:00",
        "distance": 5000.0,
        "duration": 1500.0,
        "description": "Prose. #nopost",
    })
    for marker in PRIVATE_MARKERS:
        assert marker not in published.lower()
