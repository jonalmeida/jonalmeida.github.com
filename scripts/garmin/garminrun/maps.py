"""write_route_map: the I/O shell around svg.

Everything that touches the filesystem or the network on the way to a map file
lives here, so svg.py stays a pure function of its inputs.
"""

from __future__ import annotations

from garminrun import config
from garminrun.config import MAP_URL_PREFIX
from garminrun.geo import Point, trim_route_ends
from garminrun.overpass import fetch_basemap
from garminrun.svg import MAX_SVG_WARN_BYTES, render_route_svg
from garminrun.track import prepare_track


def write_route_map(
    activity_id: int,
    points: list[Point],
    label: str = "",
    basemap: bool = True,
    privacy_trim: bool = True,
    refresh_basemap: bool = False,
) -> str | None:
    """Write static/runs/maps/<id>.svg. Return its site path, or None."""
    path = config.PATHS.maps / f"{activity_id}.svg"

    def give_up(reason: str) -> None:
        """Report, and remove any earlier map for this activity.

        Leaving the previous file in place would be the worst outcome: it was
        drawn before the privacy trim existed, so it still shows the real start
        and finish.
        """
        print(f"  no map for {activity_id}: {reason}")
        if path.exists():
            path.unlink()
            print(f"  removed the earlier {path.name}, which was not trimmed")

    trimmed, radius = trim_route_ends(points, activity_id, privacy_trim)
    if len(trimmed) < 2:
        give_up("the privacy trim leaves too little of the route")
        return None
    if radius:
        print(
            f"  privacy trim: {radius:.0f} m off each end, "
            f"keeping {len(trimmed)} of {len(points)} samples"
        )
    points = trimmed

    track = prepare_track(points)
    if track is None:
        give_up("the route is too small to draw")
        return None
    data = fetch_basemap(track, use_cache=not refresh_basemap) if basemap else None
    svg = render_route_svg(track, label=label, basemap=data)

    config.PATHS.maps.mkdir(parents=True, exist_ok=True)
    path.write_text(svg)
    size = len(svg.encode())
    # Count only the route's polylines; the basemap has its own.
    segments = svg.count('<polyline class="s')
    print(f"  Wrote map {path.name} ({size / 1024:.1f} KB, {segments} segments)")
    if size > MAX_SVG_WARN_BYTES:
        print(
            f"  WARNING: {path.name} is large even at the lowest basemap detail; "
            "consider --no-basemap for this one"
        )
    return f"{MAP_URL_PREFIX}/{activity_id}.svg"
