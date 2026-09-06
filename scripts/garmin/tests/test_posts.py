"""Where a post goes, how to find it again, and how to edit it in place.

The insert tests are ported from the old selftest_posts. They run in a tmp_path
through the `repo` fixture rather than the hardcoded /tmp scratch file the
selftest used.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from garminrun.postfmt import GALLERY_SHORTCODE, activity_to_markdown, route_shortcode
from garminrun.posts import (
    index_posts_by_activity_id,
    insert_gallery_shortcode,
    insert_route_shortcode,
    output_path,
    post_dir,
    post_distance_label,
    retract_post,
    slug_for,
)

LISBON = {
    "activityId": 24206823662,
    "activityName": "Lisbon Running",
    "startTimeLocal": "2026-09-02 08:31:00",
    "distance": 6030.0,
    "duration": 1949.0,
    "elevationGain": 7.0,
    "description": "Prose.",
}


def write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body).lstrip())
    return path


# ---------------------------------------------------------------------------
# Slugs and paths
# ---------------------------------------------------------------------------

SAME_DAY = [{"activityId": 11}, {"activityId": 22}, {"activityId": 33}]


def test_the_nth_run_of_a_day_gets_a_suffix():
    assert [slug_for(a, "2026-09-06", SAME_DAY) for a in SAME_DAY] == [
        "2026-09-06-run-2026-09-06",
        "2026-09-06-run-2026-09-06-2",
        "2026-09-06-run-2026-09-06-3",
    ]


def test_the_slug_is_a_pure_function_of_the_activity_list():
    """An import that died halfway wrote files but recorded nothing.

    The next run has to land on the same slug and overwrite it. Probing the
    filesystem would find the partial directory and make a -2 sibling instead.
    """
    once = [slug_for(a, "2026-09-06", SAME_DAY) for a in SAME_DAY]
    assert once == [slug_for(a, "2026-09-06", SAME_DAY) for a in SAME_DAY]


def test_the_slug_ignores_what_is_already_on_disk(repo):
    """With the first run's partial bundle present, the first run is still -1."""
    (repo.content_runs / "2026-09-06-run-2026-09-06").mkdir(parents=True)
    assert slug_for(SAME_DAY[0], "2026-09-06", SAME_DAY) == "2026-09-06-run-2026-09-06"


def test_output_path_creates_nothing(repo):
    """A path getter that makes directories cannot be called to ask a question."""
    path = output_path("2026-09-06-run-2026-09-06")
    assert path == repo.content_runs / "2026-09-06-run-2026-09-06" / "index.md"
    assert not path.parent.exists()


@pytest.mark.parametrize("name, bundle", [
    ("content/runs/x/index.md", "content/runs/x"),
    ("content/runs/x.md", None),
])
def test_post_dir_tells_a_bundle_from_a_flat_post(name, bundle):
    assert post_dir(Path(name)) == (Path(bundle) if bundle else None)


# ---------------------------------------------------------------------------
# Finding posts again
# ---------------------------------------------------------------------------

def test_the_index_finds_both_flat_posts_and_bundles(repo):
    """Both shapes exist in content/runs, and both have to be found."""
    write(repo.content_runs / "flat.md", """
        ---
        extra:
          garmin_activity_id: 111
        ---
        """)
    write(repo.content_runs / "bundle" / "index.md", """
        ---
        extra:
          garmin_activity_id: 222
        ---
        """)
    index = index_posts_by_activity_id()
    assert set(index) == {111, 222}
    assert index[222].name == "index.md"


def test_the_section_index_is_not_a_post(repo):
    """_index.md carries no activity id, so the regex filters it out."""
    write(repo.content_runs / "_index.md", """
        ---
        title: "Runs"
        ---
        """)
    assert index_posts_by_activity_id() == {}


# ---------------------------------------------------------------------------
# The distance label a backfilled map reads back
# ---------------------------------------------------------------------------

def test_distance_label_comes_from_the_post(repo):
    """--backfill-maps has no activity payload, so it reads the post's own number.

    Taking it from the front matter is what makes a forced redraw a no-op: it
    is the same value run_import rounded and wrote in the first place.
    """
    post = write(repo.content_runs / "x" / "index.md", """
        ---
        title: "Toronto - 4x1600"
        extra:
          distance_km: 12.22
          duration: "1:00:02"
        ---
        Four by a mile.
        """)
    assert post_distance_label(post) == "12.22 km"


def test_distance_label_is_empty_when_there_is_nothing_to_read(repo):
    """No post, or a post without the key, means an unlabelled map - not a crash."""
    assert post_distance_label(None) == ""
    post = write(repo.content_runs / "y" / "index.md", """
        ---
        title: "A run from before the importer"
        ---
        Written by hand.
        """)
    assert post_distance_label(post) == ""


# ---------------------------------------------------------------------------
# Inserting into a published post
# ---------------------------------------------------------------------------

def test_the_gallery_insert_lands_on_the_seam(repo):
    """The blank line before the stats table, where hand-made posts put it."""
    post = write(repo.content_runs / "x" / "index.md",
                 activity_to_markdown(LISBON, "/runs/maps/1.svg"))
    assert insert_gallery_shortcode(post)
    assert f"\n\n{GALLERY_SHORTCODE}\n\n| Stat | Value |" in post.read_text()


def test_the_gallery_insert_is_idempotent(repo):
    """A post carries hand-written prose. Running twice must not touch it."""
    post = write(repo.content_runs / "x" / "index.md",
                 activity_to_markdown(LISBON, "/runs/maps/1.svg"))
    insert_gallery_shortcode(post)
    before = post.read_text()
    assert not insert_gallery_shortcode(post)
    assert post.read_text() == before


def test_the_route_insert_goes_above_the_heart_rate_chart(repo):
    post = write(repo.content_runs / "x" / "index.md", """
        ---
        title: "R"
        ---
        Prose.

        ## Heart Rate Zones

        chart
        """)
    assert insert_route_shortcode(post, route_shortcode("/runs/maps/1.svg"))
    text = post.read_text()
    assert text.index("## Route") < text.index("## Heart Rate Zones")


def test_the_route_insert_appends_when_there_is_no_chart(repo):
    post = write(repo.content_runs / "x" / "index.md", """
        ---
        title: "R"
        ---
        Prose.
        """)
    assert insert_route_shortcode(post, route_shortcode("/runs/maps/1.svg"))
    assert post.read_text().rstrip().endswith("/> }}")


def test_the_route_insert_is_idempotent(repo):
    post = write(repo.content_runs / "x" / "index.md", """
        ---
        title: "R"
        ---
        Prose.
        """)
    shortcode = route_shortcode("/runs/maps/1.svg")
    insert_route_shortcode(post, shortcode)
    before = post.read_text()
    assert not insert_route_shortcode(post, shortcode)
    assert post.read_text() == before


# ---------------------------------------------------------------------------
# Taking a post back down
# ---------------------------------------------------------------------------

def test_retract_draft_flips_the_flag_once(repo):
    """Zola excludes a draft from the build, leaving the file and its history."""
    post = write(repo.content_runs / "x" / "index.md",
                 activity_to_markdown(LISBON, "/runs/maps/1.svg"))
    assert retract_post(post, 24206823662, "draft")
    assert "\ndraft: true\n" in post.read_text()
    assert not retract_post(post, 24206823662, "draft"), "not idempotent"


def test_retract_delete_removes_the_bundle_the_map_and_records_the_id(repo):
    """Delete has to reach all three, or the run comes straight back."""
    post = write(repo.content_runs / "x" / "index.md",
                 activity_to_markdown(LISBON, "/runs/maps/1.svg"))
    svg = repo.maps / "24206823662.svg"
    svg.write_text("<svg/>")
    repo.ignore.write_text("")

    assert retract_post(post, 24206823662, "delete")
    assert not post.parent.exists(), "the bundle survived"
    assert not svg.exists(), "the map survived"
    assert "24206823662" in repo.ignore.read_text(), "the id was not recorded"


def test_retract_delete_of_a_flat_post_leaves_the_directory(repo):
    post = write(repo.content_runs / "flat.md",
                 activity_to_markdown(LISBON, "/runs/maps/1.svg"))
    repo.ignore.write_text("")
    assert retract_post(post, 24206823662, "delete")
    assert not post.exists()
    assert repo.content_runs.is_dir()
