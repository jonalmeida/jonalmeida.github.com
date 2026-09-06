"""Downloading an activity's photos into its bundle.

The invariant that matters: an activity is either fully imported or not
imported at all. A post with half its photos would be recorded as done and the
missing photos lost for good, because an id in garmin_imported.json is never
looked at again.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from garminrun import photos
from garminrun.photos import PHOTO_MAX_PER_ACTIVITY, PhotoFailure, download_photos

HAS_RESIZER = bool(shutil.which("magick") or shutil.which("sips"))

# A real 1200x900 JPEG, so the resize path has something valid to chew on and
# somewhere to shrink to. Hand-built hex bytes are not enough: ImageMagick
# rejects them, and the test then silently exercises the fallback instead.
WIDE_JPEG = (Path(__file__).resolve().parent / "data" / "wide.jpg").read_bytes()


def images(count: int, **extra) -> list[dict]:
    return [
        {"url": f"https://s3.example/photo-{n}.jpg?sig=x",
         "imageId": f"id-{n}", **extra}
        for n in range(count)
    ]


@pytest.fixture
def fetcher(monkeypatch):
    """Stand in for the S3 GET, recording every URL asked for."""
    class Fetcher:
        def __init__(self):
            self.urls: list[str] = []
            self.raise_on: set[str] = set()

        def __call__(self, url):
            self.urls.append(url)
            if any(marker in url for marker in self.raise_on):
                raise RuntimeError("S3 said no")
            return WIDE_JPEG

    fake = Fetcher()
    monkeypatch.setattr(photos, "_fetch", fake)
    return fake


@pytest.fixture
def bundle(repo):
    path = repo.content_runs / "2026-09-06-run-2026-09-06"
    path.mkdir(parents=True)
    return path


# ---------------------------------------------------------------------------
# Naming and layout
# ---------------------------------------------------------------------------

def test_photos_are_named_after_the_date_and_their_order(
    bundle, fetcher, fake_client, no_sleep, capsys
):
    names = download_photos(fake_client, 1, images(3), bundle, "2026-09-06")
    assert names == ["2026-09-06-0.jpg", "2026-09-06-1.jpg", "2026-09-06-2.jpg"]
    for name in names:
        assert (bundle / name).is_file()


def test_a_retry_does_not_leave_a_photo_garmin_has_since_lost(
    bundle, fetcher, fake_client, no_sleep, capsys
):
    """Names repeat, so an overwrite is not enough: the extra file would linger
    and the gallery would publish a photo the activity no longer has."""
    (bundle / "2026-09-06-0.jpg").write_bytes(b"old")
    (bundle / "2026-09-06-1.jpg").write_bytes(b"stale")

    names = download_photos(fake_client, 1, images(1), bundle, "2026-09-06")
    assert names == ["2026-09-06-0.jpg"]
    assert not (bundle / "2026-09-06-1.jpg").exists(), "the stale photo survived"


def test_no_more_than_the_cap(bundle, fetcher, fake_client, no_sleep, capsys):
    """Every photo is a git blob forever."""
    names = download_photos(
        fake_client, 1, images(PHOTO_MAX_PER_ACTIVITY + 5), bundle, "2026-09-06"
    )
    assert len(names) == PHOTO_MAX_PER_ACTIVITY


def test_the_chosen_variant_is_the_one_fetched(
    bundle, fetcher, fake_client, no_sleep, capsys
):
    listing = [{"url": "https://s3.example/big.jpg", "smallUrl": "https://s3.example/small.jpg"}]
    download_photos(fake_client, 1, listing, bundle, "2026-09-06", variant="smallUrl")
    assert fetcher.urls == ["https://s3.example/small.jpg"]


# ---------------------------------------------------------------------------
# Failure
# ---------------------------------------------------------------------------

def test_a_failed_download_raises_so_the_activity_is_not_recorded(
    bundle, fetcher, fake_client, no_sleep, capsys
):
    fetcher.raise_on = {"photo-1"}
    with pytest.raises(PhotoFailure):
        download_photos(fake_client, 1, images(3), bundle, "2026-09-06")


def test_a_near_expired_url_is_relisted(bundle, fetcher, fake_client, no_sleep, capsys):
    """The presigned URLs live 24 h. A caller that cached the DTO would get 403s."""
    stale = images(1)
    stale[0]["expirationTimestamp"] = (time.time() - 10) * 1000
    fake_client.full[1] = {
        "metadataDTO": {"activityImages": [
            {"url": "https://s3.example/fresh.jpg?sig=new", "imageId": "id-0"}
        ]}
    }
    download_photos(fake_client, 1, stale, bundle, "2026-09-06")
    assert ("activity", 1) in fake_client.calls, "it did not re-list"
    assert fetcher.urls == ["https://s3.example/fresh.jpg?sig=new"]


# ---------------------------------------------------------------------------
# Resizing
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_RESIZER, reason="neither magick nor sips is on PATH")
def test_shrink_narrows_the_photo_and_leaves_no_scratch(bundle):
    destination = bundle / "out.jpg"
    assert photos._shrink(WIDE_JPEG, destination, 800)
    assert destination.is_file()
    assert destination.stat().st_size < len(WIDE_JPEG), "it did not get smaller"
    assert not list(bundle.glob("*.tmp")), "the scratch file was left behind"


@pytest.mark.skipif(not HAS_RESIZER, reason="neither magick nor sips is on PATH")
def test_a_downloaded_photo_really_gets_resized(
    bundle, fetcher, fake_client, no_sleep, capsys
):
    """The default path, not the no-resizer fallback."""
    download_photos(fake_client, 1, images(1), bundle, "2026-09-06", width=800)
    assert (bundle / "2026-09-06-0.jpg").stat().st_size < len(WIDE_JPEG)


def test_width_zero_commits_the_bytes_as_they_are(
    bundle, fetcher, fake_client, no_sleep, capsys
):
    """--no-photo-resize sets the width to 0."""
    download_photos(fake_client, 1, images(1), bundle, "2026-09-06", width=0)
    assert (bundle / "2026-09-06-0.jpg").read_bytes() == WIDE_JPEG
