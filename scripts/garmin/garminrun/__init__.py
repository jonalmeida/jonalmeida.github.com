"""The Garmin run importer, split by concern.

The entry point is ../import_garmin_runs.py, which carries the PEP 723
dependency header and does nothing but call cli.main(). `uv run` puts the
script's own directory on sys.path[0], so this package is importable with no
packaging files.

Dependency order, lowest first. Nothing imports anything above it:

    config          paths, and the constants more than one module needs
    state           garmin_ignore.txt and garmin_imported.json
    filters         what does not get published
    ramp            speed -> colour
    geo             Garmin payload -> points, geodesy, statistics, privacy trim
    synthetic       a fake route, for --sample-map and the tests
    postfmt         activity -> post markdown
    posts           slugs, the post index, in-place edits, retraction
    track           pixel-space fitting and thinning
    svg             the route map as a string, and the OSM tag-to-style mapping
    overpass        the OSM query, its cache and its mirrors
    maps            write_route_map: the I/O shell around svg
    photos          download and resize
    garmin_client   the only module that imports garminconnect
    cli             argument parsing and the three commands

svg sits below overpass, not above it: ROAD_WIDTHS and the green/water tag sets
say how a feature is drawn, and the query only asks for the tags the drawing
knows what to do with. So overpass imports them from svg, and svg makes no
network calls at all.

Three modules reach outside the process, and each does it through a named hook
that a test replaces: overpass._post / overpass._get, photos._fetch, and a
_sleep in each of overpass, photos and garmin_client.
"""
