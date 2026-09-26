#!/usr/bin/env bash
# Block until something on a PR needs the agent, without spending model turns
# on polling. Watches CI, review activity, and PR state together: a review that
# lands while CI is still running wakes the agent now, not when CI finishes.
#
# Usage: wait-for-pr.sh <pr> [options]
#
#   --required          only count checks GitHub marks as required for this PR
#   --sha <sha>         commit CI should run on (default: local HEAD, i.e. what
#                       you just pushed)
#   --timeout <s>       give up after this long (default: 1500)
#   --interval <s>      seconds between polls (default: 60)
#   --settle <s>        after the first actionable event, keep watching this
#                       long so a review and a CI failure that arrive together
#                       come back as one wake-up (default: 60)
#   --review-grace <s>  after CI settles green, keep watching reviews this long
#                       before returning, for reviewer bots that post after CI
#                       (default: 0)
#   --register <s>      how long to wait for the PR head to reach <sha> and for
#                       checks to register on it (default: 300)
#   --state <file>      babysit-pr state file; the script maintains its
#                       "stall" entry and reports how long nothing has changed
#
# Output: a line "WAIT_RESULT: <reasons>" (comma-separated), then one JSON
# object with the PR state, the checks snapshot, and stall info. Reasons:
#   closed        PR was merged or closed - stop babysitting
#   head-moved    someone else pushed; sync before doing anything
#   head-mismatch the PR head never reached <sha> (push missing or rejected?)
#   no-checks     no checks registered on <sha> (conflict? path filters?)
#   failing       at least one counted check is in the "fail" bucket
#   new-review    comments, reviews, or threads changed since the wait began
#   settled       every counted check finished and none failed
#   timeout       --timeout elapsed with nothing actionable
# Classify from the JSON; the reasons only say why the wait ended.
set -u

usage="usage: wait-for-pr.sh <pr> [--required] [--sha <sha>] [--timeout <s>] [--interval <s>] [--settle <s>] [--review-grace <s>] [--register <s>] [--state <file>]"
pr=${1:?$usage}
shift
req=""
sha=""
limit=1500
interval=60
settle=60
grace=0
register=300
state=""
while [ $# -gt 0 ]; do
  case "$1" in
    --required) req="--required" ;;
    --sha) sha=${2:?--sha needs a value}; shift ;;
    --timeout) limit=${2:?--timeout needs a value}; shift ;;
    --interval) interval=${2:?--interval needs a value}; shift ;;
    --settle) settle=${2:?--settle needs a value}; shift ;;
    --review-grace) grace=${2:?--review-grace needs a value}; shift ;;
    --register) register=${2:?--register needs a value}; shift ;;
    --state) state=${2:?--state needs a value}; shift ;;
    *) echo "$usage" >&2; exit 2 ;;
  esac
  shift
done
command -v jq >/dev/null || { echo "wait-for-pr.sh needs jq" >&2; exit 2; }
[ -n "$sha" ] || sha=$(git rev-parse HEAD)

hash16() {
  if command -v sha256sum >/dev/null; then sha256sum; else shasum -a 256; fi | cut -c1-16
}
now() { date +%s; }

url=$(gh pr view "$pr" --json url -q .url 2>/dev/null)
case "$url" in
  https://*/pull/*) ;;
  *) echo "cannot resolve PR $pr (gh pr view failed)" >&2; exit 2 ;;
esac
path=${url#https://*/}
owner=${path%%/*}; path=${path#*/}
name=${path%%/*}
num=${url##*/}

pr_json() {
  gh pr view "$pr" --json state,headRefOid,mergeable,mergeStateStatus,reviewDecision,isDraft 2>/dev/null
}
checks_json() {
  gh pr checks "$pr" $req --json name,bucket,state,link,workflow 2>/dev/null
}
# Cheap fingerprint of review activity: counts plus latest ids/timestamps of
# comments, submitted reviews, and threads (resolution + last reply). Pending
# (unsubmitted) reviews are excluded - they are not feedback yet.
review_fp() {
  gh api graphql -f query='
query($o:String!,$r:String!,$n:Int!){
  repository(owner:$o,name:$r){ pullRequest(number:$n){
    comments(last:20){ totalCount nodes{ id updatedAt } }
    reviews(last:20){ totalCount nodes{ id state updatedAt } }
    reviewThreads(last:100){ totalCount nodes{ id isResolved
      comments(last:1){ totalCount nodes{ id updatedAt } } } }
  } }
}' -f o="$owner" -f r="$name" -F n="$num" \
    --jq '.data.repository.pullRequest | .reviews = [.reviews.nodes[] | select(.state != "PENDING")]' \
    2>/dev/null | hash16
}
empty_fp=$(printf '' | hash16)

start=$(now)
base_fp=$(review_fp)
events=""
add_event() { case ",$events," in *",$1,"*) ;; *) events="${events:+$events,}$1" ;; esac; }
first_event_at=""
settled_at=""
seen_head=""
pj="{}"
cj=""

while :; do
  t=$(now)
  pj=$(pr_json); [ -n "$pj" ] || pj="{}"
  st=$(jq -r '.state // ""' <<<"$pj")
  head=$(jq -r '.headRefOid // ""' <<<"$pj")

  if [ "$st" = "MERGED" ] || [ "$st" = "CLOSED" ]; then add_event closed; break; fi
  if [ "$head" = "$sha" ]; then
    seen_head=1
  elif [ -n "$head" ] && [ -n "$seen_head" ]; then
    add_event head-moved; break
  elif [ -n "$head" ] && [ $((t - start)) -ge "$register" ]; then
    add_event head-mismatch; break
  fi

  settled=""
  if [ -n "$seen_head" ]; then
    cj=$(checks_json)
    if [ -n "$cj" ]; then
      fail=$(jq '[.[] | select(.bucket == "fail")] | length' <<<"$cj")
      pending=$(jq '[.[] | select(.bucket == "pending")] | length' <<<"$cj")
      [ "$fail" -gt 0 ] && add_event failing
      if [ "$pending" -eq 0 ] && [ "$fail" -eq 0 ]; then
        settled=1
        [ -n "$settled_at" ] || settled_at=$t
      fi
    elif [ $((t - start)) -ge "$register" ]; then
      add_event no-checks
    fi
  fi

  fp=$(review_fp)
  if [ "$base_fp" != "$empty_fp" ] && [ "$fp" != "$empty_fp" ] && [ "$fp" != "$base_fp" ]; then
    add_event new-review
  fi

  if [ -n "$events" ]; then
    [ -n "$first_event_at" ] || first_event_at=$t
    [ $((t - first_event_at)) -ge "$settle" ] && break
  elif [ -n "$settled" ] && [ $((t - settled_at)) -ge "$grace" ]; then
    add_event settled; break
  fi
  if [ $((t - start)) -ge "$limit" ]; then add_event timeout; break; fi

  nap=$interval
  if [ -n "$first_event_at" ]; then
    left=$((settle - (t - first_event_at)))
    [ "$left" -lt "$nap" ] && nap=$left
  fi
  [ "$nap" -gt 0 ] || nap=1
  sleep "$nap"
done

# A successful check snapshot overrides "no-checks" from an earlier poll.
[ -n "$cj" ] || cj=null

# Stall tracking: a fingerprint of everything that would make the agent act.
# If it hasn't changed across waits and passes, the PR is stuck, not slow.
stall=null
if [ -n "$state" ]; then
  sfp=$(jq -cn --argjson pr "$pj" --argjson checks "$cj" --arg rfp "$(review_fp)" \
    '[$pr.headRefOid, $pr.mergeable, $pr.reviewDecision,
      (($checks // []) | map([.name, .bucket]) | sort), $rfp]' | hash16)
  mkdir -p "$(dirname "$state")"
  [ -s "$state" ] || echo '{}' > "$state"
  tn=$(now)
  tmp="$state.tmp.$$"
  if jq --arg fp "$sfp" --argjson t "$tn" \
      '.stall = (if .stall.fingerprint == $fp then .stall else {fingerprint: $fp, since: $t} end)' \
      "$state" > "$tmp"; then
    mv "$tmp" "$state"
    stall=$(jq --argjson t "$tn" '{fingerprint: .stall.fingerprint, unchanged_minutes: ((($t - .stall.since) / 60) | floor)}' "$state")
  else
    rm -f "$tmp"
  fi
fi

echo "WAIT_RESULT: ${events:-timeout}"
jq -n --argjson pr "$pj" --argjson checks "$cj" --argjson stall "$stall" \
  --arg sha "$sha" --argjson waited $(( $(now) - start )) \
  '{expected_sha: $sha, waited_seconds: $waited, pr: $pr, checks: $checks, stall: $stall}'
