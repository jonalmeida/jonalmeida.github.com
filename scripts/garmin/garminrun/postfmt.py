"""An activity, as the markdown of a Zola page bundle.

Pure string building: no filesystem, no network, no clock beyond the date the
activity itself carries.
"""

from __future__ import annotations

from datetime import datetime, timezone

from garminrun.config import MAP_EMBED_WIDTH
from garminrun.filters import PRIVATE_MARKERS, strip_markers


# Photos. Garmin returns them on the full activity DTO, as presigned S3 URLs
# with no auth header and a 24 h life. Every new post is a Zola page bundle, so
# the photos sit beside index.md and the gallery component finds them.
GALLERY_SHORTCODE = "{{ <gallery page={page} /> }}"


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


def format_pace_from_speed(mps: float) -> str:
    """Return M:SS pace per km for a speed in m/s ('--:--' if implausible)."""
    if not mps or mps < 0.4:
        return "--:--"
    return format_pace(1000.0 / mps)


ZONE_NAMES = {1: "Warm Up", 2: "Easy", 3: "Aerobic", 4: "Threshold", 5: "Maximum"}


def hr_zone_percentages(activity: dict) -> list[tuple[int, float]]:
    """Return [(zone, percent of the time)] for the HR zones, zone 5 first.

    The list is empty when the activity has no zone data.
    """
    # Collect all hrTimeInZone_N keys (e.g. hrTimeInZone_1 … hrTimeInZone_5)
    zone_data: list[tuple[int, int]] = []
    for key, value in activity.items():
        if key.startswith("hrTimeInZone_"):
            suffix = key[len("hrTimeInZone_"):]
            if suffix.isdigit():
                zone_data.append((int(suffix), int(value or 0)))

    if not zone_data:
        return []

    # A run recorded without a heart-rate strap still carries all five keys,
    # every one of them zero. That is no data, not five empty zones: reporting
    # it would put `mermaid: true` and a chart of nothing on the page, a table
    # of nothing in the feed, and load mermaid.min.js to draw neither.
    total = sum(seconds for _, seconds in zone_data)
    if not total:
        return []

    # Display zone 5 → 1 (top to bottom, matching Garmin UI)
    zone_data.sort(key=lambda x: -x[0])

    return [(zone, round(secs / total * 100, 1)) for zone, secs in zone_data]


def hr_zones_front_matter(activity: dict) -> str:
    """Return an `hr_zones` front matter block, or empty string.

    A feed reader removes JavaScript, so it cannot draw the mermaid chart.
    The feed template (templates/atom.xml) makes a plain table from this
    data instead. The page itself still shows the chart.
    """
    zones = hr_zone_percentages(activity)
    if not zones:
        return ""

    lines = ["\n  hr_zones:"]
    for zone, pct in zones:
        name = ZONE_NAMES.get(zone, "")
        lines.append(f'    - {{ zone: {zone}, name: "{name}", pct: {pct} }}')
    return "\n".join(lines)


def hr_zones_mermaid(activity: dict) -> str:
    """Return a mermaid xychart component for time in HR zones, or empty string."""
    zones = hr_zone_percentages(activity)
    if not zones:
        return ""

    n = len(zones)
    labels = ", ".join(f'"Zone {z} {ZONE_NAMES.get(z, "")}"' for z, _ in zones)

    # One bar series per zone so each picks up its own palette color from the
    # plotColorPalette defined in mermaid.html (gray, orange, green, blue, lightgray).
    bar_lines = []
    for i, (_, pct) in enumerate(zones):
        values = ["0.0"] * n
        values[i] = f"{pct:.1f}"
        bar_lines.append(f"    bar [{', '.join(values)}]")

    lines = [
        "{% <mermaid> %}",
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
        "{% </mermaid> %}",
    ]
    return "\n".join(lines)


def activity_date(activity: dict) -> str:
    """The activity's local start date as YYYY-MM-DD."""
    start_local = activity.get("startTimeLocal") or activity.get("startTimeGMT", "")
    if start_local:
        return start_local[:10]
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def yaml_dq(value: str) -> str:
    """Escape a value for a YAML double-quoted scalar.

    An activity name is whatever was typed on the phone. Without this, a name
    holding a double quote breaks the front matter, and for a page bundle that
    leaves a directory of orphaned photos behind.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


def activity_to_markdown(
    activity: dict,
    map_url: str | None = None,
    photos: int = 0,
    markers: tuple[str, ...] = PRIVATE_MARKERS,
) -> str:
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

    date_str = activity_date(activity)
    title = strip_markers(activity["activityName"], markers)

    # strip_markers also tidies the trailing spaces the phone keyboard leaves.
    description = strip_markers(activity.get("description") or "", markers)
    mermaid_chart = hr_zones_mermaid(activity)
    chart_section = f"\n## Heart Rate Zones\n\n{mermaid_chart}\n" if mermaid_chart else ""
    mermaid_flag = "\n  mermaid: true" if mermaid_chart else ""
    zones_block = hr_zones_front_matter(activity)
    route_section = f"\n## Route\n\n{route_shortcode(map_url)}\n" if map_url else ""

    frontmatter = f"""---
title: "{yaml_dq(title)}"
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
  elevation_gain_m: {elevation_str}{mermaid_flag}{zones_block}
---"""

    table = f"""
| Stat | Value |
|------|-------|
| Distance | {distance_km} km |
| Duration | {duration_str} |
| Pace | {pace_str} /km |
| Elevation Gain | {elevation_str} m |
"""

    # The gallery goes between the prose and the stats table, which is where
    # every hand-made post put it.
    gallery_section = f"\n{GALLERY_SHORTCODE}\n" if photos else ""

    return (
        frontmatter + "\n" + description + "\n" + gallery_section
        + table + route_section + chart_section
    )


def route_shortcode(map_url: str) -> str:
    """Return the image() shortcode line for a map URL."""
    return f'{{{{ <image path="{map_url}" width={{{MAP_EMBED_WIDTH}}} /> }}}}'
