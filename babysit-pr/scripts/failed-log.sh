#!/usr/bin/env bash
# Print a compact failure excerpt for failed GitHub Actions jobs: the failed
# step's output around the first error, the error lines, and the check-run
# annotations (file:line). Works while the workflow run is still in progress,
# as soon as the failed job itself has finished - unlike `gh run view
# --log-failed`, which returns nothing until the whole run completes.
#
# Usage: failed-log.sh <run-id | run URL | job URL> [--max-bytes <n>]
#
#   A check's `link` from `gh pr checks --json link` is a job URL
#   (.../actions/runs/<run>/job/<job>) and selects just that job. A run id or
#   run URL selects every failed job in the run.
#   --max-bytes  cap on the log excerpt per job (default: 4000)
#
# Run it from inside the repository (gh resolves {owner}/{repo} from it).
set -u

usage="usage: failed-log.sh <run-id | run URL | job URL> [--max-bytes <n>]"
target=${1:?$usage}
shift
max=4000
while [ $# -gt 0 ]; do
  case "$1" in
    --max-bytes) max=${2:?--max-bytes needs a value}; shift ;;
    *) echo "$usage" >&2; exit 2 ;;
  esac
  shift
done

run=""
job=""
case "$target" in
  */job/*) job=${target##*/job/}; job=${job%%[!0-9]*}; run=${target##*/runs/}; run=${run%%[!0-9]*} ;;
  */runs/*) run=${target##*/runs/}; run=${run%%[!0-9]*} ;;
  *[!0-9]*|"") echo "$usage" >&2; exit 2 ;;
  *) run=$target ;;
esac

# id <TAB> name <TAB> conclusion <TAB> failed step names
if [ -n "$job" ]; then
  jobs=$(gh api "repos/{owner}/{repo}/actions/jobs/$job" \
    --jq '[.id, .name, (.conclusion // .status), ([.steps[]? | select(.conclusion == "failure") | .name] | join("; "))] | @tsv')
else
  jobs=$(gh api "repos/{owner}/{repo}/actions/runs/$run/jobs?per_page=100" \
    --jq '.jobs[] | select(.conclusion == "failure" or .conclusion == "timed_out")
          | [.id, .name, .conclusion, ([.steps[]? | select(.conclusion == "failure") | .name] | join("; "))] | @tsv')
fi
if [ -z "$jobs" ]; then
  if [ -n "$job" ]; then what="job $job"; else what="run $run"; fi
  echo "No failed jobs found for $what (still running, or failed before any job started)."
  exit 0
fi

while IFS="$(printf '\t')" read -r id jname concl steps; do
  [ -n "$id" ] || continue
  echo "=== job: $jname ($id) - $concl${steps:+ - failed step: $steps}"

  ann=$(gh api "repos/{owner}/{repo}/check-runs/$id/annotations" \
    --jq '.[] | select(.annotation_level != "notice") | "\(.path):\(.start_line) [\(.annotation_level)] \(.message | gsub("\n"; " "))"' \
    2>/dev/null | head -20)
  if [ -n "$ann" ]; then
    echo "--- annotations"
    echo "$ann"
  fi

  echo "--- log excerpt"
  gh api "repos/{owner}/{repo}/actions/jobs/$id/logs" 2>/dev/null | awk -v max="$max" '
    { sub(/\r$/, ""); sub(/^[0-9][0-9-]*T[0-9:.]+Z /, ""); line[NR] = $0 }
    /##\[group\]/ { lastg = NR }
    /##\[error\]/ { if (!e) { e = NR; s = lastg } errs[++ne] = NR }
    /Post job cleanup/ && !cleanup { cleanup = NR }
    END {
      if (NR == 0) { print "(log not available yet)"; exit }
      if (!e) {                    # no error marker: show the tail before cleanup
        last = cleanup ? cleanup - 1 : NR
        first = last - 80 < 1 ? 1 : last - 80
      } else {
        first = s ? s : e - 60
        if (first < 1) first = 1
        last = e + 15
        if (cleanup && last >= cleanup) last = cleanup - 1
        if (last > NR) last = NR
      }
      # Drop lines from the front until the excerpt fits in max bytes, so the
      # lines nearest the error survive.
      bytes = 0
      for (i = first; i <= last; i++) bytes += length(line[i]) + 1
      while (bytes > max && first < last) { bytes -= length(line[first]) + 1; first++ }
      if (first > 1) print "[... " first - 1 " earlier lines trimmed]"
      for (i = first; i <= last; i++) if (line[i] !~ /##\[endgroup\]/) print line[i]
      extra = 0
      for (k = 1; k <= ne; k++) if (errs[k] > last && extra < 10) { if (!extra) print "--- later errors"; print line[errs[k]]; extra++ }
    }'
  echo
done <<EOF
$jobs
EOF
