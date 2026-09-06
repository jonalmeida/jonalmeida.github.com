"""Checks against the committed posts, not against the code.

These read content/runs/ as it stands in the repo. They are cheap, and they
catch the class of problem that a unit test cannot see: a post that was written
by an older version of the importer and is still wrong on the live site.
"""

from __future__ import annotations

import re

import pytest

from garminrun import config
from garminrun.posts import index_posts_by_activity_id

ZONE_LINE = re.compile(
    r'^    - \{ zone: \d+, name: "[^"]*", pct: ([\d.]+) \}$', re.MULTILINE
)


def published_posts():
    """Every post in the real content/runs/, flat and bundled."""
    return sorted(index_posts_by_activity_id().items())


def test_there_are_posts_to_check():
    """Guard the guard: a broken glob would make every test below vacuous."""
    assert len(published_posts()) > 20


@pytest.mark.parametrize("activity_id, post", published_posts())
def test_no_post_carries_a_chart_of_nothing(activity_id, post):
    """A run recorded without a heart-rate strap must have no chart at all.

    Garmin sends all five hrTimeInZone_* keys as zeroes for those runs, and the
    importer used to turn that into five 0.0 entries: a chart of nothing, a
    feed table of nothing, and mermaid.min.js loaded to draw neither.
    """
    text = post.read_text()
    percentages = [float(pct) for pct in ZONE_LINE.findall(text)]
    if not percentages:
        return
    assert sum(percentages) > 0, (
        f"{post.relative_to(config.PATHS.repo)} has an hr_zones block where "
        "every zone is 0.0; it should have none"
    )


@pytest.mark.parametrize("activity_id, post", published_posts())
def test_the_mermaid_flag_matches_whether_there_is_a_chart(activity_id, post):
    """`mermaid: true` loads a script. It has to earn it."""
    text = post.read_text()
    assert ("mermaid: true" in text) == ("{% <mermaid> %}" in text), (
        f"{post.relative_to(config.PATHS.repo)} sets the mermaid flag and the "
        "chart inconsistently"
    )


@pytest.mark.parametrize("activity_id, post", published_posts())
def test_no_post_leaks_a_private_marker(activity_id, post):
    """The one that would matter most. Cheap enough to check on every run."""
    from garminrun.filters import PRIVATE_MARKERS

    lowered = post.read_text().lower()
    for marker in PRIVATE_MARKERS:
        assert marker not in lowered, (
            f"{post.relative_to(config.PATHS.repo)} contains {marker}"
        )
