# Garmin run importer

`import_garmin_runs.py` pulls running activities from Garmin Connect and writes
them into the site as Zola posts under `content/runs/`, each with the photos
attached to the activity and a route map drawn as an SVG in
`static/runs/maps/`. `run_import.sh` wraps it for cron: import, commit, push.

One script, no build step. Dependencies are declared inline (PEP 723), so `uv`
fetches them on the fly:

```sh
uv run scripts/garmin/import_garmin_runs.py
```

Needs Python 3.11+. Every example below is run from the repository root.

## Requirements

`brew-requirements.txt` is a plain list, one formula per line, so it can be
handed straight to `brew`:

```sh
brew install $(cat scripts/garmin/brew-requirements.txt)
```

| Formula | Needed for |
|---------|------------|
| `uv` | runs the script and fetches its inline (PEP 723) dependencies |
| `git` | `jj` shells out to it for every network operation |
| `jj` | the scheduled wrapper commits and pushes with it |
| `zola` | the wrapper builds the site before pushing |
| `imagemagick` | resizes the photos to 800 px |
| `jq` | the wrapper reads the importer's JSON report |
| `terminal-notifier` | tells you when a scheduled run fails |

Only `uv` is needed to import by hand. The rest are for `run_import.sh`, except
`imagemagick` — without it the resize falls back to `/usr/bin/sips`, which
ships with macOS.

Everything else the wrapper uses is already on macOS: `sips`, `shlock`, `nc`,
`ssh` and `crontab`.

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

`--sample-map` and `--print-crontab` are the two modes that need no
credentials at all. So are the tests: `uv run scripts/garmin/run_tests.py`.

## Typical usage

### Import new runs

```sh
uv run scripts/garmin/import_garmin_runs.py
```

Fetches every running activity since `START_DATE` (2026-03-07), skips anything
already in `garmin_imported.json`, listed in `garmin_ignore.txt`, or held back
by the content rules below, and for each new one writes a Zola page bundle:

```
content/runs/2026-09-06-run-2026-09-06/
    index.md
    2026-09-06-0.jpg
    2026-09-06-1.jpg
    2026-09-06-2.jpg
static/runs/maps/24260009891.svg
```

Two runs on the same day get `-2`, `-3` suffixes on the directory name.

Cost per new activity: one `get_activity_details` call, one `get_activity` call
and one Overpass query.

Imported IDs are saved back to `garmin_imported.json` once the whole run
finishes. An ID in that file means *fully done* and is never looked at again,
so an activity that fails part way through is deliberately left out and redone
from scratch on the next run.

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

## Photos

Garmin serves the photos attached to an activity, even though `garminconnect`
has no helper for them: they ride along on the full activity DTO as
`metadataDTO.activityImages`, presigned S3 URLs with no auth header and a 24 h
life. The importer downloads them into the post's page bundle as
`YYYY-MM-DD-N.jpg` and adds one line to the post:

```
{{ <gallery page={page} /> }}
```

`gallery.html` renders every `.jpg`/`.png` in the bundle as a 240×180
thumbnail. **Adding a file to a bundle publishes it** — there is no allow-list.

Every new post is a page bundle whether or not it has photos, so a photo
uploaded to Garmin after the import can be dropped in beside `index.md` without
renaming anything. Both shapes serve at the same URL, so nothing moves.

### Why 800 px

Photos are resized to 800 px before being committed. Three reasons:

- `gallery.html` links the *committed* file as the full-size image, so 800 px is
  what a reader actually gets when they click a thumbnail.
- These are plain git blobs, in the history for good. Garmin's originals are
  400–660 KB each; at 800 px they are ~130–200 KB. Over a year of two runs a
  week that is roughly 40 MB instead of 150 MB, paid by every clone and every
  CI checkout.
- It matches every photo that was added to `content/runs` by hand.

ImageMagick does the work if it is installed, then `sips`, which ships with
macOS so nothing needs bootstrapping. If neither is available the script falls
back to Garmin's own medium variant rather than commit a half-megabyte
original, and says so.

`--no-photo-resize` commits the bytes as downloaded. `--photo-width PX` picks a
different width.

Git LFS is deliberately **not** used: `jj` does not support it
([jj-vcs/jj#80](https://github.com/jj-vcs/jj/issues/80)), and the resize
removes the problem it would solve.

### Photos uploaded after the import

Photos usually reach Garmin after the run has already synced and been imported.

```sh
# one activity
uv run scripts/garmin/import_garmin_runs.py --backfill-photos --activity 24260009891

# every imported activity (one get_activity call each)
uv run scripts/garmin/import_garmin_runs.py --backfill-photos
```

This re-downloads all of that activity's photos and inserts the gallery line if
it is missing. It refuses to touch a flat `.md` post and prints the `mkdir`/`mv`
to convert it by hand; `--convert-flat` does it for you.

### If a photo cannot be fetched

The activity is deferred, not published: nothing is written to
`garmin_imported.json` and the next run redoes the whole thing. A post with
half its photos would be permanent, because an imported ID is never revisited.
A *missing map*, by contrast, only warns — `--backfill-maps` can fix that
later.

```sh
uv run scripts/garmin/import_garmin_runs.py --no-photos   # skip photos entirely
```

## What does not get published

Two rules decide this from the activity itself. Both are free: the name and the
description already ride on the activity-list payload.

**A marker in the name or description.** Put `#nopost` (or `#private`) in the
Garmin activity description — the same box the post prose is written in — and
the run is skipped. Matched case-insensitively, with a word-boundary guard, so
`#nopostcard` does not trigger it. The marker is stripped from the name and the
body of *every* post, published or not, so it can never leak onto the site.

**No description at all.** Nothing written about a run means it was not written
for the blog.

A skipped ID is appended to `garmin_ignore.txt` as a bare number with **no
reason beside it** — that file is tracked and public, so a trailing
`# marker #nopost` would leak exactly what the marker was meant to hide. The
reason is printed to stdout, which lands in the run log.

`garmin_ignore.txt` wins over everything, including `--no-content-filter`. To
publish a run that was skipped, delete its line there and either edit it in
Garmin or:

```sh
uv run scripts/garmin/import_garmin_runs.py --no-content-filter --max-new 1
```

Garmin's own per-activity privacy setting is wired up but off by default,
because every activity is currently `groups` and an allow-list would skip the
lot:

```sh
uv run scripts/garmin/import_garmin_runs.py --allowed-privacy public,subscribers,groups
```

### A published run that is later marked private

Re-checking already-imported runs is free, so the importer does it and reports:

```
RETRACT? 24312345678 is now marker #nopost but runs/2026-09-08-.../index.md is published
```

It stops there by default. The post is already public and in a feed that
readers' clients have cached, so deleting the file does not unpublish it and
leaves a 404 at a URL that may have been linked. `--retract draft` flips
`draft: false` to `true`, which drops the page from the build while leaving the
file and its history in place — the recoverable option. `--retract delete`
removes the post and its map.

The empty-description rule is ignored for this check: an absence is not a
withdrawal, and prose is sometimes written into the post rather than into
Garmin.

## Scheduled imports

`run_import.sh` runs the importer, commits each new run, and pushes. Cron drives
it twice a day.

### One-time setup

There is no ssh-agent under cron, so the push needs its own credential. Use a
repo-scoped, passphrase-less deploy key, which leaves `~/.ssh/config` alone so
interactive `git` and `jj` keep behaving exactly as they do now:

```sh
ssh-keygen -t ed25519 -N '' -C 'garmin-import' \
  -f ~/.ssh/id_ed25519_jonalmeida_site
chmod 600 ~/.ssh/id_ed25519_jonalmeida_site
pbcopy < ~/.ssh/id_ed25519_jonalmeida_site.pub
```

Paste it at *Settings → Deploy keys → Add deploy key* **on the repository**, and
tick **Allow write access**.

Do not add it under *Settings → SSH and GPG keys* on your account: that grants
the key write access to every repository you own, which for a passphrase-less
key sitting on disk is much wider than this job needs.

To check which kind you created, ask GitHub — but **isolate the key first**. A
bare `ssh -T git@github.com` ignores `GIT_SSH_COMMAND` and silently falls back
to a default identity such as `~/.ssh/id_rsa`, so it will happily report your
account even when the deploy key is set up correctly:

```sh
$ ssh -F /dev/null -i ~/.ssh/id_ed25519_jonalmeida_site \
    -o IdentitiesOnly=yes -o IdentityAgent=none -T git@github.com
Hi jonalmeida/jonalmeida.github.com!   # deploy key, correctly scoped
Hi jonalmeida!                         # account key, too broad
```

`-F /dev/null` ignores `~/.ssh/config` and `IdentitiesOnly=yes` stops ssh
offering anything else, so the answer is about that key and nothing else. Add
`-v` and look for `Offering public key:` to see exactly which file was used.

Read access proves nothing about scope, because a public repository is readable
with any key, or none. Only a write attempt does:

```sh
$ git push --dry-run git@github.com:jonalmeida/some-other-repo.git HEAD:refs/heads/probe
ERROR: Permission to jonalmeida/some-other-repo.git denied to deploy key
```

Finally, check the push path the wrapper actually uses, from a shell with no
agent. Here `GIT_SSH_COMMAND` is correct, because the caller is `git`:

```sh
env -u SSH_AUTH_SOCK GIT_SSH_COMMAND="/usr/bin/ssh \
  -i ~/.ssh/id_ed25519_jonalmeida_site -o IdentitiesOnly=yes \
  -o IdentityAgent=none -o BatchMode=yes" \
  git push --dry-run origin main
```

`Everything up-to-date` means the key authenticated and has write access.

Then install the cron entry. `--print-crontab` derives the absolute paths from
the script's own location, so a pasted entry cannot point at a repo that moved.

Build the new table in a file, read it, then install *from the file*. Do not
pipe straight into `crontab -`: if the write is refused part way through you
can be left with a truncated table, and there is nothing to inspect first.

```sh
{ crontab -l 2>/dev/null; \
  uv run scripts/garmin/import_garmin_runs.py --print-crontab; } > /tmp/new.cron
cat /tmp/new.cron        # check it before it goes live
crontab /tmp/new.cron
crontab -l
```

`--cron-hours 7,19` picks different times.

### crontab: Operation not permitted

Installing a crontab needs **Full Disk Access for the terminal application**,
not just for cron:

```
crontab: tmp/tmp.NNNNN: Operation not permitted
```

`/usr/bin/crontab` is setuid root and its temp directory is root-only, so this
is not a Unix permission problem — it is macOS TCC refusing the write. Grant
Full Disk Access to the terminal app in System Settings → Privacy & Security →
Full Disk Access, restart it, and try again. `sudo crontab -u "$USER"
/tmp/new.cron` sometimes gets through without the grant.

This is a *second* grant on top of the one cron may need to run the job. If
neither appeals, launchd needs no Full Disk Access at all and also survives
sleep — see below.

### What a run does

1. Refuses to act if the working copy has changes, if `jj workspace list` shows
   more than one workspace, or if no deploy key is present.
2. Waits for the network — cron can fire before Wi-Fi is up after a wake.
3. `jj git fetch`, and bails out if `origin/main` is ahead, before spending any
   Garmin API calls.
4. Imports one activity at a time (`--max-new 1`) so each gets its own
   `Run: YYYY-MM-DD.` commit, dated by the *activity*, and moves the `main`
   bookmark to it. Up to 10 per run.
5. Runs `zola build` into `/tmp` and only pushes if the site builds. A failure
   leaves the commits local for you to look at.

A PID-aware lock means a hand-run and a cron run cannot both commit. Try it
without any of the consequences:

```sh
scripts/garmin/run_import.sh --dry-run
tail -30 ~/Library/Logs/garmin-import.log
```

Exit codes: `0` nothing to do or pushed, `3` refused, `4` already running,
`5` Garmin needs an interactive login, `6` a step failed.

### When it stops working

`scripts/garmin/.needs_login` appearing means the Garmin tokens expired and MFA
needs a person. Nothing will import until you run it by hand once:

```sh
uv run scripts/garmin/import_garmin_runs.py
```

Two things to know about cron on macOS:

- **It does not catch up.** A slot that falls while the Mac is asleep is skipped
  entirely, not deferred. To survive that, switch the entry to `40 * * * *` and
  have the wrapper keep a timestamp, acting only when the last run is more than
  8 hours old.
- **Full Disk Access.** Needed once to install the table, and possibly again
  for `/usr/sbin/cron` to run the job. The job itself only touches `~/src`,
  `~/.ssh` and `~/Library/Logs`, none of which are protected, so it may run
  without the second grant. Do not move the repo under `~/Documents` or
  `~/Desktop`, which would make it mandatory.

### launchd instead

launchd needs no Full Disk Access and re-fires a schedule that was missed while
the Mac was asleep. `run_import.sh` works unchanged; only the schedule differs.

Write this to `~/Library/LaunchAgents/com.jonalmeida.garmin-import.plist`,
substituting the two placeholders:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.jonalmeida.garmin-import</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>REPO/scripts/garmin/run_import.sh</string>
  </array>
  <key>WorkingDirectory</key><string>REPO</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>HOME</key><string>HOMEDIR</string>
  </dict>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>40</integer></dict>
    <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>40</integer></dict>
  </array>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>HOMEDIR/Library/Logs/garmin-import.launchd.log</string>
  <key>StandardErrorPath</key><string>HOMEDIR/Library/Logs/garmin-import.launchd.log</string>
  <key>ProcessType</key><string>Background</string>
  <key>LowPriorityIO</key><true/>
  <key>ThrottleInterval</key><integer>300</integer>
</dict>
</plist>
```

```sh
plist=~/Library/LaunchAgents/com.jonalmeida.garmin-import.plist
sed -i '' -e "s|REPO|$PWD|g" -e "s|HOMEDIR|$HOME|g" "$plist"
plutil -lint "$plist"
launchctl bootstrap gui/$(id -u) "$plist"
launchctl kickstart -p gui/$(id -u)/com.jonalmeida.garmin-import   # run it now
launchctl print gui/$(id -u)/com.jonalmeida.garmin-import | grep -E 'state|last exit'
```

`RunAtLoad` is false on purpose: with it true, every login and every plist edit
fires a real import and push.

To change the plist later, `launchctl bootout` it first, then bootstrap again.

**`kickstart` looks like it hangs.** `ThrottleInterval` stops launchd running
the job more than once per 300 s, and that applies to a manual kickstart too.
If the job ran less than five minutes ago, `launchctl kickstart` blocks and
`launchctl print` shows `state = spawn scheduled` until the window clears —
then it runs normally. Nothing is wrong. To watch instead of waiting:

```sh
launchctl print gui/$(id -u)/com.jonalmeida.garmin-import | grep -E 'state|runs|last exit'
tail -f ~/Library/Logs/garmin-import.log
```

The throttle is there to stop a crash-looping job hammering Garmin. Drop
`ThrottleInterval` if the delay is more annoying than that risk.

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

## Tests

```sh
uv run scripts/garmin/run_tests.py
uv run scripts/garmin/run_tests.py -k trim -x     # arguments go through to pytest
uv run scripts/garmin/run_tests.py --golden-update
```

`run_tests.py` is a second PEP 723 script, so pytest needs no installing and
there is no `pyproject.toml` to keep in step. Everything runs offline: no
credentials, no network, no Garmin. Run it before every commit.

The suite lives in `tests/`, one file per module. What it is really guarding:

| Area | Why it matters |
|------|----------------|
| `test_geo.py` | the privacy trim. Both ends really cut, the result contiguous, stable per activity ID, and a lap run still trimmed. A regression here publishes a home address, permanently, in git history |
| `test_filters.py` | the publish rules, and that no `#nopost` or `#private` marker survives into a post under any flag combination |
| `test_run_import.py` | the whole importer against a fake Garmin. Includes the two contracts nothing checked before: that the `--report` JSON carries every key `run_import.sh` reads with `jq`, and that a photo failure leaves no bundle, no stray `.jpg` and no recorded ID |
| `test_overpass.py` | what happens when an Overpass endpoint misbehaves, including the 200-with-zero-elements answer that must never be cached |
| `test_golden.py` | golden files holding today's post markdown and route SVG byte for byte. `--golden-update` rewrites them after a wanted change |

`tests/golden/` and `tests/data/wide.jpg` are committed fixtures. GPS fixtures
are always synthetic — a real trace in the repo is the leak the privacy trim
exists to prevent.

### Looking at a map

```sh
uv run scripts/garmin/import_garmin_runs.py --sample-map
uv run scripts/garmin/import_garmin_runs.py --sample-map /tmp/check.svg
```

Draws a synthetic figure-eight route so a change to the drawing code can be
eyeballed. It checks nothing — that is what the tests are for. Writes to
`/tmp/route_sample.svg` unless given a path. `--selftest` still works as an
alias for this flag.

### Proving a change to the drawing code changed nothing

The privacy trim is seeded from the activity ID and the basemaps come from
`.overpass_cache/`, so redrawing a map is deterministic:

```sh
uv run scripts/garmin/import_garmin_runs.py --backfill-maps --force
jj diff --stat static/runs/maps/      # must be empty
```

An empty diff across all the committed maps is the strongest check available
for a refactor of `garminrun/svg.py`, `track.py` or `geo.py`. It needs Garmin
(one details call per activity), so it is a before-you-commit check rather than
a per-edit one.

## Ignoring activities

Add one activity ID per line to `garmin_ignore.txt`; `#` starts a comment. The
importer skips those IDs forever. Use it for races logged twice, walks that
Garmin filed as runs, or anything you do not want on the site. The content
rules above append to this same file, as bare IDs.

This list wins over everything, including `--no-content-filter`.

To re-import a post from scratch, remove its ID from the `imported` list in
`garmin_imported.json`. The post directory and its photos are overwritten, so
there is no need to delete them first — the slug is derived from the activity's
position among that date's runs, not from what is on disk.

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
| `import_garmin_runs.py` | the entry point: the PEP 723 header and a call to `cli.main()` |
| `garminrun/` | the importer itself, one module per concern |
| `run_tests.py` | the test runner, also a PEP 723 script |
| `tests/` | the test suite, its golden files and its fixtures |
| `run_import.sh` | the scheduled wrapper: import, commit, push |
| `brew-requirements.txt` | Homebrew formulae the script and wrapper need |
| `garmin_imported.json` | activity IDs already imported |
| `garmin_ignore.txt` | activity IDs to skip |

Ignored: `.env`, `.garmin_tokens/`, `.overpass_cache/`, `.needs_login`,
`.last_import.json`.

`garminrun/__init__.py` lists the modules in dependency order and says which
three reach outside the process. In short: `config` `state` `filters` `ramp`
`geo` `synthetic` `postfmt` `posts` `track` `svg` `overpass` `maps` `photos`
`garmin_client` `cli`, each importing only from the ones before it. `svg` sits
below `overpass` because the tag sets say how a feature is *drawn*, and the
query only asks for tags the drawing knows what to do with — so `svg` makes no
network calls and is a pure function of a `Track` plus basemap data.

`overpass._post`, `overpass._get` and `photos._fetch` are the only places the
importer touches the network, and each module that pauses has its own `_sleep`.
The tests replace all of them.

Written elsewhere in the repo:

- `content/runs/YYYY-MM-DD-run-YYYY-MM-DD/index.md` and its
  `YYYY-MM-DD-N.jpg` photos, shown with `{{ <gallery page={page} /> }}`
- `static/runs/maps/<activity_id>.svg`, embedded with
  `{{ <image path="/runs/maps/<id>.svg" width={640} /> }}`
- `~/Library/Logs/garmin-import.log`, the scheduled run log
## All options

Generated from `--help`, so it cannot drift:

```sh
uv run scripts/garmin/import_garmin_runs.py --help
```

```
  -h, --help            show this help message and exit
  --no-maps             skip route map generation (no extra API calls)
  --backfill-maps       generate route maps for already-imported activities
                        and insert a '## Route' block into their posts;
                        imports nothing new
  --no-basemap          draw the route without the OpenStreetMap background
                        (no Overpass queries, and a much smaller file)
  --refresh-basemap     ignore the cached Overpass responses and query again
                        (use when the OpenStreetMap data has changed)
  --no-privacy-trim     draw the whole track, including the real start and
                        finish (default: cut a random 400-800 m off each end)
  --no-content-filter   import everything, ignoring the marker and description
                        rules
  --private-marker TOKEN
                        token in the Garmin activity name or description that
                        means 'do not publish' (repeatable, default: #nopost
                        #private)
  --allowed-privacy LIST
                        comma-separated Garmin privacy typeKeys that may be
                        published, e.g. public,subscribers,groups (default:
                        allow every value)
  --retract {off,draft,delete}
                        what to do when an already-imported run now fails the
                        filter (default: off, which only reports it)
  --no-photos           skip photo download (saves one API call per activity)
  --backfill-photos     download photos for already-imported activities and
                        insert a gallery line into their posts; imports
                        nothing new
  --convert-flat        with --backfill-photos, turn a flat post into a page
                        bundle
  --photo-variant {url,smallUrl}
                        which Garmin variant to download (default: url, the
                        largest, which is then resized locally)
  --photo-width PX      resize photos to this width before committing
                        (default: 800)
  --no-photo-resize     commit the downloaded bytes as they are (around 500 KB
                        each)
  --activity ID         with --backfill-maps or --backfill-photos, limit to
                        these activity IDs (repeatable)
  --force               with --backfill-maps, overwrite an SVG that exists
                        already
  --delay SECONDS       pause between activity-details API calls (default:
                        0.75)
  --non-interactive     never prompt; exit 2 if Garmin needs an interactive
                        login (implied when stdin is not a terminal)
  --max-new N           import at most N new activities (0 = no limit). The
                        scheduled job uses 1, so every run gets its own commit
  --report PATH         write a JSON summary of this run, for the scheduled
                        wrapper
  --print-crontab       print a crontab entry for the scheduled importer and
                        exit (needs no Garmin credentials)
  --cron-hours LIST     with --print-crontab, the hours to run at (default:
                        8,20)
  --sample-map, --selftest [PATH]
                        draw a synthetic route and exit, to eyeball a change
                        to the drawing code (no Garmin credentials needed).
                        The assertions that used to ride along with --selftest
                        are now a pytest suite: uv run
                        scripts/garmin/run_tests.py
```
