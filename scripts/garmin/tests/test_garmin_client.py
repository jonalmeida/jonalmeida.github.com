"""Talking to Garmin, with a stand-in for Garmin.

The retry policies differ on purpose, and the difference is the point of most
of these tests: a failed details fetch costs a map, so it degrades; a failed
photo list could cost the photos for good, so it raises.
"""

from __future__ import annotations

import pytest
from garminconnect import GarminConnectAuthenticationError

from garminrun import garmin_client
from garminrun.garmin_client import (
    NeedsLogin,
    authenticate,
    fetch_activity_points,
    fetch_running_activities,
)
from garminrun.photos import PhotoFailure, fetch_activity_photos


# ---------------------------------------------------------------------------
# The activity list
# ---------------------------------------------------------------------------

def test_activities_come_back_oldest_first(fake_client):
    """--max-new imports the backlog in order, so the sort is load-bearing."""
    fake_client.activities = [
        {"activityId": 3, "startTimeLocal": "2026-09-03 08:00:00"},
        {"activityId": 1, "startTimeLocal": "2026-09-01 08:00:00"},
        {"activityId": 2, "startTimeLocal": "2026-09-02 08:00:00"},
    ]
    assert [a["activityId"] for a in fetch_running_activities(fake_client)] == [1, 2, 3]


def test_an_activity_with_only_a_gmt_time_still_sorts(fake_client):
    fake_client.activities = [
        {"activityId": 2, "startTimeGMT": "2026-09-02 08:00:00"},
        {"activityId": 1, "startTimeLocal": "2026-09-01 08:00:00"},
    ]
    assert [a["activityId"] for a in fetch_running_activities(fake_client)] == [1, 2]


def test_a_rejected_token_asks_for_a_person(fake_client):
    """client.load() only reads a file, so it succeeds even when the token is
    dead. The first real call is where we find out, and the wrapper needs
    exit 2 rather than a traceback."""
    fake_client.fail_with = GarminConnectAuthenticationError("nope")
    with pytest.raises(NeedsLogin):
        fetch_running_activities(fake_client)


# ---------------------------------------------------------------------------
# Details, which may be missing
# ---------------------------------------------------------------------------

def test_no_gps_gives_no_points_rather_than_an_error(fake_client, no_sleep, capsys):
    """A treadmill run. The post is still worth publishing."""
    assert fetch_activity_points(fake_client, 1) == []


def test_a_details_failure_retries_once_then_gives_up_quietly(
    monkeypatch, no_sleep, capsys
):
    """A missing map must never cost the markdown post."""
    calls = []

    class Failing:
        def get_activity_details(self, activity_id, **kwargs):
            calls.append(activity_id)
            raise RuntimeError("429")

    assert fetch_activity_points(Failing(), 7) == []
    assert calls == [7, 7], "it should try exactly twice"
    assert "WARNING" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Photos: empty is not the same as failed
# ---------------------------------------------------------------------------

def test_an_activity_with_no_photos_returns_an_empty_list(fake_client, no_sleep):
    fake_client.full[1] = {"metadataDTO": {"activityImages": []}}
    assert fetch_activity_photos(fake_client, 1) == []


def test_an_entry_without_a_url_is_not_a_photo(fake_client, no_sleep):
    fake_client.full[1] = {"metadataDTO": {"activityImages": [
        {"imageId": "a"}, {"url": "https://s3.example/x.jpg", "imageId": "b"}, "junk",
    ]}}
    assert [i["imageId"] for i in fetch_activity_photos(fake_client, 1)] == ["b"]


def test_a_failed_photo_list_raises(no_sleep, capsys):
    """This is the important one.

    Returning [] here would look exactly like "no photos", the activity would
    be recorded as imported, and the photos would be lost for good - an id in
    garmin_imported.json is never looked at again.
    """
    class Failing:
        def get_activity(self, activity_id):
            raise RuntimeError("500")

    with pytest.raises(PhotoFailure):
        fetch_activity_photos(Failing(), 1)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class FakeGarth:
    def __init__(self):
        self.loaded = None
        self.dumped = None
        self.logged_in = False

    def load(self, path):
        self.loaded = path

    def dump(self, path):
        self.dumped = path

    def login(self, email, password, prompt_mfa=None):
        self.logged_in = True


@pytest.fixture
def fake_garmin(monkeypatch):
    made = []

    class FakeGarmin:
        def __init__(self, email, password):
            self.client = FakeGarth()
            made.append(self)

    monkeypatch.setattr(garmin_client, "Garmin", FakeGarmin)
    return made


def test_a_cached_token_is_loaded_and_nothing_is_typed(repo, fake_garmin, capsys):
    repo.tokenstore.mkdir(parents=True)
    (repo.tokenstore / "garmin_tokens.json").write_text("{}")

    client = authenticate("e", "p", interactive=False)
    assert client.client.loaded == str(repo.tokenstore)
    assert not client.client.logged_in


def test_no_token_and_nobody_watching_exits_rather_than_hangs(repo, fake_garmin):
    """Under cron stdin is /dev/null, so input() would raise a bare EOFError.

    The wrapper wants exit 2 and a .needs_login file instead.
    """
    with pytest.raises(NeedsLogin):
        authenticate("e", "p", interactive=False)


def test_an_interactive_login_saves_the_token(repo, fake_garmin, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt="": "123456")
    client = authenticate("e", "p", interactive=True)
    assert client.client.logged_in
    assert client.client.dumped == str(repo.tokenstore)
    assert repo.tokenstore.is_dir()
