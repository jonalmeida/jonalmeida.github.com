# Garmin run importer

`import_garmin_runs.py` pulls running activities from Garmin Connect and writes
them into the site as Zola posts under `content/runs/`, each with a route map
drawn as an SVG in `static/runs/maps/`.

One script, no build step. Dependencies are declared inline (PEP 723), so `uv`
fetches them on the fly:

```sh
uv run scripts/garmin/import_garmin_runs.py
```

Needs Python 3.11+. Every example below is run from the repository root.

## Credentials

Put these in `scripts/garmin/.env` (git-ignored) or the environment:

```sh
GARMIN_EMAIL=you@example.com
GARMIN_PASSWORD=...
```

The first run prompts for the Garmin MFA code interactively and caches OAuth
tokens in `scripts/garmin/.garmin_tokens/`. Later runs reuse those and do not
prompt. If Garmin starts rejecting the tokens, delete that directory and log in
again:

```sh
rm -rf scripts/garmin/.garmin_tokens
uv run scripts/garmin/import_garmin_runs.py
```

`--selftest` is the one mode that needs no credentials at all.

## Typical usage

### Import new runs

```sh
uv run scripts/garmin/import_garmin_runs.py
```

Fetches every running activity since `START_DATE` (2026-03-07), skips anything
already in `garmin_imported.json` or listed in `garmin_ignore.txt`, and for each
new one writes `content/runs/YYYY-MM-DD-run-YYYY-MM-DD.md` plus
`static/runs/maps/<activity_id>.svg`. Imported IDs are saved back to
`garmin_imported.json` at the end.

Two runs on the same day get `-2`, `-3` suffixes on the filename.

Cost per new activity: one `get_activity_details` call and one Overpass query.

### Import without maps

```sh
uv run scripts/garmin/import_garmin_runs.py --no-maps
```

Posts only. No details calls, no Overpass queries — the fastest way to catch up
on a backlog. Fill the maps in later with `--backfill-maps`.

### Import with the route but no OSM background

```sh
uv run scripts/garmin/import_garmin_runs.py --no-basemap
```

Draws the speed-coloured route on a plain background. No Overpass queries, and a
much smaller SVG.

## Backfilling maps

`--backfill-maps` imports nothing. It generates maps for activities already in
`garmin_imported.json` and inserts a `## Route` block into the matching post.

```sh
# every imported activity that has no map yet
uv run scripts/garmin/import_garmin_runs.py --backfill-maps
```

Posts are matched by their `garmin_activity_id` frontmatter key. The insert is
idempotent and additive: it never rewrites an existing line, it drops the block
in before `## Heart Rate Zones` (or at the end of the post if there is no such
heading), and it does nothing when the post already links a map. If no post
matches an ID, the script prints the shortcode line for you to paste manually.

### One or a few activities

```sh
uv run scripts/garmin/import_garmin_runs.py --backfill-maps --activity 22243257604
```

`--activity` is repeatable:

```sh
uv run scripts/garmin/import_garmin_runs.py --backfill-maps \
  --activity 22243257604 --activity 22571725386
```

### Force a re-write of existing maps

By default an activity whose SVG already exists is left alone. `--force`
regenerates it:

```sh
# redraw one map
uv run scripts/garmin/import_garmin_runs.py --backfill-maps --force \
  --activity 22243257604

# redraw everything (slow: one details call + one Overpass query each)
uv run scripts/garmin/import_garmin_runs.py --backfill-maps --force
```

Use this after changing anything about how maps are drawn — the road classes,
the colour ramp, the sizing. Cached Overpass responses make a full redraw much
cheaper than the first pass, as long as the query itself has not changed (see
below).

Note that `--force` re-runs the privacy trim, and the trim radius is derived
from the activity ID, so a redrawn map cuts at exactly the same place as before.

### Slow the Garmin calls down

```sh
uv run scripts/garmin/import_garmin_runs.py --backfill-maps --delay 3
```

`--delay` (default 0.75 s) is the pause between activity-details calls. Raise it
if Garmin starts returning 429s.

## Heart rate zones in feeds

Each post gets the zone data two times:

- A mermaid `xychart` in the body. A browser draws it with JavaScript.
- An `hr_zones` list in the front matter, for example
  `- { zone: 5, name: "Maximum", pct: 0.0 }`.

A feed reader removes JavaScript, so it cannot draw the chart. The feed
template `templates/atom.xml` therefore cuts the `## Heart Rate Zones`
section off the content and makes a plain table from `hr_zones` instead. A
post without `hr_zones` keeps its content as it is.

Keep the two in agreement: `hr_zone_percentages()` is the one source for
both.

## Caching

Two caches, both git-ignored:

| Path | Holds | Safe to delete |
|------|-------|----------------|
| `scripts/garmin/.garmin_tokens/` | Garmin OAuth tokens | Yes — costs one MFA prompt |
| `scripts/garmin/.overpass_cache/` | gzipped Overpass responses | Yes — costs one query per map |

Overpass is free, anonymous and rate-limited per IP, so every response is
cached. Cache files are keyed by a hash of the query text, which includes both
the bounding box and the tag filters. Two consequences:

- Redrawing the same route hits the cache and makes no network call at all.
- Changing which tags are drawn (`ROAD_WIDTHS`, `GREEN_LEISURE`,
  `GREEN_LANDUSE`, the waterway filter) changes the query and therefore misses
  every existing entry. The next run re-queries once per map, and the old
  entries become dead weight you can delete.

### Force fresh Overpass data

```sh
uv run scripts/garmin/import_garmin_runs.py --backfill-maps --force \
  --refresh-basemap --activity 22243257604
```

`--refresh-basemap` ignores the cache and queries again, then overwrites the
cached entry. Use it when the OpenStreetMap data itself has changed — a new
park, a re-drawn shoreline. It does nothing on its own during a backfill unless
the map is also being regenerated, so pair it with `--force`.

### Clearing the Overpass cache

```sh
du -sh scripts/garmin/.overpass_cache
rm -rf scripts/garmin/.overpass_cache
```

Only worth doing to reclaim disk or to drop entries stranded by a query change.
The script recreates the directory on the next run.

If an endpoint refuses a query, the script waits and retries, then falls through
a list of mirrors, and slows every later query down for the rest of the run. A
run that hits the rate limit hard is better stopped and restarted later — the
maps already written are cached and will not be re-queried.

## Privacy trim

Every route has a random 400–800 m cut off each end (capped at 7.5% of the route
length), so the real start and finish never reach a published file. The radius
is seeded from the activity ID: stable across redraws, different per run.

```sh
uv run scripts/garmin/import_garmin_runs.py --backfill-maps --force \
  --no-privacy-trim --activity 22243257604
```

`--no-privacy-trim` draws the whole track. Do not commit the result.

If a trim would leave too little of a route to be worth drawing, the script
writes no map and deletes any earlier SVG for that activity — an untrimmed file
left behind would be worse than no map.

## Self-test

```sh
uv run scripts/garmin/import_garmin_runs.py --selftest
uv run scripts/garmin/import_garmin_runs.py --selftest /tmp/check.svg
```

Renders a synthetic figure-eight route and asserts the map maths: the colour
ramp, the speed clipping and gap filling, the privacy trim (including a lap run
that never leaves its own start radius). No credentials, no network, writes to
`/tmp/route_selftest.svg` unless given a path. Run it after touching anything in
the drawing code.

## Ignoring activities

Add one activity ID per line to `garmin_ignore.txt`; `#` starts a comment. The
importer skips those IDs forever. Use it for races logged twice, walks that
Garmin filed as runs, or anything you do not want on the site.

To re-import a post from scratch, delete its markdown file and remove its ID
from the `imported` list in `garmin_imported.json`.

## What the map shows

- The GPS route, coloured by speed: dark navy for the slow stretches, pale blue
  for the fast ones, with a pace legend and an OpenStreetMap credit line.
- An OSM basemap of major streets only (motorway through tertiary, plus their
  link roads), green areas (parks, gardens, forest, grass, cemeteries, pitches,
  golf courses and similar), and water (rivers, streams, canals, lakes,
  coastline).
- Light and dark theme variants, switched by CSS inside the SVG.

Residential and unclassified streets, footways, cycleways and service roads are
deliberately absent: in a city they are most of the ways, and they cost both
clutter and bytes.

Maps are held to a size budget (160 KB). A map over budget is redrawn at
progressively lower detail — tertiary roads dropped first, then coarser vertex
thinning and a higher minimum feature size. If it is still too big at the lowest
level the script says so and suggests `--no-basemap` for that activity.

## Files

Tracked in git:

| Path | Purpose |
|------|---------|
| `import_garmin_runs.py` | the script |
| `garmin_imported.json` | activity IDs already imported |
| `garmin_ignore.txt` | activity IDs to skip |

Ignored: `.env`, `.garmin_tokens/`, `.overpass_cache/`.

Written elsewhere in the repo: `content/runs/*.md` and
`static/runs/maps/<activity_id>.svg`, embedded with
`{{ <image path="/runs/maps/<id>.svg" width={640} /> }}`.

## All options

```
--no-maps            skip route map generation (no extra API calls)
--backfill-maps      generate maps for already-imported activities and insert a
                     '## Route' block into their posts; imports nothing new
--no-basemap         draw the route without the OpenStreetMap background
--refresh-basemap    ignore the cached Overpass responses and query again
--no-privacy-trim    draw the whole track, including the real start and finish
--activity ID        with --backfill-maps, limit to these IDs (repeatable)
--force              with --backfill-maps, overwrite an SVG that exists already
--delay SECONDS      pause between activity-details API calls (default 0.75)
--selftest [PATH]    render a synthetic route and exit (no credentials needed)
```
