#!/usr/bin/env bash
# Block until a PR's checks settle, without spending model turns on polling.
#
# Usage: wait-for-checks.sh <pr> [--required] [--sha <sha>] [--timeout <seconds>] [--interval <seconds>]
#
#   --required   only wait on checks GitHub marks as required for this PR
#   --sha        commit CI should run on (default: local HEAD, i.e. what you pushed)
#   --timeout    ceiling for the watch phase in seconds (default: 1500)
#   --interval   seconds between polls in the watch phase (default: 60)
#
# Prints one line "WAIT_RESULT: <result>" and then a JSON snapshot of the checks.
# Results: settled, failing, pending (timed out), no-checks (none registered
# for the SHA within ~5 min), head-mismatch (PR head is not the expected SHA).
# Classify from the snapshot; the result line only says why the wait ended.
set -u

pr=${1:?usage: wait-for-checks.sh <pr> [--required] [--sha <sha>] [--timeout <seconds>] [--interval <seconds>]}
shift
req=""
sha=""
limit=1500
interval=60
while [ $# -gt 0 ]; do
  case "$1" in
    --required) req="--required" ;;
    --sha) sha=${2:?--sha needs a value}; shift ;;
    --timeout) limit=${2:?--timeout needs a value}; shift ;;
    --interval) interval=${2:?--interval needs a value}; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
[ -n "$sha" ] || sha=$(git rev-parse HEAD)

snapshot() {
  gh pr checks "$pr" $req --json name,bucket,state,link,workflow 2>&1
}

# 1) Right after a push, GitHub needs a moment to move the PR head and attach
#    checks. `gh pr checks` errors with "no checks reported" (or shows a partial
#    set) until then, and a watcher started too early exits on a state that
#    isn't real yet. Give it up to ~5 minutes.
registered=""
head=""
for _ in $(seq 1 30); do
  head=$(gh pr view "$pr" --json headRefOid -q .headRefOid 2>/dev/null)
  if [ "$head" = "$sha" ] && gh pr checks "$pr" $req --json name >/dev/null 2>&1; then
    registered=1
    break
  fi
  sleep 10
done
if [ -z "$registered" ]; then
  if [ "$head" != "$sha" ]; then
    echo "WAIT_RESULT: head-mismatch (PR head ${head:-unknown}, expected $sha)"
  else
    echo "WAIT_RESULT: no-checks"
  fi
  snapshot
  exit 0
fi

# 2) gh does the polling: returns when every check settles, or on the first
#    failure with --fail-fast. Exit 0 = all passed, 8 = still pending.
timeout "$limit" gh pr checks "$pr" $req --watch --fail-fast --interval "$interval" >/dev/null 2>&1
rc=$?
case "$rc" in
  0) echo "WAIT_RESULT: settled" ;;
  124|8) echo "WAIT_RESULT: pending" ;;
  *) echo "WAIT_RESULT: failing" ;;
esac

# 3) One compact snapshot for the model. `bucket` is pass/fail/pending/skipping/
#    cancel; gh maps FAILURE, ERROR, TIMED_OUT and ACTION_REQUIRED to "fail".
snapshot
