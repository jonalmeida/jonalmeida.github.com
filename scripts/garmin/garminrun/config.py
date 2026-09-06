"""Where everything lives, and the constants more than one module needs.

Paths are reached through ``PATHS`` rather than as module constants, and read
at call time rather than bound at import. That is what lets a test point the
importer at a temporary tree with one ``monkeypatch.setattr``:

    monkeypatch.setattr(config, "PATHS", config.paths_for(tmp_path))

Import this module, not its names: ``config.PATHS.maps`` sees a patched value,
``from garminrun.config import PATHS`` does not.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

# resolve(): the importer is reached by several paths - `uv run` with an
# absolute path, a relative path from the repo root, and an sys.path entry
# in the tests. Only an absolute anchor gives the same answer to all three.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = SCRIPTS_DIR.parent.parent

START_DATE = "2026-03-07"

# Where a map lands, and the URL it is served from. Both sides of the same
# fact, needed by modules that never see each other: maps writes the file,
# postfmt and posts write the link.
MAP_URL_PREFIX = "/runs/maps"
MAP_EMBED_WIDTH = 640

# Exit code the wrapper looks for: Garmin wants a person at a keyboard.
EXIT_NEEDS_LOGIN = 2


class Paths(NamedTuple):
    """Every path the importer reads or writes."""

    scripts: Path
    repo: Path
    content_runs: Path
    maps: Path
    imported: Path
    ignore: Path
    tokenstore: Path
    overpass_cache: Path


def paths_for(scripts_dir: Path, repo_dir: Path | None = None) -> Paths:
    """The path set anchored at a scripts/garmin directory.

    ``repo_dir`` defaults to two levels up, which is true for the real layout.
    A test passes both so that content/ and static/ land inside its tmp_path
    rather than two levels above it.
    """
    repo = repo_dir if repo_dir is not None else scripts_dir.parent.parent
    return Paths(
        scripts=scripts_dir,
        repo=repo,
        content_runs=repo / "content" / "runs",
        maps=repo / "static" / "runs" / "maps",
        imported=scripts_dir / "garmin_imported.json",
        ignore=scripts_dir / "garmin_ignore.txt",
        tokenstore=scripts_dir / ".garmin_tokens",
        overpass_cache=scripts_dir / ".overpass_cache",
    )


PATHS = paths_for(SCRIPTS_DIR, REPO_DIR)
