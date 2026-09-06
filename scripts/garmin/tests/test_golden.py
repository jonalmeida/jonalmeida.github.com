"""Characterisation tests: pin today's published output, byte for byte.

These exist to make the module split safe. They say nothing about whether the
output is *right* - only that it does not change. Every one of them targets a
file that gets committed to a public repo and served to readers:

  - content/runs/<slug>/index.md   the post
  - static/runs/maps/<id>.svg      the route map
  - the --report JSON              read by run_import.sh with jq
  - the crontab line               copy-pasted by a human

If one of these fails during the refactor, the refactor changed behaviour.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest

GARMIN_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# The post
# ---------------------------------------------------------------------------

def test_post_bare(importer, activity, golden):
    """A post with no map and no photos."""
    golden("post-bare.md", importer.activity_to_markdown(activity()))


def test_post_full(importer, activity, golden):
    """A post with a route map and a photo gallery."""
    text = importer.activity_to_markdown(
        activity(), map_url="/runs/maps/24048177886.svg", photos=3
    )
    golden("post-full.md", text)


def test_post_sparse(importer, activity, golden):
    """A treadmill run: no distance, no elevation, no heart rate, no prose."""
    text = importer.activity_to_markdown(
        activity(
            activityName='He said "hello" \\ then left',
            description="",
            distance=0,
            duration=0,
            elevationGain=None,
            **{f"hrTimeInZone_{n}": 0.0 for n in range(1, 6)},
        )
    )
    golden("post-sparse.md", text)


def test_post_never_leaks_a_marker(importer, activity, golden):
    """--no-content-filter publishes a marked run. The marker must not ride along.

    This is the one characterisation test that is also a privacy assertion: the
    marker is the private signal, and a post is public forever once pushed.
    """
    text = importer.activity_to_markdown(
        activity(
            activityName="Toronto - 4x1600 #nopost",
            description="Four by a mile.\n\n#private   \n\nLast one honest.",
        )
    )
    for marker in importer.PRIVATE_MARKERS:
        assert marker not in text.lower(), marker
    golden("post-marked.md", text)


# ---------------------------------------------------------------------------
# The map
# ---------------------------------------------------------------------------

def test_sample_map(importer, golden):
    """The synthetic route, drawn without a basemap.

    No network: route_map_svg takes basemap data rather than fetching it, and
    None means "no basemap". Deterministic, so it can be a golden file.
    """
    svg = importer.route_map_svg(importer.synthetic_points(), label="10.1 km")
    assert svg is not None
    golden("sample-map.svg", svg)


def test_sample_map_is_well_formed_xml(importer):
    """A malformed SVG renders as nothing at all in a browser.

    The existing --selftest never checked this: it counted substrings.
    """
    svg = importer.route_map_svg(importer.synthetic_points(), label="10.1 km")
    root = ElementTree.fromstring(svg)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"


def test_trimmed_map_is_stable_per_activity(importer, golden):
    """The privacy trim is seeded from the activity id, so the map is stable.

    That property is what makes `--backfill-maps --force` a no-op diff, which
    is the strongest verification available for this refactor.
    """
    points, _ = importer.trim_route_ends(importer.synthetic_points(), 24048177886)
    svg = importer.route_map_svg(points, label="10.1 km")
    assert svg is not None
    golden("sample-map-trimmed.svg", svg)


# ---------------------------------------------------------------------------
# The wrapper contract
# ---------------------------------------------------------------------------

# Every `jq -r '<path>' "$REPORT"` in run_import.sh. A key renamed here breaks
# the scheduled job silently: jq prints `null` and the wrapper carries on.
WRAPPER = GARMIN_DIR / "run_import.sh"
REPORT_KEYS = ("imported_count", "imported", "filtered_count",
               "deferred_count", "retract_candidates")


def test_report_keys_match_the_wrapper():
    """Whatever run_import.sh reads with jq must be a key the importer writes."""
    jq_paths = re.findall(r"jq -r '\.([A-Za-z_]+)", WRAPPER.read_text())
    assert jq_paths, "found no jq reads in run_import.sh; the regex is stale"
    for key in jq_paths:
        assert key in REPORT_KEYS, f"run_import.sh reads .{key}, which is not a report key"


def test_report_shape(importer, repo, tmp_path, monkeypatch, capsys):
    """run_import with nothing to do still writes every key the wrapper reads."""
    monkeypatch.setattr(importer, "fetch_running_activities", lambda client: [])

    report = tmp_path / "report.json"
    # parse_args reads sys.argv directly today. Cutting that seam is a later
    # step; until then, patching argv is how a test reaches it.
    monkeypatch.setattr("sys.argv", ["import_garmin_runs.py", "--report", str(report)])
    args = importer.parse_args()

    importer.run_import(client=None, args=args)
    capsys.readouterr()

    data = json.loads(report.read_text())
    assert set(data) == set(REPORT_KEYS), sorted(data)
    assert data["imported_count"] == 0
    assert data["imported"] == []
    assert data["retract_candidates"] == []


# ---------------------------------------------------------------------------
# The crontab line
# ---------------------------------------------------------------------------

def test_print_crontab(importer, capsys):
    """A human copy-pastes this. It has to keep pointing at run_import.sh."""
    importer.print_crontab("8,20")
    out = capsys.readouterr().out
    assert out.startswith("# Garmin run importer:")
    assert f"40 8,20 * * * /bin/bash {WRAPPER.resolve()}" in out


def test_print_crontab_hours(importer, capsys):
    importer.print_crontab(" 6 , 18 ,")
    assert "40 6,18 * * *" in capsys.readouterr().out
