"""The OSM query, its cache, and what happens when an endpoint misbehaves.

None of this was testable before: the network was reached inline and the
retry paths really slept. overpass now has one hook per outside call, so these
tests run offline and instantly.
"""

from __future__ import annotations

import gzip
import json

import pytest

from garminrun import overpass
from garminrun.svg import ROAD_WIDTHS
from garminrun.synthetic import synthetic_points
from garminrun.track import prepare_track

# One way, enough to be a valid non-empty answer.
ANSWER = {"elements": [{"type": "way", "tags": {"highway": "primary"},
                        "geometry": [{"lat": 43.65, "lon": -79.38},
                                     {"lat": 43.66, "lon": -79.39}]}]}
EMPTY = {"elements": []}


@pytest.fixture(autouse=True)
def isolate(repo, no_sleep):
    """Every test gets its own cache directory and no accumulated penalty."""
    overpass.reset_penalty()
    yield
    overpass.reset_penalty()


@pytest.fixture
def track():
    return prepare_track(synthetic_points())


@pytest.fixture
def transport(monkeypatch):
    """Stand in for the network, recording every call."""
    class Transport:
        def __init__(self):
            self.calls: list[str] = []
            self.answers: dict[str, object] = {}
            self.default: object = ANSWER

        def __call__(self, url, query):
            self.calls.append(url)
            answer = self.answers.get(url, self.default)
            if isinstance(answer, Exception):
                raise answer
            return json.dumps(answer).encode()

    fake = Transport()
    monkeypatch.setattr(overpass, "_post", fake)
    monkeypatch.setattr(overpass, "_get", lambda url: "1 slots available now")
    return fake


# ---------------------------------------------------------------------------
# The query
# ---------------------------------------------------------------------------

def test_the_query_asks_for_every_road_class_that_gets_drawn():
    """A class in ROAD_WIDTHS but not in the query is a road drawn as nothing."""
    query = overpass._overpass_query(43.6, -79.4, 43.7, -79.3)
    for road in ROAD_WIDTHS:
        assert road in query, road


def test_the_query_carries_the_bounding_box():
    query = overpass._overpass_query(43.6, -79.4, 43.7, -79.3)
    assert "43.60000,-79.40000,43.70000,-79.30000" in query


def test_the_cache_key_follows_the_query_text():
    """Changing the tag filters or the box must miss the cache automatically."""
    one = overpass._cache_path(overpass._overpass_query(43.6, -79.4, 43.7, -79.3))
    same = overpass._cache_path(overpass._overpass_query(43.6, -79.4, 43.7, -79.3))
    other = overpass._cache_path(overpass._overpass_query(43.6, -79.4, 43.7, -79.2))
    assert one == same
    assert one != other


# ---------------------------------------------------------------------------
# The cache
# ---------------------------------------------------------------------------

def test_a_second_call_makes_no_request(track, transport):
    first = overpass.fetch_basemap(track)
    assert first == ANSWER
    assert len(transport.calls) == 1

    second = overpass.fetch_basemap(track)
    assert second == ANSWER
    assert len(transport.calls) == 1, "the cache was not used"


def test_refresh_ignores_the_cache(track, transport):
    overpass.fetch_basemap(track)
    overpass.fetch_basemap(track, use_cache=False)
    assert len(transport.calls) == 2


def test_an_unreadable_cache_file_is_ignored_not_fatal(track, transport, capsys):
    """A truncated .gz from a killed run must not stop the map."""
    query = overpass._overpass_query(*track.bounds())
    path = overpass._cache_path(query)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not gzip at all")

    assert overpass.fetch_basemap(track) == ANSWER
    assert len(transport.calls) == 1, "it should have gone to the network"


def test_a_cache_write_survives_a_read_back(track, transport):
    overpass.fetch_basemap(track)
    path = overpass._cache_path(overpass._overpass_query(*track.bounds()))
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        assert json.load(handle) == ANSWER


# ---------------------------------------------------------------------------
# Endpoints behaving badly
# ---------------------------------------------------------------------------

def test_an_empty_answer_is_a_failure_not_an_empty_basemap(track, transport):
    """overpass.osm.ch answers 200 with zero elements outside Switzerland.

    Caching that would poison the cache with a blank basemap, and the map would
    come out as a route floating on nothing. So zero elements must be treated
    as a failure and never written to the cache.
    """
    transport.default = EMPTY
    assert overpass.fetch_basemap(track) is None
    assert not overpass._cache_path(overpass._overpass_query(*track.bounds())).exists()


def test_it_moves_on_to_the_next_mirror(track, transport):
    transport.answers[overpass.OVERPASS_URLS[0]] = RuntimeError("503")
    assert overpass.fetch_basemap(track) == ANSWER
    assert transport.calls[0] == overpass.OVERPASS_URLS[0]
    assert transport.calls[-1] == overpass.OVERPASS_URLS[1]


def test_all_mirrors_down_gives_no_basemap_rather_than_an_exception(track, transport):
    """A missing background must never cost the post, or even the route."""
    transport.default = RuntimeError("everything is down")
    assert overpass.fetch_basemap(track) is None
    assert len(transport.calls) == len(overpass.OVERPASS_URLS) * overpass.OVERPASS_ATTEMPTS


def test_a_refusal_slows_the_later_queries_down(track, transport):
    """One rate limit must not strip the basemap from every remaining map."""
    transport.default = RuntimeError("429")
    overpass.fetch_basemap(track)
    assert overpass._penalty > 0


def test_the_penalty_can_be_reset(track, transport):
    transport.default = RuntimeError("429")
    overpass.fetch_basemap(track)
    overpass.reset_penalty()
    assert overpass._penalty == 0
