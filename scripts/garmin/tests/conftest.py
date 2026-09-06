"""Shared fixtures for the Garmin importer tests.

Nothing here touches the network, Garmin, or the real repo. Every test that
writes runs inside pytest's ``tmp_path``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

GARMIN_DIR = Path(__file__).resolve().parent.parent
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

# `uv run import_garmin_runs.py` puts scripts/garmin/ on sys.path[0], which
# is how the entry point reaches the garminrun package. Do the same here so
# the tests import it by exactly the same route.
if str(GARMIN_DIR) not in sys.path:
    sys.path.insert(0, str(GARMIN_DIR))


# ---------------------------------------------------------------------------
# The code under test
# ---------------------------------------------------------------------------

def _load_importer():
    """The importer's public surface, as one namespace.

    Was: load import_garmin_runs.py by path, because it was a 2568-line script
    with no import path. Now the entry point is a shim and the code lives in
    the garminrun package, so this is a thin facade for the handful of tests
    that assert on the CLI end of it. Everything else imports the module it
    is actually testing.
    """
    from garminrun import cli, garmin_client, maps, posts, svg

    class Importer:
        pass

    surface = Importer()
    for module in (cli, garmin_client, maps, posts, svg):
        for name in dir(module):
            if not name.startswith("__"):
                setattr(surface, name, getattr(module, name))
    return surface


@pytest.fixture(scope="session")
def importer():
    """The importer module. Session-scoped: loading it is not free."""
    return _load_importer()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Point the importer at an empty repo under tmp_path, and return it.

    One setattr covers every path the importer reads or writes, because they
    all hang off config.PATHS and are read at call time. The layout mirrors the
    real one, so nothing has to know it is in a temporary directory.
    """
    from garminrun import config

    scripts = tmp_path / "scripts" / "garmin"
    scripts.mkdir(parents=True)
    paths = config.paths_for(scripts, tmp_path)
    paths.content_runs.mkdir(parents=True)
    paths.maps.mkdir(parents=True)
    monkeypatch.setattr(config, "PATHS", paths)
    return paths


# ---------------------------------------------------------------------------
# Golden files
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--golden-update",
        action="store_true",
        help="rewrite the golden files instead of comparing against them",
    )


@pytest.fixture
def golden(request):
    """Compare text against tests/golden/<name>, or rewrite it.

    A golden file is the point of the characterisation tests: it pins today's
    output byte for byte, so a refactor that changes a published post or a
    published map fails loudly instead of quietly.
    """
    update = request.config.getoption("--golden-update")

    def check(name: str, actual: str) -> None:
        path = GOLDEN_DIR / name
        if update or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(actual)
            if not update:
                pytest.fail(
                    f"golden file {name} did not exist; wrote it. "
                    "Check the contents, then re-run."
                )
            return
        expected = path.read_text()
        assert actual == expected, (
            f"{name} changed. If the change is wanted, re-run with "
            f"--golden-update and review the diff."
        )

    return check


# ---------------------------------------------------------------------------
# Garmin payloads
# ---------------------------------------------------------------------------

@pytest.fixture
def activity():
    """A factory for a realistic activity-list entry.

    The shape follows a real ``get_activities_by_date`` item, with only the
    keys the importer reads. Values are invented: no real trace, no real time.
    """
    def make(**overrides):
        base = {
            "activityId": 24048177886,
            "activityName": "Toronto - 4x1600",
            "description": "Four by a mile, with the last one honest.",
            "startTimeLocal": "2026-08-20 07:12:31",
            "startTimeGMT": "2026-08-20 11:12:31",
            "distance": 12220.0,
            "duration": 3602.0,
            "elevationGain": 51.0,
            "privacy": {"typeKey": "groups"},
            "hrTimeInZone_1": 300.0,
            "hrTimeInZone_2": 900.0,
            "hrTimeInZone_3": 1500.0,
            "hrTimeInZone_4": 800.0,
            "hrTimeInZone_5": 100.0,
        }
        base.update(overrides)
        return base

    return make


@pytest.fixture
def fake_client():
    """A stand-in for a garminconnect Garmin, serving canned payloads.

    Records what was asked for, so a test can assert on the call count - which
    is the only way to check "used the cache, made no request".
    """
    class FakeClient:
        def __init__(self):
            self.activities: list[dict] = []
            self.details: dict[int, dict] = {}
            self.full: dict[int, dict] = {}
            self.calls: list[tuple] = []
            self.fail_with: Exception | None = None

        def get_activities_by_date(self, start, end, kind):
            self.calls.append(("list", start, end, kind))
            if self.fail_with:
                raise self.fail_with
            return list(self.activities)

        def get_activity_details(self, activity_id, **kwargs):
            self.calls.append(("details", activity_id))
            return self.details.get(int(activity_id), {})

        def get_activity(self, activity_id):
            self.calls.append(("activity", activity_id))
            return self.full.get(int(activity_id), {})

    return FakeClient()


@pytest.fixture
def no_sleep(monkeypatch):
    """Make every pause instant.

    The retry and backoff paths really sleep for tens of seconds otherwise,
    which is why they had no tests before.
    """
    from garminrun import garmin_client, overpass, photos

    for module in (overpass, photos, garmin_client):
        monkeypatch.setattr(module, "_sleep", lambda seconds: None)
