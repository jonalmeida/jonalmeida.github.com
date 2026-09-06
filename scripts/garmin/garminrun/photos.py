"""Downloading an activity's photos into its page bundle, and shrinking them.

Garmin returns photos on the full activity DTO as presigned S3 URLs with no
auth header and a 24 h life. There is no per-photo state: an activity is either
fully imported or not imported at all, so every failure here raises and the
caller skips the activity without recording it. A post with half its photos is
worse than a post that arrives a few hours late.
"""

from __future__ import annotations

import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from garminconnect import Garmin


PHOTO_MAX_PER_ACTIVITY = 12


PHOTO_TIMEOUT_S = 60


# Photos are plain git blobs forever, and gallery.html links the committed file
# as the full-size image, so this width is what a reader actually gets. 800 px
# matches every photo added to content/runs by hand.
PHOTO_TARGET_WIDTH = 800


PHOTO_QUALITY = 82


PHOTO_WARN_BYTES = 1_000_000


class PhotoFailure(Exception):
    """Garmin has photos for this activity but we could not get them."""


def fetch_activity_photos(client: Garmin, activity_id: int) -> list[dict]:
    """Return metadataDTO.activityImages for an activity.

    garminconnect 0.3.2 has no photo helper; the images ride along on the full
    activity DTO, so this costs one extra get_activity call.

    An empty list and a failed call are very different here, and both look like
    "no photos" if you are careless. An activity id in garmin_imported.json is
    never looked at again, so swallowing a failure would publish a photoless
    post and lose those photos for good. Hence: [] means the run really has no
    photos, and anything else raises so the caller can skip the activity
    without recording it.
    """
    for attempt in (1, 2):
        try:
            full = client.get_activity(activity_id)
            break
        except Exception as exc:  # noqa: BLE001
            if attempt == 1:
                print(f"  photo list failed for {activity_id} ({exc}); retrying")
                _sleep(5)
            else:
                raise PhotoFailure(f"photo list failed for {activity_id}: {exc}") from exc

    images = ((full or {}).get("metadataDTO") or {}).get("activityImages") or []
    return [i for i in images if isinstance(i, dict) and i.get("url")]


def _fetch(url: str) -> bytes:
    """GET a presigned S3 URL. The one place this module reaches the network.

    No auth header: the signature is in the query string. A test replaces this.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": "jonalmeida.com run importer"}
    )
    with urllib.request.urlopen(request, timeout=PHOTO_TIMEOUT_S) as response:
        return response.read()


_sleep = time.sleep


def _http_get(url: str) -> bytes:
    """Fetch a presigned S3 URL.

    No auth header: the signature is in the query string. client.download()
    cannot be used, because garminconnect prefixes every path with the
    connectapi base URL and so cannot reach S3 at all.
    """
    for attempt in (1, 2):
        try:
            return _fetch(url)
        except Exception as exc:  # noqa: BLE001
            if attempt == 1:
                print(f"  photo download failed ({exc}); retrying")
                _sleep(5)
            else:
                raise PhotoFailure(f"photo download failed: {exc}") from exc
    raise PhotoFailure("unreachable")


def _shrink(data: bytes, destination: Path, width: int) -> bool:
    """Write data to destination, shrunk to `width` px. False if we could not.

    ImageMagick first, then sips, which ships with macOS so the resize needs no
    bootstrapping. '800x>' only ever shrinks, so a photo already narrower than
    the target is left alone. -strip drops metadata; Garmin already strips EXIF,
    this is belt and braces.
    """
    scratch = destination.with_suffix(".orig.tmp")
    scratch.write_bytes(data)
    try:
        if shutil.which("magick"):
            # 'magick', not 'magick convert': IMv7 deprecated the latter.
            command = [
                "magick", str(scratch), "-auto-orient", "-resize", f"{width}x>",
                "-strip", "-quality", str(PHOTO_QUALITY), str(destination),
            ]
        elif shutil.which("sips"):
            command = [
                "sips", "--resampleWidth", str(width), str(scratch),
                "--out", str(destination),
            ]
        else:
            print("  WARNING: neither magick nor sips found; cannot resize")
            return False

        subprocess.run(command, check=True, capture_output=True, timeout=180)
        return destination.exists() and destination.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: resize failed ({exc})")
        return False
    finally:
        scratch.unlink(missing_ok=True)


def download_photos(
    client: Garmin,
    activity_id: int,
    images: list[dict],
    bundle: Path,
    date_str: str,
    variant: str = "url",
    width: int = PHOTO_TARGET_WIDTH,
) -> list[str]:
    """Download an activity's photos into its bundle as <date_str>-<n>.jpg.

    There is no per-photo state: an activity is either fully imported or not
    imported at all, so this always fetches every photo and overwrites. Any
    failure raises, and the caller then skips the activity without recording
    it - a post with half its photos is worse than a post that arrives a
    few hours late.
    """
    bundle.mkdir(parents=True, exist_ok=True)

    # A retry writes the same names in the same order, but if Garmin has since
    # lost a photo the old file would linger and the gallery would publish it.
    for stale in bundle.glob("*.jpg"):
        stale.unlink()

    saved: list[str] = []
    for n, image in enumerate(images[:PHOTO_MAX_PER_ACTIVITY]):
        url = image.get(variant) or image["url"]

        # The URLs are presigned with a 24 h life. We use them seconds after
        # get_activity returned, so this only bites a caller that cached the
        # DTO - cheap enough to guard anyway.
        expires = image.get("expirationTimestamp")
        if expires and expires / 1000 < time.time() + 60:
            print(f"  photo URL for {activity_id} has expired; re-listing")
            fresh = fetch_activity_photos(client, activity_id)
            match = next(
                (f for f in fresh if f.get("imageId") == image.get("imageId")), None
            )
            if match:
                url = match.get(variant) or match["url"]

        data = _http_get(url)
        name = f"{date_str}-{n}.jpg"
        destination = bundle / name

        if width and _shrink(data, destination, width):
            pass
        elif width:
            # No resizer. Take Garmin's medium variant rather than commit a
            # half-megabyte original.
            small = image.get("smallUrl") or image.get("mediumUrl")
            if small and small != url:
                print("  falling back to Garmin's medium variant")
                data = _http_get(small)
            destination.write_bytes(data)
        else:
            destination.write_bytes(data)

        size = destination.stat().st_size
        print(f"  Wrote photo {name} ({size / 1024:.0f} KB)")
        if size > PHOTO_WARN_BYTES:
            print(
                f"  WARNING: {name} is {size / 1024:.0f} KB "
                "and goes into git history for good"
            )
        saved.append(name)

    return saved
