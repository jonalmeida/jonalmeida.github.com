"""run_import end to end, against a fake Garmin and a temporary repo.

This is the test that would have caught most of the things the plan worried
about: the wrapper contract, the deferral invariant, and the rule that an
activity is either fully imported or not recorded at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from garminrun import cli, photos
from garminrun.cli import parse_args, run_import
from garminrun.state import load_ignore_set, load_imported_set

WIDE_JPEG = (Path(__file__).resolve().parent / "data" / "wide.jpg").read_bytes()

REPORT_KEYS = {"imported_count", "imported", "filtered_count",
               "deferred_count", "retract_candidates"}


def activity(activity_id, date="2026-09-06", **overrides):
    base = {
        "activityId": activity_id,
        "activityName": "Toronto - Easy Run",
        "description": "Legs felt fine.",
        "startTimeLocal": f"{date} 07:12:31",
        "distance": 10000.0,
        "duration": 3000.0,
        "elevationGain": 42.0,
    }
    base.update(overrides)
    return base


@pytest.fixture
def run(repo, fake_client, no_sleep, monkeypatch, capsys):
    """Run the importer with maps and photos off unless a test asks for them."""
    repo.ignore.write_text("")

    def go(*flags, photos_listing=None, photo_bytes=WIDE_JPEG):
        if photos_listing is not None:
            for activity_id, listing in photos_listing.items():
                fake_client.full[activity_id] = {
                    "metadataDTO": {"activityImages": listing}
                }
            monkeypatch.setattr(photos, "_fetch", lambda url: photo_bytes)
        args = parse_args(list(flags))
        run_import(fake_client, args)
        return capsys.readouterr().out

    go.client = fake_client
    go.repo = repo
    return go


def bundle(repo, slug="2026-09-06-run-2026-09-06"):
    return repo.content_runs / slug


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------

def test_a_run_becomes_a_page_bundle(run, repo):
    run.client.activities = [activity(1)]
    run("--no-maps", "--no-photos")

    post = bundle(repo) / "index.md"
    assert post.is_file()
    text = post.read_text()
    assert "garmin_activity_id: 1" in text
    assert "distance_km: 10.0" in text
    assert 'duration: "50:00"' in text
    assert "Legs felt fine." in text


def test_the_id_is_recorded_so_it_is_never_redone(run, repo):
    run.client.activities = [activity(1)]
    run("--no-maps", "--no-photos")
    assert load_imported_set() == {1}


def test_a_second_run_does_nothing(run, repo):
    run.client.activities = [activity(1)]
    run("--no-maps", "--no-photos")
    out = run("--no-maps", "--no-photos")
    assert "skipped (already imported): 1" in out


def test_two_runs_on_one_day_get_separate_bundles(run, repo):
    run.client.activities = [activity(1), activity(2)]
    run("--no-maps", "--no-photos")
    assert (bundle(repo) / "index.md").is_file()
    assert (bundle(repo, "2026-09-06-run-2026-09-06-2") / "index.md").is_file()


def test_max_new_stops_early_so_each_commit_holds_one_run(run, repo):
    """The scheduled job uses --max-new 1, so every run gets its own commit."""
    run.client.activities = [activity(1), activity(2, date="2026-09-07")]
    run("--no-maps", "--no-photos", "--max-new", "1")
    assert load_imported_set() == {1}


# ---------------------------------------------------------------------------
# The filter
# ---------------------------------------------------------------------------

def test_a_marked_run_is_skipped_and_remembered(run, repo):
    run.client.activities = [activity(1, description="Secret loop #nopost")]
    run("--no-maps", "--no-photos")

    assert not bundle(repo).exists(), "a post was written for a marked run"
    assert 1 in load_ignore_set()
    assert load_imported_set() == set()


def test_the_reason_never_reaches_the_public_ignore_file(run, repo):
    """garmin_ignore.txt is tracked and published. A trailing '# marker #nopost'
    would leak exactly the thing the marker was meant to hide."""
    run.client.activities = [activity(1, description="Secret loop #nopost")]
    run("--no-maps", "--no-photos")

    text = repo.ignore.read_text()
    assert "1" in text
    assert "nopost" not in text
    assert "#" not in text.replace("\n", ""), text


def test_a_run_with_no_prose_is_skipped(run, repo):
    run.client.activities = [activity(1, description="")]
    run("--no-maps", "--no-photos")
    assert not bundle(repo).exists()
    assert 1 in load_ignore_set()


def test_an_ignored_id_is_never_reconsidered(run, repo):
    repo.ignore.write_text("1\n")
    run.client.activities = [activity(1)]
    out = run("--no-maps", "--no-photos")
    assert "skipped (ignored): 1" in out
    assert not bundle(repo).exists()


# ---------------------------------------------------------------------------
# Photos, and the deferral invariant
# ---------------------------------------------------------------------------

def test_photos_land_in_the_bundle_and_the_post_gets_a_gallery(run, repo):
    run.client.activities = [activity(1)]
    run("--no-maps", photos_listing={1: [
        {"url": "https://s3.example/a.jpg", "imageId": "a"},
        {"url": "https://s3.example/b.jpg", "imageId": "b"},
    ]})

    assert (bundle(repo) / "2026-09-06-0.jpg").is_file()
    assert (bundle(repo) / "2026-09-06-1.jpg").is_file()
    assert "<gallery" in (bundle(repo) / "index.md").read_text()


def test_a_photo_failure_leaves_nothing_behind_and_records_nothing(
    run, repo, monkeypatch
):
    """The activity has to come back intact on the next run.

    A bundle with no index.md is invisible to Zola, so a half-written import is
    not published - but it must not leave litter either, and above all the id
    must stay out of garmin_imported.json.
    """
    run.client.activities = [activity(1)]
    run.client.full[1] = {"metadataDTO": {"activityImages": [
        {"url": "https://s3.example/a.jpg", "imageId": "a"},
    ]}}
    monkeypatch.setattr(photos, "_fetch", lambda url: (_ for _ in ()).throw(
        RuntimeError("S3 said no")))

    out = run("--no-maps")
    assert "deferring 1" in out
    assert load_imported_set() == set(), "a failed import was recorded as done"
    assert 1 not in load_ignore_set(), "a failed import was blacklisted"
    assert not (bundle(repo) / "index.md").exists()
    assert not list(repo.content_runs.rglob("*.jpg")), "partial photos were left"


def test_a_photo_list_failure_defers_without_touching_the_disk(run, repo, monkeypatch):
    def explode(activity_id):
        raise RuntimeError("500")

    run.client.activities = [activity(1)]
    monkeypatch.setattr(run.client, "get_activity", explode)

    out = run("--no-maps")
    assert "deferring 1" in out
    assert load_imported_set() == set()
    assert not bundle(repo).exists()


# ---------------------------------------------------------------------------
# The map
# ---------------------------------------------------------------------------

def test_a_map_is_written_and_linked(run, repo, monkeypatch):
    from garminrun.synthetic import synthetic_points

    points = synthetic_points()
    monkeypatch.setattr(cli, "fetch_activity_points", lambda client, i: points)
    run.client.activities = [activity(1)]

    run("--no-photos", "--no-basemap")

    assert (repo.maps / "1.svg").is_file()
    assert "/runs/maps/1.svg" in (bundle(repo) / "index.md").read_text()


def test_no_gps_means_no_map_but_still_a_post(run, repo):
    """A treadmill run."""
    run.client.activities = [activity(1)]
    out = run("--no-photos", "--no-basemap")
    assert "no GPS data" in out
    assert (bundle(repo) / "index.md").is_file()
    assert not (repo.maps / "1.svg").exists()


# ---------------------------------------------------------------------------
# The report the wrapper reads with jq
# ---------------------------------------------------------------------------

def test_the_report_carries_every_key_the_wrapper_reads(run, repo, tmp_path):
    report = tmp_path / "report.json"
    run.client.activities = [activity(1)]
    run("--no-maps", "--no-photos", "--report", str(report))

    data = json.loads(report.read_text())
    assert set(data) == REPORT_KEYS
    assert data["imported_count"] == 1
    assert data["imported"][0]["date"] == "2026-09-06"
    assert data["imported"][0]["activity_id"] == 1
    assert data["imported"][0]["path"].startswith("content/runs/")


def test_the_report_counts_a_deferral_separately_from_a_filter(run, repo, tmp_path):
    """The wrapper treats them differently: a filter is normal, a deferral
    means the next run has work to do."""
    report = tmp_path / "report.json"
    run.client.activities = [
        activity(1, description="nope #nopost"),
        activity(2, date="2026-09-07"),
    ]
    run("--no-maps", "--no-photos", "--report", str(report))

    data = json.loads(report.read_text())
    assert data["filtered_count"] == 1
    assert data["deferred_count"] == 0
    assert data["imported_count"] == 1


# ---------------------------------------------------------------------------
# Retraction
# ---------------------------------------------------------------------------

def test_a_published_run_that_now_fails_the_filter_is_reported_not_deleted(
    run, repo, tmp_path
):
    """Deleting a published post does not unpublish it: readers have the feed
    cached and a linked URL would 404. Not a robot's call at 08:40."""
    report = tmp_path / "report.json"
    run.client.activities = [activity(1)]
    run("--no-maps", "--no-photos")

    run.client.activities = [activity(1, description="Actually private #nopost")]
    out = run("--no-maps", "--no-photos", "--report", str(report))

    assert "RETRACT?" in out
    assert (bundle(repo) / "index.md").is_file(), "the post was deleted"

    data = json.loads(report.read_text())
    assert len(data["retract_candidates"]) == 1
    assert data["retract_candidates"][0]["activity_id"] == 1
    assert data["retract_candidates"][0]["reason"] == "marker #nopost"


def test_retract_draft_takes_it_down_when_asked(run, repo):
    run.client.activities = [activity(1)]
    run("--no-maps", "--no-photos")

    run.client.activities = [activity(1, description="Actually private #nopost")]
    run("--no-maps", "--no-photos", "--retract", "draft")

    assert "\ndraft: true\n" in (bundle(repo) / "index.md").read_text()
