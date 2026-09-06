"""The Garmin run importer, split by concern.

The entry point is ../import_garmin_runs.py, which carries the PEP 723
dependency header and does nothing but call cli.main(). `uv run` puts the
script's own directory on sys.path[0], so this package is importable with no
packaging files.

Dependency order, lowest first. Nothing imports anything above it:

    config      paths and the two cross-module URL constants
    state       garmin_ignore.txt and garmin_imported.json
    filters     what does not get published
    ramp        speed -> colour
    geo         Garmin payload -> points, geodesy, statistics, privacy trim
    postfmt     activity -> post markdown
    posts       slugs, the post index, in-place edits, retraction
    track       pixel-space fitting and thinning
    svg         the route map and the OSM basemap, as a string
    overpass    the OSM query, its cache and its mirrors
    maps        write_route_map: the I/O shell around svg
    photos      download and resize
    garmin_client   the only module that imports garminconnect
    synthetic   a fake route, for --sample-map and the tests
    cli         argument parsing and the three commands
"""
