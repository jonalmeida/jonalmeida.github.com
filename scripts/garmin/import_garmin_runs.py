# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "garminconnect==0.3.2",
#   "python-dotenv",
# ]
# ///

"""Import Garmin running activities to Zola markdown files.

Usage:
    uv run scripts/garmin/import_garmin_runs.py

Credentials: set GARMIN_EMAIL and GARMIN_PASSWORD in environment or
scripts/.env. On first run, Garmin MFA will prompt interactively; subsequent
runs use the cached session in ~/.garth/.

Key behaviours:
  - First run prompts for MFA interactively; subsequent runs use the cached ~/.garth/ session
  - Fetches all running activities since 2026-03-07 via get_activities_by_date
  - Skips IDs in garmin_ignore.txt or already in garmin_imported.json
  - Writes content/runs/YYYY-MM-DD-run.md (or -2, -3 for multiple runs on the same day)
  - Saves imported IDs back to garmin_imported.json after each run
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin

SCRIPTS_DIR = Path(__file__).parent
CONTENT_RUNS_DIR = SCRIPTS_DIR.parent.parent / "content" / "runs"
IMPORTED_FILE = SCRIPTS_DIR / "garmin_imported.json"
IGNORE_FILE = SCRIPTS_DIR / "garmin_ignore.txt"
TOKENSTORE = str(SCRIPTS_DIR / ".garmin_tokens")
START_DATE = "2026-03-07"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_ignore_set() -> set[int]:
    if not IGNORE_FILE.exists():
        return set()
    ids: set[int] = set()
    for line in IGNORE_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.add(int(line))
    return ids


def load_imported_set() -> set[int]:
    if not IMPORTED_FILE.exists():
        return set()
    data = json.loads(IMPORTED_FILE.read_text())
    return set(data.get("imported", []))


def save_imported_set(imported: set[int]) -> None:
    IMPORTED_FILE.write_text(
        json.dumps({"imported": sorted(imported)}, indent=2) + "\n"
    )


def format_duration(seconds: float) -> str:
    """Return MM:SS or H:MM:SS string."""
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_pace(seconds_per_km: float) -> str:
    """Return M:SS string for pace."""
    total = int(round(seconds_per_km))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


ZONE_NAMES = {1: "Warm Up", 2: "Easy", 3: "Aerobic", 4: "Threshold", 5: "Maximum"}


def hr_zones_mermaid(activity: dict) -> str:
    """Return a mermaid xychart shortcode for time in HR zones, or empty string."""
    # Collect all hrTimeInZone_N keys (e.g. hrTimeInZone_1 … hrTimeInZone_5)
    zone_data: list[tuple[int, int]] = []
    for key, value in activity.items():
        if key.startswith("hrTimeInZone_"):
            suffix = key[len("hrTimeInZone_"):]
            if suffix.isdigit():
                zone_data.append((int(suffix), int(value or 0)))

    if not zone_data:
        return ""

    # Display zone 5 → 1 (top to bottom, matching Garmin UI)
    zone_data.sort(key=lambda x: -x[0])

    total = sum(s for _, s in zone_data) or 1
    n = len(zone_data)
    labels = ", ".join(f'"Zone {z} {ZONE_NAMES.get(z, "")}"' for z, _ in zone_data)

    # One bar series per zone so each picks up its own palette color from the
    # plotColorPalette defined in mermaid.html (gray, orange, green, blue, lightgray).
    bar_lines = []
    for i, (_, secs) in enumerate(zone_data):
        values = ["0.0"] * n
        values[i] = f"{secs / total * 100:.1f}"
        bar_lines.append(f"    bar [{', '.join(values)}]")

    lines = [
        "{% mermaid() %}",
        """---
config:
  themeVariables:
    xyChart:
      plotColorPalette: "#555555,#FF8200,#56CC3C,#4090D4,#AAAAAA"
      backgroundColor: "transparent"
---
        """,
        "xychart horizontal",
        '    title "Time in Heart Rate Zones (%)"',
        f"    x-axis [{labels}]",
        # Start at 2 because of a weird mermaid rendering issue that shows
        # a bar even for zero values.
        '    y-axis "%" 2 --> 100', 
        *bar_lines,
        "{% end %}",
    ]
    return "\n".join(lines)


def activity_to_markdown(activity: dict) -> str:
    distance_m: float = activity.get("distance", 0) or 0
    distance_km = round(distance_m / 1000, 2)

    duration_s: float = activity.get("duration", 0) or 0
    duration_str = format_duration(duration_s)

    pace_str = "N/A"
    if distance_km > 0 and duration_s > 0:
        pace_s = duration_s / distance_km
        pace_str = format_pace(pace_s)

    elevation_gain = activity.get("elevationGain") or activity.get("gainElevation")
    elevation_str = str(int(elevation_gain)) if elevation_gain else "N/A"

    activity_id = activity["activityId"]

    # Parse start time to get date
    start_local = activity.get("startTimeLocal") or activity.get("startTimeGMT", "")
    date_str = start_local[:10] if start_local else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    run_date = datetime.strptime(date_str, "%Y-%m-%d")
    activity_name = activity["activityName"]

    # Alternative title. Example: "8 March, 2026: Toronto - Easy Run"
    #title = f"{run_date.day} {run_date.strftime('%B')}, {run_date.year}: {activity_name}"
    title = f"{activity_name}"

    frontmatter = f"""---
title: "{title}"
date: {date_str}
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: {activity_id}
  distance_km: {distance_km}
  duration: "{duration_str}"
  pace_per_km: "{pace_str}"
  elevation_gain_m: {elevation_str}
---"""

    table = f"""
| Stat | Value |
|------|-------|
| Distance | {distance_km} km |
| Duration | {duration_str} |
| Pace | {pace_str} /km |
| Elevation Gain | {elevation_str} m |
"""
    description = activity["description"]
    mermaid_chart = hr_zones_mermaid(activity)
    chart_section = f"\n## Heart Rate Zones\n\n{mermaid_chart}\n" if mermaid_chart else ""

    return frontmatter + "\n" + description + "\n" + table + chart_section


def output_path(date_str: str) -> Path:
    """Return a unique path for the given date, appending -2, -3, etc. if needed."""
    CONTENT_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    base = CONTENT_RUNS_DIR / f"{date_str}-run-{date_str}.md"
    if not base.exists():
        return base
    n = 2
    while True:
        candidate = CONTENT_RUNS_DIR / f"{date_str}-run-{date_str}-{n}.md"
        if not candidate.exists():
            return candidate
        n += 1


# ---------------------------------------------------------------------------
# Garmin fetch
# ---------------------------------------------------------------------------

def fetch_running_activities(client: Garmin) -> list[dict]:
    """Fetch all running activities on or after START_DATE, oldest first."""
    all_activities: list[dict] = []
    limit = 100
    start = 0
    while True:
        batch = client.get_activities_by_date(
            START_DATE,
            None,
            "running",
        )
        # get_activities_by_date returns all at once (no pagination needed for
        # most users); fall back to paginated get_activities if needed.
        all_activities = batch
        break

    # Sort oldest first
    all_activities.sort(key=lambda a: a.get("startTimeLocal") or a.get("startTimeGMT") or "")
    return all_activities


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Load credentials
    load_dotenv(SCRIPTS_DIR / ".env")
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    if not email or not password:
        raise SystemExit(
            "GARMIN_EMAIL and GARMIN_PASSWORD must be set in environment or scripts/.env"
        )

    ignore_set = load_ignore_set()
    imported_set = load_imported_set()

    print(f"Loaded {len(ignore_set)} ignored IDs, {len(imported_set)} already-imported IDs.")

    # Authenticate
    client = Garmin(email, password)
    tokenstore_path = Path(TOKENSTORE)
    if (tokenstore_path / "garmin_tokens.json").exists():
        client.client.load(TOKENSTORE)
    else:
        client.client.login(email, password, prompt_mfa=lambda: input("Enter MFA code: "))
        tokenstore_path.mkdir(parents=True, exist_ok=True)
        client.client.dump(TOKENSTORE)
    print("Authenticated with Garmin Connect.")

    activities = fetch_running_activities(client)
    print(f"Fetched {len(activities)} running activities since {START_DATE}.")

    count_imported = 0
    count_ignored = 0
    count_already = 0

    for activity in activities:
        activity_id = int(activity["activityId"])

        if activity_id in ignore_set:
            count_ignored += 1
            continue

        if activity_id in imported_set:
            count_already += 1
            continue

        start_local = activity.get("startTimeLocal") or activity.get("startTimeGMT", "")
        date_str = start_local[:10] if start_local else datetime.now(timezone.utc).strftime("%Y-%m-%d")

        path = output_path(date_str)
        content = activity_to_markdown(activity)
        path.write_text(content)
        imported_set.add(activity_id)
        count_imported += 1
        print(f"  Wrote {path.name}  (activity {activity_id})")

    save_imported_set(imported_set)

    print(
        f"\nDone. Imported: {count_imported}, "
        f"skipped (ignored): {count_ignored}, "
        f"skipped (already imported): {count_already}."
    )


if __name__ == "__main__":
    main()
