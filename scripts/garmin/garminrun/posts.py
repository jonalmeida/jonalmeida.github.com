"""Where a post goes, how to find it again, and how to edit it in place.

The in-place edits are insert-only and idempotent by design. A post carries
hand-written prose and photos, so nothing here ever rewrites a line: it only
inserts a block, or flips one field.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from garminrun import config
from garminrun.config import MAP_URL_PREFIX
from garminrun.postfmt import GALLERY_SHORTCODE
from garminrun.state import append_ignore


def slug_for(activity: dict, date_str: str, same_day: list[dict]) -> str:
    """Return the directory name for an activity. The Nth run of a date always
    gets the same answer.

    The index comes from the activity's position among that date's activities,
    not from what is already on disk. An import that died halfway through wrote
    files but recorded nothing, so the next run has to land on the same slug
    and overwrite it - probing the filesystem would find the partial directory
    and create a -2 sibling beside it instead.
    """
    base = f"{date_str}-run-{date_str}"
    n = [a["activityId"] for a in same_day].index(activity["activityId"])
    return base if n == 0 else f"{base}-{n + 1}"


def output_path(slug: str) -> Path:
    """Return the index.md of the page bundle for a slug.

    Every new post is a page bundle, so a photo uploaded to Garmin after the
    import can be dropped in beside index.md without renaming anything.

    Creates nothing: a path getter that makes directories cannot be called to
    ask a question. The callers that write already mkdir the bundle.
    """
    return config.PATHS.content_runs / slug / "index.md"


ACTIVITY_ID_RE = re.compile(r"^\s*garmin_activity_id:\s*(\d+)\s*$", re.MULTILINE)


def index_posts_by_activity_id() -> dict[int, Path]:
    """Map each post's garmin_activity_id to its path."""
    index: dict[int, Path] = {}
    # Flat posts and page bundles both exist. _index.md carries no activity id,
    # so ACTIVITY_ID_RE filters it out.
    candidates = [*config.PATHS.content_runs.glob("*.md"), *config.PATHS.content_runs.glob("*/index.md")]
    for path in sorted(candidates):
        match = ACTIVITY_ID_RE.search(path.read_text())
        if match:
            index[int(match.group(1))] = path
    return index


DISTANCE_KM_RE = re.compile(r"^\s*distance_km:\s*([\d.]+)\s*$", re.MULTILINE)


def post_distance_label(post: Path | None) -> str:
    """The '12.22 km' label for a post, read from its own front matter.

    --backfill-maps has no activity payload to take the distance from, and
    fetching one per activity would cost an API call for a number the post
    already carries. Reading it back gives the same bytes run_import wrote,
    which is what keeps a forced redraw a no-op.
    """
    if post is None:
        return ""
    match = DISTANCE_KM_RE.search(post.read_text())
    return f"{match.group(1)} km" if match else ""


def insert_route_shortcode(path: Path, shortcode: str) -> bool:
    """Insert a '## Route' block into an existing post. Insert only, idempotent.

    Returns True when the file changed. Posts carry hand-written prose and
    photos, so this never rewrites a line - it only inserts a block, before the
    '## Heart Rate Zones' heading when there is one, or at the end.
    """
    text = path.read_text()
    if MAP_URL_PREFIX in text:
        return False

    block = f"## Route\n\n{shortcode}\n\n"
    anchor = "## Heart Rate Zones"
    at = text.find(anchor)
    if at == -1:
        path.write_text(text.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n")
    else:
        path.write_text(text[:at] + block + text[at:])
    return True


def insert_gallery_shortcode(path: Path) -> bool:
    """Insert the gallery line into an existing post. Insert only, idempotent.

    Returns True when the file changed. Same contract as
    insert_route_shortcode: never rewrite a line, only insert a block. The
    seam is the blank line before the stats table, which is where every
    hand-made post put it.
    """
    text = path.read_text()
    if "<gallery" in text:
        return False

    for anchor in ("\n| Stat | Value |", "\n## Route", "\n## Heart Rate Zones"):
        at = text.find(anchor)
        if at != -1:
            path.write_text(text[:at] + "\n" + GALLERY_SHORTCODE + "\n" + text[at:])
            return True

    path.write_text(text.rstrip("\n") + "\n\n" + GALLERY_SHORTCODE + "\n")
    return True


def post_dir(post: Path) -> Path | None:
    """The bundle directory for a post, or None when the post is a flat .md."""
    return post.parent if post.name == "index.md" else None


def retract_post(post: Path, activity_id: int, mode: str) -> bool:
    """Take a published post back down. Returns True when the file changed.

    'draft' flips draft: false -> true, which Zola excludes from the build
    while leaving the file, the photos and the history in place - the
    recoverable option. 'delete' removes the post and its map.
    """
    if mode == "draft":
        text = post.read_text()
        if "\ndraft: true\n" in text:
            return False
        post.write_text(text.replace("\ndraft: false\n", "\ndraft: true\n", 1))
        print(f"  retracted {activity_id}: {post.parent.name}/{post.name} is now a draft")
        return True

    bundle = post_dir(post)
    if bundle is not None:
        shutil.rmtree(bundle)
    else:
        post.unlink()
    (config.PATHS.maps / f"{activity_id}.svg").unlink(missing_ok=True)
    append_ignore(activity_id)
    print(f"  retracted {activity_id}: deleted the post and its map")
    return True
