# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "garminconnect==0.3.2",
#   "python-dotenv",
# ]
# ///

"""Import Garmin running activities to Zola markdown files.

Usage:
    uv run scripts/garmin/import_garmin_runs.py                    # new runs + maps + photos
    uv run scripts/garmin/import_garmin_runs.py --no-maps          # skip route maps
    uv run scripts/garmin/import_garmin_runs.py --no-photos        # skip photos
    uv run scripts/garmin/import_garmin_runs.py --backfill-maps    # maps for imported runs
    uv run scripts/garmin/import_garmin_runs.py --backfill-photos  # photos for imported runs
    uv run scripts/garmin/import_garmin_runs.py --print-crontab    # emit a crontab entry
    uv run scripts/garmin/import_garmin_runs.py --sample-map       # no credentials needed

Credentials: set GARMIN_EMAIL and GARMIN_PASSWORD in environment or
scripts/garmin/.env. On first run, Garmin MFA will prompt interactively;
subsequent runs use the cached tokens in scripts/garmin/.garmin_tokens/.

Key behaviours:
  - First run prompts for MFA interactively; later runs use the cached tokens.
    With --non-interactive, or when stdin is not a terminal, a missing or
    rejected token exits 2 instead of prompting.
  - Fetches all running activities since 2026-03-07 via get_activities_by_date
  - Skips IDs in garmin_ignore.txt or already in garmin_imported.json
  - Skips runs whose Garmin name or description carries #nopost, and runs with
    no description at all. A skipped ID is appended to garmin_ignore.txt as a
    bare number; the reason is printed, never written to that tracked file.
  - Writes content/runs/YYYY-MM-DD-run-YYYY-MM-DD/index.md, a Zola page bundle
    (or -2, -3 for several runs on the same day)
  - Downloads the activity's photos into that bundle as YYYY-MM-DD-N.jpg,
    resized to 800 px, and puts a gallery line in the post. This costs one
    extra get_activity call per imported activity.
  - Writes static/runs/maps/<activity_id>.svg: the GPS route, coloured by speed,
    over an OpenStreetMap basemap. This costs one get_activity_details call and
    one Overpass query per imported activity.
  - Cuts a random 400-800 m off each end of the route, so the real start and
    finish never reach the file. Use --no-privacy-trim to keep the whole track.
  - Saves imported IDs back to garmin_imported.json once the run finishes. An
    ID in that file means fully done and is never revisited, so an activity
    that fails part way through is left out and redone from scratch next time.
"""

from garminrun.cli import main

if __name__ == "__main__":
    main()
