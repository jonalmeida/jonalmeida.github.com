"""The two files the importer uses as its memory.

garmin_imported.json means "fully done, never look at this again".
garmin_ignore.txt means "never publish this", and is tracked and public.
"""

from __future__ import annotations

import json

from garminrun import config


def load_ignore_set() -> set[int]:
    if not config.PATHS.ignore.exists():
        return set()
    ids: set[int] = set()
    for line in config.PATHS.ignore.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.add(int(line))
    return ids


def append_ignore(activity_id: int) -> None:
    """Record an activity in garmin_ignore.txt so it is never reconsidered.

    The id alone, with no reason beside it. This file is tracked and published
    in a public repo, so a trailing "# marker #nopost" would leak exactly the
    thing the marker was meant to hide. The reason goes to stdout, which ends
    up in the untracked run log.
    """
    if activity_id in load_ignore_set():
        return
    text = config.PATHS.ignore.read_text() if config.PATHS.ignore.exists() else ""
    config.PATHS.ignore.write_text(text.rstrip("\n") + f"\n{activity_id}\n")


def load_imported_set() -> set[int]:
    if not config.PATHS.imported.exists():
        return set()
    data = json.loads(config.PATHS.imported.read_text())
    return set(data.get("imported", []))


def save_imported_set(imported: set[int]) -> None:
    config.PATHS.imported.write_text(
        json.dumps({"imported": sorted(imported)}, indent=2) + "\n"
    )
