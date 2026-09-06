#!/bin/bash
#
# Unattended Garmin import: fetch new runs with their photos, commit each one,
# push to origin/main. Driven by cron twice a day; see --print-crontab on the
# importer for the entry.
#
# Safe to run by hand:
#   scripts/garmin/run_import.sh --dry-run   # import, but never commit or push
#
# Exit codes:
#   0  nothing to do, or imported and pushed
#   3  refused: dirty working copy, extra jj workspace, or origin/main is ahead
#   4  another copy is already running
#   5  Garmin needs an interactive login (MFA)
#   6  a step failed: the importer, zola build, or jj

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG="$HOME/Library/Logs/garmin-import.log"
LOCK="/tmp/garmin-import.lock"
NEEDS_LOGIN="$REPO/scripts/garmin/.needs_login"
REPORT="$REPO/scripts/garmin/.last_import.json"
BUILD_DIR="/tmp/garmin-import-build"
MAX_COMMITS=10

# cron hands us PATH=/usr/bin:/bin. uv, jj, zola, magick and jq all live in
# /opt/homebrew/bin, and jj resolves its own `git` through PATH.
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# There is no ssh-agent under cron. Pin one repo-scoped, passphrase-less deploy
# key and refuse to prompt for anything: BatchMode turns a would-be prompt into
# an immediate failure rather than a job that hangs until the next run.
DEPLOY_KEY="$HOME/.ssh/id_ed25519_jonalmeida_site"
export GIT_SSH_COMMAND="/usr/bin/ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes \
-o IdentityAgent=none -o BatchMode=yes -o StrictHostKeyChecking=yes"

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

mkdir -p "$(dirname "$LOG")"
log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG"; }
notify() {
  command -v terminal-notifier >/dev/null || return 0
  terminal-notifier -title "Garmin import" -message "$1" \
    -group garmin-import >/dev/null 2>&1 || true
}
die() { log "ERROR: $2"; notify "$2"; exit "$1"; }

# Rotate at 1 MB. Two files is plenty of history for a twice-daily job.
if [ -f "$LOG" ] && [ "$(stat -f%z "$LOG")" -gt 1048576 ]; then mv "$LOG" "$LOG.1"; fi

# shlock is PID-aware, so a lock left behind by a killed run is taken over
# rather than honoured forever. This mostly guards against the human running
# the script while cron is running it.
/usr/bin/shlock -f "$LOCK" -p $$ || { log "another run holds $LOCK; exiting"; exit 4; }
trap 'rm -f "$LOCK"' EXIT

cd "$REPO"
log "=== start (dry_run=$DRY_RUN) ==="

# --- refuse to touch a working copy that is not ours --------------------------

workspaces=$(jj workspace list | wc -l | tr -d ' ')
[ "$workspaces" = "1" ] || die 3 "jj shows $workspaces workspaces; refusing to commit"

[ "$(jj log -r @ -T empty --no-graph)" = "true" ] \
  || die 3 "the working copy has changes; refusing to import on top of them"

if [ "$DRY_RUN" = "0" ] && [ ! -f "$DEPLOY_KEY" ]; then
  die 3 "no deploy key at $DEPLOY_KEY; see scripts/garmin/README.md"
fi

# --- wait for the network, then check the remote ------------------------------

# cron can fire before Wi-Fi is up after a wake.
for _ in 1 2 3 4 5 6; do
  /usr/bin/nc -z -G 3 connect.garmin.com 443 >/dev/null 2>&1 && break
  sleep 10
done

jj git fetch --remote origin --quiet || die 6 "jj git fetch failed"
[ -z "$(jj log -r 'main@origin ~ ::main' -T '"x"' --no-graph)" ] \
  || die 3 "origin/main is ahead of local main; sort it out by hand"

# --- import, one activity per commit -----------------------------------------

commits=0
for _ in $(seq 1 "$MAX_COMMITS"); do
  set +e
  uv run scripts/garmin/import_garmin_runs.py \
      --non-interactive --max-new 1 --report "$REPORT" >>"$LOG" 2>&1
  rc=$?
  set -e

  if [ "$rc" = "2" ]; then
    : >"$NEEDS_LOGIN"
    die 5 "Garmin needs an interactive login - run the importer in a terminal"
  fi
  [ "$rc" = "0" ] || die 6 "the importer exited $rc (see $LOG)"
  rm -f "$NEEDS_LOGIN"

  retract=$(jq -r '.retract_candidates | length' "$REPORT")
  [ "$retract" = "0" ] \
    || notify "$retract published run(s) now fail the filter - review them"

  new=$(jq -r '.imported_count' "$REPORT")
  if [ "$new" = "0" ]; then log "nothing new"; break; fi

  date=$(jq -r '.imported[0].date' "$REPORT")
  changed=$(jj diff -r @ --summary)
  [ -n "$changed" ] || die 6 "the importer reported $date but the working copy is empty"
  log "changed for $date:"; printf '%s\n' "$changed" >>"$LOG"

  if [ "$DRY_RUN" = "1" ]; then
    log "dry run: would commit 'Run: $date.' - leaving the changes in @"
    break
  fi

  jj commit -m "Run: $date." || die 6 "jj commit failed"
  # Not `jj tug`: after jj commit, @ is a fresh empty undescribed commit and
  # the push would be refused. The commit we want is @-.
  jj bookmark set main -r @- || die 6 "jj bookmark set main failed"
  commits=$((commits + 1))
  log "committed Run: $date."
done

if [ "$commits" = "0" ]; then log "=== done, nothing committed ==="; exit 0; fi

# --- never push a site that does not build -----------------------------------

# Into /tmp, so a local `zola serve` watching public/ is left alone.
zola build --output-dir "$BUILD_DIR" --force >>"$LOG" 2>&1 \
  || die 6 "zola build failed; $commits commit(s) are local and NOT pushed"

jj git push --bookmark main --quiet || die 6 "jj git push failed"
log "pushed main ($commits commit(s))"
notify "pushed $commits new run(s)"
log "=== done ==="
