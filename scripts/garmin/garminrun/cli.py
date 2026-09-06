"""Argument parsing and the three commands: import, backfill maps, backfill photos."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin

from garminrun import config
from garminrun.config import EXIT_NEEDS_LOGIN, MAP_URL_PREFIX, START_DATE
from garminrun.filters import PRIVATE_MARKERS, FilterRules, publish_decision
from garminrun.garmin_client import (
    DETAILS_DELAY_S,
    NeedsLogin,
    authenticate,
    fetch_activity_points,
    fetch_running_activities,
)
from garminrun.geo import PRIVACY_TRIM_MAX_M, PRIVACY_TRIM_MIN_M
from garminrun.maps import write_route_map
from garminrun.photos import (
    PHOTO_TARGET_WIDTH,
    PhotoFailure,
    download_photos,
    fetch_activity_photos,
)
from garminrun.postfmt import (
    activity_date,
    activity_to_markdown,
    format_pace_from_speed,
    route_shortcode,
)
from garminrun.posts import (
    index_posts_by_activity_id,
    insert_gallery_shortcode,
    insert_route_shortcode,
    output_path,
    post_dir,
    post_distance_label,
    retract_post,
    slug_for,
)
from garminrun.state import (
    append_ignore,
    load_ignore_set,
    load_imported_set,
    save_imported_set,
)
from garminrun.svg import route_map_svg
from garminrun.synthetic import synthetic_points
from garminrun.track import prepare_track


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Garmin running activities to Zola markdown files."
    )
    parser.add_argument(
        "--no-maps", action="store_true",
        help="skip route map generation (no extra API calls)",
    )
    parser.add_argument(
        "--backfill-maps", action="store_true",
        help="generate route maps for already-imported activities and insert a "
             "'## Route' block into their posts; imports nothing new",
    )
    parser.add_argument(
        "--no-basemap", action="store_true",
        help="draw the route without the OpenStreetMap background "
             "(no Overpass queries, and a much smaller file)",
    )
    parser.add_argument(
        "--refresh-basemap", action="store_true",
        help="ignore the cached Overpass responses and query again "
             "(use when the OpenStreetMap data has changed)",
    )
    parser.add_argument(
        "--no-privacy-trim", action="store_true",
        help=f"draw the whole track, including the real start and finish "
             f"(default: cut a random {PRIVACY_TRIM_MIN_M:.0f}-{PRIVACY_TRIM_MAX_M:.0f} m "
             f"off each end)",
    )
    parser.add_argument(
        "--no-content-filter", action="store_true",
        help="import everything, ignoring the marker and description rules",
    )
    parser.add_argument(
        "--private-marker", action="append", metavar="TOKEN", default=None,
        help="token in the Garmin activity name or description that means "
             "'do not publish' (repeatable, default: "
             f"{' '.join(PRIVATE_MARKERS)})",
    )
    parser.add_argument(
        "--allowed-privacy", metavar="LIST", default="",
        help="comma-separated Garmin privacy typeKeys that may be published, "
             "e.g. public,subscribers,groups (default: allow every value)",
    )
    parser.add_argument(
        "--retract", choices=("off", "draft", "delete"), default="off",
        help="what to do when an already-imported run now fails the filter "
             "(default: %(default)s, which only reports it)",
    )
    parser.add_argument(
        "--no-photos", action="store_true",
        help="skip photo download (saves one API call per activity)",
    )
    parser.add_argument(
        "--backfill-photos", action="store_true",
        help="download photos for already-imported activities and insert a "
             "gallery line into their posts; imports nothing new",
    )
    parser.add_argument(
        "--convert-flat", action="store_true",
        help="with --backfill-photos, turn a flat post into a page bundle",
    )
    parser.add_argument(
        "--photo-variant", choices=("url", "smallUrl"), default="url",
        help="which Garmin variant to download (default: %(default)s, the "
             "largest, which is then resized locally)",
    )
    parser.add_argument(
        "--photo-width", type=int, default=PHOTO_TARGET_WIDTH, metavar="PX",
        help="resize photos to this width before committing (default: %(default)s)",
    )
    parser.add_argument(
        "--no-photo-resize", action="store_true",
        help="commit the downloaded bytes as they are (around 500 KB each)",
    )
    parser.add_argument(
        "--activity", type=int, action="append", metavar="ID",
        help="with --backfill-maps or --backfill-photos, limit to these "
             "activity IDs (repeatable)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="with --backfill-maps, overwrite an SVG that exists already",
    )
    parser.add_argument(
        "--delay", type=float, default=DETAILS_DELAY_S, metavar="SECONDS",
        help="pause between activity-details API calls (default: %(default)s)",
    )
    parser.add_argument(
        "--non-interactive", action="store_true",
        help=f"never prompt; exit {EXIT_NEEDS_LOGIN} if Garmin needs an "
             "interactive login (implied when stdin is not a terminal)",
    )
    parser.add_argument(
        "--max-new", type=int, default=0, metavar="N",
        help="import at most N new activities (0 = no limit). The scheduled "
             "job uses 1, so every run gets its own commit",
    )
    parser.add_argument(
        "--report", metavar="PATH",
        help="write a JSON summary of this run, for the scheduled wrapper",
    )
    parser.add_argument(
        "--print-crontab", action="store_true",
        help="print a crontab entry for the scheduled importer and exit "
             "(needs no Garmin credentials)",
    )
    parser.add_argument(
        "--cron-hours", metavar="LIST", default="8,20",
        help="with --print-crontab, the hours to run at (default: %(default)s)",
    )
    parser.add_argument(
        "--sample-map", "--selftest", dest="sample_map",
        nargs="?", const="/tmp/route_sample.svg", metavar="PATH",
        help="draw a synthetic route and exit, to eyeball a change to the "
             "drawing code (no Garmin credentials needed). The assertions that "
             "used to ride along with --selftest are now a pytest suite: "
             "uv run scripts/garmin/run_tests.py",
    )
    # argv=None means sys.argv, which is what the entry point wants; a test
    # passes a list instead of patching sys.argv.
    args = parser.parse_args(argv)
    if args.no_photo_resize:
        args.photo_width = 0
    args.private_marker = tuple(args.private_marker or PRIVATE_MARKERS)
    args.allowed_privacy = frozenset(
        key.strip().lower() for key in args.allowed_privacy.split(",") if key.strip()
    )
    return args


def filter_rules(args: argparse.Namespace) -> FilterRules:
    """The publish policy the flags describe."""
    return FilterRules(
        private_markers=args.private_marker,
        allowed_privacy=args.allowed_privacy,
        no_content_filter=args.no_content_filter,
    )


def run_import(client: Garmin, args: argparse.Namespace) -> None:
    rules = filter_rules(args)
    ignore_set = load_ignore_set()
    imported_set = load_imported_set()
    print(f"Loaded {len(ignore_set)} ignored IDs, {len(imported_set)} already-imported IDs.")

    activities = fetch_running_activities(client)
    print(f"Fetched {len(activities)} running activities since {START_DATE}.")

    # slug_for needs every activity that shares a date, so group up front.
    by_date: dict[str, list[dict]] = {}
    for activity in activities:
        by_date.setdefault(activity_date(activity), []).append(activity)

    posts_by_id = index_posts_by_activity_id()

    count_imported = 0
    count_ignored = 0
    count_already = 0
    count_deferred = 0
    count_filtered = 0
    report_imported: list[dict] = []
    retract_candidates: list[dict] = []

    for activity in activities:
        activity_id = int(activity["activityId"])

        if activity_id in ignore_set:
            count_ignored += 1
            continue

        if activity_id in imported_set:
            count_already += 1
            # The list payload covers imported activities too, so re-checking
            # is free. Report only: the post is already public and in a feed
            # readers have cached, so deleting it does not unpublish it and
            # leaves a 404 at a linked URL. That is not a robot's call to make
            # at 08:40 with nobody watching.
            publish, reason = publish_decision(activity, rules, for_retract=True)
            if not publish:
                post = posts_by_id.get(activity_id)
                where = f"{post.parent.name}/{post.name}" if post else "(post not found)"
                print(f"  RETRACT? {activity_id} is now {reason} but {where} is published")
                retract_candidates.append(
                    {"activity_id": activity_id, "reason": reason, "post": where}
                )
                if args.retract != "off" and post is not None:
                    retract_post(post, activity_id, args.retract)
            continue

        publish, reason = publish_decision(activity, rules)
        if not publish:
            print(f"  skipping {activity_id}: {reason}")
            append_ignore(activity_id)
            count_filtered += 1
            continue

        date_str = activity_date(activity)

        # Photos first, because this is the step that can defer the activity.
        # Doing it before the map saves an Overpass query on a deferral.
        images: list[dict] = []
        if not args.no_photos:
            try:
                images = fetch_activity_photos(client, activity_id)
            except PhotoFailure as exc:
                print(f"  WARNING: {exc}")
                print(f"  deferring {activity_id}; the next run will retry it")
                count_deferred += 1
                continue
            if images:
                time.sleep(args.delay)

        map_url = None
        if not args.no_maps:
            points = fetch_activity_points(client, activity_id)
            time.sleep(args.delay)
            if len(points) >= 2:
                distance_km = round((activity.get("distance") or 0) / 1000, 2)
                map_url = write_route_map(
                    activity_id, points,
                    label=f"{distance_km} km", basemap=not args.no_basemap,
                    privacy_trim=not args.no_privacy_trim,
                    refresh_basemap=args.refresh_basemap,
                )
            if len(points) < 2:
                print(f"  no GPS data for {activity_id} (treadmill?) - map skipped")

        slug = slug_for(activity, date_str, by_date[date_str])
        path = output_path(slug)

        names: list[str] = []
        if images:
            try:
                names = download_photos(
                    client, activity_id, images, path.parent, date_str,
                    variant=args.photo_variant, width=args.photo_width,
                )
            except PhotoFailure as exc:
                print(f"  WARNING: {exc}")
                print(f"  deferring {activity_id}; the next run will retry it")
                count_deferred += 1
                # A bundle with no index.md is invisible to Zola, but leave no
                # litter behind either.
                for partial in path.parent.glob("*.jpg"):
                    partial.unlink()
                if path.parent.is_dir() and not any(path.parent.iterdir()):
                    path.parent.rmdir()
                continue

        # index.md last. A directory of photos with no index.md is invisible to
        # Zola, so a run that dies here leaves nothing published.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            activity_to_markdown(
                activity, map_url, photos=len(names), markers=args.private_marker
            )
        )
        imported_set.add(activity_id)
        count_imported += 1
        report_imported.append({
            "activity_id": activity_id,
            "date": date_str,
            "path": str(path.relative_to(config.PATHS.repo)),
            "photos": len(names),
        })
        print(
            f"  Wrote {path.parent.name}/{path.name}  "
            f"({len(names)} photos, activity {activity_id})"
        )

        if args.max_new and count_imported >= args.max_new:
            print(f"  stopping at --max-new {args.max_new}")
            break

    # Written once, only after the whole run succeeded. An activity that is not
    # in here has to be redone from scratch, which is why slug_for is
    # deterministic and download_photos overwrites.
    save_imported_set(imported_set)

    deferred = f", deferred: {count_deferred}" if count_deferred else ""
    print(
        f"\nDone. Imported: {count_imported}, "
        f"skipped (ignored): {count_ignored}, "
        f"skipped (filtered): {count_filtered}, "
        f"skipped (already imported): {count_already}{deferred}."
    )
    if count_filtered:
        print(
            f"\nThe {count_filtered} filtered run(s) are now in "
            f"{config.PATHS.ignore.name}. To publish one, delete its line there and "
            "either edit it in Garmin or re-run with --no-content-filter."
        )

    if args.report:
        Path(args.report).write_text(json.dumps({
            "imported_count": count_imported,
            "imported": report_imported,
            "filtered_count": count_filtered,
            "deferred_count": count_deferred,
            "retract_candidates": retract_candidates,
        }, indent=2) + "\n")


def run_backfill(client: Garmin, args: argparse.Namespace) -> None:
    targets = sorted(args.activity or load_imported_set())
    posts = index_posts_by_activity_id()
    print(f"Backfilling maps for {len(targets)} activities.")

    count_written = 0
    count_existing = 0
    count_no_gps = 0
    count_inserted = 0

    for i, activity_id in enumerate(targets):
        destination = config.PATHS.maps / f"{activity_id}.svg"
        map_url: str | None = None
        post = posts.get(activity_id)

        if destination.exists() and not args.force:
            print(f"  {activity_id}: map exists (use --force to regenerate)")
            count_existing += 1
            map_url = f"{MAP_URL_PREFIX}/{activity_id}.svg"
        else:
            points = fetch_activity_points(client, activity_id)
            if i < len(targets) - 1:
                time.sleep(args.delay)
            if len(points) >= 2:
                map_url = write_route_map(
                    activity_id, points,
                    label=post_distance_label(post),
                    basemap=not args.no_basemap,
                    privacy_trim=not args.no_privacy_trim,
                    refresh_basemap=args.refresh_basemap,
                )
            if map_url is None:
                count_no_gps += 1
                continue
            count_written += 1

        if post is None:
            print(f"  {activity_id}: no post found; add manually: {route_shortcode(map_url)}")
        elif insert_route_shortcode(post, route_shortcode(map_url)):
            print(f"  {activity_id}: inserted into {post.name}")
            count_inserted += 1
        else:
            print(f"  {activity_id}: already linked in {post.name}")

    print(
        f"\nDone. Maps written: {count_written}, "
        f"already present: {count_existing}, "
        f"no GPS: {count_no_gps}, "
        f"posts updated: {count_inserted}."
    )


def run_backfill_photos(client: Garmin, args: argparse.Namespace) -> None:
    """Download photos for activities that were imported before the photos
    were uploaded to Garmin, and insert a gallery line into their posts."""
    targets = sorted(args.activity or load_imported_set())
    posts = index_posts_by_activity_id()
    print(f"Backfilling photos for {len(targets)} activities.")

    count_photos = 0
    count_none = 0
    count_inserted = 0
    count_failed = 0

    for i, activity_id in enumerate(targets):
        post = posts.get(activity_id)
        if post is None:
            print(f"  {activity_id}: no post found; skipping")
            continue

        bundle = post_dir(post)
        if bundle is None:
            # Renaming a post changes nothing about its URL, but it is still a
            # destructive move. Refuse by default and hand over the command.
            if not args.convert_flat:
                print(f"  {activity_id}: {post.name} is a flat post. Convert it with:")
                print(f"      mkdir content/runs/{post.stem} && \\")
                print(f"        mv content/runs/{post.name} content/runs/{post.stem}/index.md")
                print("    or re-run with --convert-flat")
                continue
            bundle = post.with_suffix("")
            bundle.mkdir(parents=True, exist_ok=True)
            post = post.rename(bundle / "index.md")
            print(f"  {activity_id}: converted to a page bundle {bundle.name}/")

        try:
            images = fetch_activity_photos(client, activity_id)
        except PhotoFailure as exc:
            print(f"  WARNING: {exc}")
            count_failed += 1
            continue
        if i < len(targets) - 1:
            time.sleep(args.delay)

        if not images:
            print(f"  {activity_id}: no photos on Garmin")
            count_none += 1
            continue

        try:
            names = download_photos(
                client, activity_id, images, bundle, bundle.name[:10],
                variant=args.photo_variant, width=args.photo_width,
            )
        except PhotoFailure as exc:
            print(f"  WARNING: {exc}")
            count_failed += 1
            continue

        count_photos += len(names)
        if insert_gallery_shortcode(post):
            print(f"  {activity_id}: inserted the gallery into {bundle.name}/index.md")
            count_inserted += 1

    print(
        f"\nDone. Photos written: {count_photos}, "
        f"no photos: {count_none}, "
        f"posts updated: {count_inserted}, "
        f"failed: {count_failed}."
    )


def write_sample_map(path: Path) -> None:
    """Draw the synthetic route to `path` and report what came out.

    Checks nothing: this is for looking at. The map maths is asserted in
    tests/test_svg.py, tests/test_geo.py and tests/test_ramp.py, which pytest
    collects and `python -O` cannot switch off.
    """
    points = synthetic_points()
    svg = route_map_svg(points, label="10.1 km")
    if svg is None:
        raise SystemExit("the synthetic route did not draw; run the tests")
    path.write_text(svg)

    track = prepare_track(points)
    print(f"Wrote {path} ({len(svg.encode()) / 1024:.1f} KB)")
    print(f"  points: {len(points)} in, {len(track.px)} after decimation")
    print(f"  polylines: {svg.count('<polyline')}")
    print(
        f"  legend: {format_pace_from_speed(track.lo)}/km (slow) -> "
        f"{format_pace_from_speed(track.hi)}/km (fast)"
    )


def print_crontab(hours: str) -> None:
    """Print a crontab entry for the scheduled importer.

    The paths come from this file's own location, so a copy-pasted entry cannot
    point at a repo that has moved.
    """
    wrapper = config.PATHS.scripts / "run_import.sh"
    log = Path.home() / "Library" / "Logs" / "garmin-import.cron.log"
    slots = ",".join(h.strip() for h in hours.split(",") if h.strip())

    if not wrapper.exists():
        print(f"# WARNING: {wrapper} does not exist yet", file=sys.stderr)

    print("# Garmin run importer: import new runs, commit, push.")
    print(f"# Log: {Path.home() / 'Library' / 'Logs' / 'garmin-import.log'}")
    print(f"40 {slots} * * * /bin/bash {wrapper} >> {log} 2>&1")

    # This output is meant to be piped. If the reader dies first - `crontab -`
    # refusing to write, say - Python would otherwise dump a BrokenPipeError
    # traceback from the interpreter's final flush, on top of whatever real
    # error the reader already printed.
    try:
        sys.stdout.flush()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        raise SystemExit(1) from None


def main() -> None:
    args = parse_args()

    # Before the credential check: neither of these talks to Garmin.
    if args.sample_map:
        write_sample_map(Path(args.sample_map))
        return

    if args.print_crontab:
        print_crontab(args.cron_hours)
        return

    load_dotenv(config.PATHS.scripts / ".env")
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    if not email or not password:
        raise SystemExit(
            "GARMIN_EMAIL and GARMIN_PASSWORD must be set in environment or scripts/.env"
        )

    # Under cron stdin is /dev/null, so input() would raise a bare EOFError.
    # Both checks: the flag documents the intent, isatty catches a caller who
    # forgot it.
    interactive = sys.stdin.isatty() and not args.non_interactive

    try:
        client = authenticate(email, password, interactive=interactive)

        if args.backfill_maps:
            run_backfill(client, args)
        if args.backfill_photos:
            run_backfill_photos(client, args)
        if not (args.backfill_maps or args.backfill_photos):
            run_import(client, args)
    except NeedsLogin as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(EXIT_NEEDS_LOGIN)
