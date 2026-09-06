# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest",
#   # The same pins as import_garmin_runs.py. The tests import the importer, so
#   # they need its runtime dependencies too. Keep these two lines in step with
#   # that file's header; tests/test_deps.py fails if they drift.
#   "garminconnect==0.3.2",
#   "python-dotenv",
# ]
# ///

"""Run the importer's tests.

    uv run scripts/garmin/run_tests.py
    uv run scripts/garmin/run_tests.py -k trim -x
    uv run scripts/garmin/run_tests.py --golden-update

Arguments are passed straight through to pytest. Nothing here touches the
network, Garmin, or the repo: every test works in a temporary directory.
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent

if __name__ == "__main__":
    sys.exit(pytest.main([str(HERE / "tests"), "-q", *sys.argv[1:]]))
