"""Shared fixtures for the Garmin importer tests.

Nothing here touches the network, Garmin, or the real repo. Every test that
writes runs inside pytest's ``tmp_path``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

GARMIN_DIR = Path(__file__).resolve().parent.parent
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


# ---------------------------------------------------------------------------
# The code under test
# ---------------------------------------------------------------------------

def _load_importer():
    """Import ``import_garmin_runs.py`` by path.

    The importer is a PEP 723 script, not an installed package, so there is no
    import path to it. Loading it by path is also what keeps this file working
    through the module split: only this function has to change.
    """
    path = GARMIN_DIR / "import_garmin_runs.py"
    spec = importlib.util.spec_from_file_location("import_garmin_runs", path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def importer():
    """The importer module. Session-scoped: loading it is not free."""
    return _load_importer()


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
