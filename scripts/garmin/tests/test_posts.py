"""Reading things back out of an already-published post."""

from __future__ import annotations

import textwrap


def _post(tmp_path, body: str):
    path = tmp_path / "index.md"
    path.write_text(textwrap.dedent(body).lstrip())
    return path


def test_distance_label_comes_from_the_post(importer, tmp_path):
    """--backfill-maps has no activity payload, so it reads the post's own number.

    Taking it from the front matter is what makes a forced redraw a no-op: it
    is the same value run_import rounded and wrote in the first place.
    """
    post = _post(tmp_path, """
        ---
        title: "Toronto - 4x1600"
        extra:
          distance_km: 12.22
          duration: "1:00:02"
        ---
        Four by a mile.
        """)
    assert importer.post_distance_label(post) == "12.22 km"


def test_distance_label_is_empty_when_there_is_nothing_to_read(importer, tmp_path):
    """No post, or a post without the key, means an unlabelled map - not a crash."""
    assert importer.post_distance_label(None) == ""
    assert importer.post_distance_label(_post(tmp_path, """
        ---
        title: "A run from before the importer"
        ---
        Written by hand.
        """)) == ""


def test_distance_label_ignores_a_lookalike_in_the_prose(importer, tmp_path):
    """The regex is anchored to a whole line, so prose cannot spoof it."""
    post = _post(tmp_path, """
        ---
        title: "Toronto - 4x1600"
        extra:
          distance_km: 12.22
        ---
        I thought about distance_km: 99.9 the whole way round.
        """)
    assert importer.post_distance_label(post) == "12.22 km"
