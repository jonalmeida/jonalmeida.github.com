"""The route map, as a string.

Pure: takes a prepared Track and already-fetched basemap data, and makes no
network calls. Everything about how the map looks lives here, including the OSM
tag-to-style mapping and the dark-theme CSS the file carries with it.
"""

from __future__ import annotations

from statistics import fmean

from garminrun.geo import Point
from garminrun.postfmt import format_pace_from_speed
from garminrun.ramp import (
    DARK_SPAN,
    LIGHT_SPAN,
    RAMP_BUCKETS,
    RAMP_DARK_HEX,
    RAMP_LIGHT_HEX,
    bucket_of,
    ramp_at_speed,
)
from garminrun.track import LEGEND_H, SVG_PAD, SVG_WIDTH, Track, prepare_track


STROKE_WIDTH = 3.2


MAX_SVG_WARN_BYTES = 160_000  # basemap detail budget, and the "too big" warning


BASEMAP_MIN_STEP_PX = 1.2     # thin dense node runs


MIN_GREEN_AREA_PX = 40.0      # drop tiny pitches and playgrounds


# Detail levels, tried in order until the file fits MAX_SVG_WARN_BYTES:
# (draw tertiary roads, thinning step px, min green area px2, min way extent px).
# Thinning drops vertices that sit close together and leaves the rest where they
# are. Do NOT snap coordinates to a coarse grid instead: snapping moves every
# vertex off its true position, and straight roads come out visibly wobbly for
# no real saving.
BASEMAP_DETAIL_LEVELS = (
    (True, BASEMAP_MIN_STEP_PX, MIN_GREEN_AREA_PX, 2.0),
    (False, BASEMAP_MIN_STEP_PX, MIN_GREEN_AREA_PX, 2.0),
    (False, 2.5, 200.0, 3.0),
)


# Road classes we draw, and their stroke width: the major street network only.
# Residential, unclassified, living streets, pedestrian ways, footways,
# cycleways, tracks, service roads and driveways are all left out on purpose:
# in a city they are most of the ways, and they cost both clutter and bytes.
ROAD_WIDTHS: dict[str, float] = {
    "motorway": 2.6, "motorway_link": 1.8, "trunk": 2.6, "trunk_link": 1.8,
    "primary": 2.4, "primary_link": 1.6, "secondary": 2.0, "secondary_link": 1.4,
    "tertiary": 1.7, "tertiary_link": 1.2,
}


BIG_ROADS = {
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
}


GREEN_LEISURE = {"park", "garden", "pitch", "golf_course", "playground"}


GREEN_LANDUSE = {
    "grass", "forest", "recreation_ground", "cemetery", "meadow",
    "village_green", "allotments",
}


def merge_runs(
    px: list[tuple[float, float]], buckets: list[int]
) -> list[tuple[int, list[tuple[float, float]]]]:
    """Group consecutive same-bucket segments into one polyline each.

    Each new run restarts on the previous run's last vertex. Together with
    stroke-linecap="round" that shared vertex hides the seam: both strokes put a
    half-disc on it, so no background shows through at a colour change.
    """
    runs: list[tuple[int, list[tuple[float, float]]]] = []
    current_bucket = buckets[0]
    current = [px[0], px[1]]
    for i in range(1, len(buckets)):
        if buckets[i] == current_bucket:
            current.append(px[i + 1])
        else:
            runs.append((current_bucket, current))
            current_bucket = buckets[i]
            current = [px[i], px[i + 1]]
    runs.append((current_bucket, current))
    return runs


def _num(value: float) -> str:
    """Compact number for SVG output ('18.4', '201' rather than '201.0')."""
    return f"{value:g}"


def _gradient(gradient_id: str, span: tuple[float, float]) -> str:
    """A 5-stop legend gradient, sampled from the same ramp as the route.

    Left to right is slow to fast, so the bar runs light to dark.
    """
    stops = "".join(
        f'<stop offset="{_num(offset)}" stop-color="{ramp_at_speed(offset, span)}"/>'
        for offset in (0.0, 0.25, 0.5, 0.75, 1.0)
    )
    return f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient>'


def _edge_crossing(
    outside: tuple[float, float], inside: tuple[float, float], width: float, height: float
) -> tuple[int, int] | None:
    """Where the segment enters the panel rectangle (Liang-Barsky clip)."""
    x0, y0 = outside
    dx, dy = inside[0] - x0, inside[1] - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0), (dx, width - x0), (-dy, y0), (dy, height - y0)):
        if p == 0:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            if r > t1:
                return None
            t0 = max(t0, r)
        else:
            if r < t0:
                return None
            t1 = min(t1, r)
    return (round(x0 + t0 * dx), round(y0 + t0 * dy))


def _basemap_path(
    track: Track, geometry: list[dict], min_step: float
) -> list[list[tuple[int, int]]]:
    """Project a way to whole pixels. Return only the parts inside the panel.

    Whole pixels keep the file small without the wobble a coarser grid causes.
    Cutting at the panel edge matters for privacy as well as size: a clipPath
    hides off-panel geometry on screen, but leaves every coordinate in the file
    for anyone who opens it. Each crossing gets an exact boundary point, so a
    road still reaches the edge of the panel.
    """
    out: list[tuple[int, int]] = []
    for node in geometry:
        lat, lon = node.get("lat"), node.get("lon")
        if lat is None or lon is None:
            continue
        x, y = track.to_px(lat, lon)
        candidate = (round(x), round(y))
        if out:
            last_x, last_y = out[-1]
            if candidate == out[-1]:
                continue
            if min_step and max(abs(candidate[0] - last_x), abs(candidate[1] - last_y)) < min_step:
                continue
        out.append(candidate)

    # Put back the closing node of a ring, if thinning dropped it.
    if len(out) > 2 and geometry[0].get("lat") == geometry[-1].get("lat") and out[0] != out[-1]:
        out.append(out[0])
    if len(out) < 2:
        return []

    width, height = float(SVG_WIDTH), float(track.panel_h)

    def inside(point: tuple[int, int]) -> bool:
        return 0 <= point[0] <= width and 0 <= point[1] <= height

    # Keep each run of vertices inside the panel, plus its boundary crossings.
    # A segment with both ends outside that clips a corner is dropped; for road
    # and park data that sliver is not worth the code.
    runs: list[list[tuple[int, int]]] = []
    current: list[tuple[int, int]] = []
    previous: tuple[int, int] | None = None
    for point in out:
        if inside(point):
            if previous is not None and not inside(previous):
                entry = _edge_crossing(previous, point, width, height)
                if entry and entry != point:
                    current.append(entry)
            current.append(point)
        elif previous is not None and inside(previous):
            exit_point = _edge_crossing(point, previous, width, height)
            if exit_point and exit_point != previous:
                current.append(exit_point)
            if len(current) >= 2:
                runs.append(current)
            current = []
        previous = point
    if len(current) >= 2:
        runs.append(current)
    return runs


def basemap_layers(
    track: Track,
    data: dict,
    tertiary_roads: bool = True,
    min_step: float = BASEMAP_MIN_STEP_PX,
    min_green: float = MIN_GREEN_AREA_PX,
    min_extent: float = 2.0,
) -> str:
    """Return the SVG for the green, water and road layers, in draw order.

    Only major streets are drawn. With tertiary_roads off, that narrows further
    to the arterials: a long run covers a much wider area, where even the
    tertiary network is both too much detail and too many bytes.
    """
    greens: list[list[dict]] = []
    waters: list[list[dict]] = []
    water_lines: list[list[dict]] = []
    roads: list[tuple[str, list[dict]]] = []

    for element in data.get("elements") or []:
        tags = element.get("tags") or {}
        if element.get("type") == "relation":
            # Approximate a multipolygon by its member rings; good enough here.
            for member in element.get("members") or []:
                if member.get("geometry"):
                    waters.append(member["geometry"])
            continue
        geometry = element.get("geometry")
        if not geometry:
            continue
        if tags.get("natural") in ("water", "coastline"):
            waters.append(geometry)
        elif tags.get("waterway"):
            water_lines.append(geometry)
        elif tags.get("leisure") in GREEN_LEISURE or tags.get("landuse") in GREEN_LANDUSE:
            greens.append(geometry)
        elif tags.get("highway") in ROAD_WIDTHS:
            roads.append((tags["highway"], geometry))

    def shapes(geometries, css_class: str, close: bool, min_area: float = 0.0) -> str:
        out = []
        for geometry in geometries:
            for pts in _basemap_path(track, geometry, min_step):
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                width, height = max(xs) - min(xs), max(ys) - min(ys)
                if min_area and width * height < min_area:
                    continue
                # Overpass splits ways at every junction, so a dense area yields
                # thousands of fragments too short to see.
                if max(width, height) < min_extent:
                    continue
                points = " ".join(f"{x},{y}" for x, y in pts)
                out.append(
                    f'<{"polygon" if close else "polyline"} class="{css_class}" points="{points}"/>'
                )
        return "\n".join(out)

    layers = [
        shapes(greens, "gr", True, min_green),
        shapes(waters, "wa", True),
        shapes(water_lines, "wl", False),
    ]
    # Widest roads first, so the small ones draw on top of the big ones.
    for name, width in sorted(ROAD_WIDTHS.items(), key=lambda kv: -kv[1]):
        if not tertiary_roads and name not in BIG_ROADS:
            continue
        group = [g for cls, g in roads if cls == name]
        body = shapes(group, "rd" if name in BIG_ROADS else "rn", False) if group else ""
        if body:
            layers.append(f'<g stroke-width="{width}">\n{body}\n</g>')

    return "\n".join(layer for layer in layers if layer)


def route_map_svg(
    points: list[Point], label: str = "", basemap: dict | None = None
) -> str | None:
    """Return a standalone SVG of the route, coloured by speed.

    Returns None (and never raises) when there is nothing worth drawing. Takes
    already-fetched basemap data, so it stays free of network calls.
    """
    track = prepare_track(points)
    if track is None:
        return None
    return render_route_svg(track, label=label, basemap=basemap)


def render_route_svg(track: Track, label: str = "", basemap: dict | None = None) -> str:
    """Draw a prepared track, optionally over an OSM basemap."""
    px, speeds, lo, hi = track.px, track.speeds, track.lo, track.hi
    buckets = [
        bucket_of(fmean((speeds[i], speeds[i + 1])), lo, hi)
        for i in range(len(px) - 1)
    ]
    runs = merge_runs(px, buckets)

    panel_h = track.panel_h
    legend_y = panel_h + 8
    total_h = panel_h + LEGEND_H + 12
    slow_label = format_pace_from_speed(lo)
    fast_label = format_pace_from_speed(hi)
    title = f"Route map{f' — {label}' if label else ''}"
    where = " on a street map" if basemap else ""
    aria = (
        f"Route map{where}{f', {label}' if label else ''}, "
        f"pace {slow_label} to {fast_label} per km"
    )

    # Firefox and Safari honour prefers-color-scheme for an SVG in an <img>;
    # older Chromium does not (crbug.com/1252199). The light palette rides on
    # the stroke attribute, so it is the graceful fallback and it matches the
    # site default. currentColor does not resolve in an <img>, hence .lg/.mk/.mkf.
    dark_rules = "".join(
        f".s{i}{{stroke:{RAMP_DARK_HEX[i]}}}" for i in range(RAMP_BUCKETS)
    )
    style = (
        f".rt{{fill:none;stroke-width:{STROKE_WIDTH};stroke-linecap:round;stroke-linejoin:round}}\n"
        ".lg{font:11px system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;fill:#555}\n"
        ".at{font:9px system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;fill:#8a8578}\n"
        ".mk{fill:none;stroke:#333;stroke-width:2}\n"
        ".mkf{fill:#333}\n"
        ".bar{fill:url(#rampL);stroke:#8884;stroke-width:.5}\n"
        ".bg{fill:#f4f1ea}\n"
        ".gr{fill:#e3ebdb;stroke:none}\n"
        ".wa{fill:#cfe0ea;stroke:none}\n"
        ".wl{fill:none;stroke:#cfe0ea;stroke-width:1.4}\n"
        ".rn{fill:none;stroke:#e2ddd2;stroke-linecap:round}\n"
        ".rd{fill:none;stroke:#d5cec0;stroke-linecap:round}\n"
        "@media (prefers-color-scheme:dark){\n"
        ".lg{fill:#c9d6da}.at{fill:#5c7580}.mk{stroke:#eee}.mkf{fill:#eee}.bar{fill:url(#rampD)}\n"
        ".bg{fill:#04202a}.gr{fill:#0a2c2c}.wa{fill:#062c3a}.wl{stroke:#062c3a}\n"
        ".rn{stroke:#0e3340}.rd{stroke:#14404e}\n"
        f"{dark_rules}\n"
        "}"
    )

    # The <g> carries fill, stroke-width and the caps once; all are inherited,
    # so each polyline costs only class, stroke and points.
    polylines = "\n".join(
        '<polyline class="s{b}" stroke="{hex}" points="{pts}"/>'.format(
            b=bucket,
            hex=RAMP_LIGHT_HEX[bucket],
            pts=" ".join(f"{_num(x)},{_num(y)}" for x, y in run),
        )
        for bucket, run in runs
    )

    panel = (
        f'<rect class="bg" x="0" y="0" width="{SVG_WIDTH}" height="{panel_h}" rx="6"/>\n'
        if basemap else ""
    )
    # ODbL requires the credit whenever OSM data is shown.
    attribution = (
        f'<text class="at" x="{SVG_WIDTH - 2 * SVG_PAD}" y="14" text-anchor="end">'
        "Map data &#169; OpenStreetMap contributors</text>\n"
        if basemap else ""
    )
    start_x, start_y = px[0]
    end_x, end_y = px[-1]

    def compose(layers: str) -> str:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_WIDTH} {total_h}" width="{SVG_WIDTH}" height="{total_h}" role="img" aria-label="{aria}">
<title>{title}</title>
<style>
{style}
</style>
<defs>
{_gradient("rampL", LIGHT_SPAN)}
{_gradient("rampD", DARK_SPAN)}
<clipPath id="panel"><rect x="0" y="0" width="{SVG_WIDTH}" height="{panel_h}" rx="6"/></clipPath>
</defs>
{panel}<g clip-path="url(#panel)">
{layers}<g class="rt">
{polylines}
</g>
<circle class="mk" cx="{_num(start_x)}" cy="{_num(start_y)}" r="5"/>
<circle class="mkf" cx="{_num(end_x)}" cy="{_num(end_y)}" r="2.2"/>
</g>
<g transform="translate({SVG_PAD},{legend_y})">
<rect class="bar" x="0" y="6" width="150" height="8" rx="4"/>
<text class="lg" x="0" y="30">{slow_label}/km</text>
<text class="lg" x="150" y="30" text-anchor="end">{fast_label}/km</text>
<text class="lg" x="166" y="14" dominant-baseline="middle">slower &#8594; faster</text>
{attribution}</g>
</svg>
"""

    if not basemap:
        return compose("")

    # Drop detail until the file fits the budget. Wide-area maps lose their
    # tertiary roads first, which is what a map at that scale should do anyway.
    svg = ""
    for level, (tertiary, step, green, extent) in enumerate(BASEMAP_DETAIL_LEVELS):
        svg = compose(
            basemap_layers(track, basemap, tertiary, step, green, extent) + "\n"
        )
        size = len(svg.encode())
        if size <= MAX_SVG_WARN_BYTES:
            if level:
                print(f"  basemap thinned to detail level {level} ({size / 1024:.0f} KB)")
            return svg
    print(f"  basemap still {len(svg.encode()) / 1024:.0f} KB at the lowest detail level")
    return svg
