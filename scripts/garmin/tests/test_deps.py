"""The two PEP 723 headers must declare the same runtime pins.

run_tests.py has to install what the importer imports, so its dependency list
repeats the importer's. That duplication is the price of keeping the repo free
of packaging files; this test is what stops it drifting.
"""

from __future__ import annotations

import re
from pathlib import Path

GARMIN_DIR = Path(__file__).resolve().parent.parent

# Declared by run_tests.py only: the runner's own tool, not a runtime import.
RUNNER_ONLY = {"pytest"}


def _pep723_dependencies(path: Path) -> set[str]:
    """The `dependencies` list from a PEP 723 `# /// script` block."""
    text = path.read_text()
    block = re.search(r"^# /// script\n(.*?)^# ///$", text, re.MULTILINE | re.DOTALL)
    assert block, f"{path.name} has no PEP 723 script block"
    body = "\n".join(line.removeprefix("#").strip() for line in block.group(1).splitlines())
    listing = re.search(r"dependencies\s*=\s*\[(.*?)\]", body, re.DOTALL)
    assert listing, f"{path.name} declares no dependencies"
    return set(re.findall(r'"([^"]+)"', listing.group(1)))


def test_runner_installs_what_the_importer_needs():
    importer = _pep723_dependencies(GARMIN_DIR / "import_garmin_runs.py")
    runner = _pep723_dependencies(GARMIN_DIR / "run_tests.py")
    assert importer <= runner, (
        "run_tests.py is missing "
        f"{sorted(importer - runner)}; the tests import the importer, so they "
        "need its dependencies too"
    )
    assert runner - importer == RUNNER_ONLY, sorted(runner - importer)


def test_both_require_the_same_python():
    pattern = r'requires-python\s*=\s*"([^"]+)"'
    versions = {
        name: re.search(pattern, (GARMIN_DIR / name).read_text()).group(1)
        for name in ("import_garmin_runs.py", "run_tests.py")
    }
    assert len(set(versions.values())) == 1, versions
