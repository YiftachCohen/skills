#!/usr/bin/env bash
# Atlas repo survey — the whole coverage checklist as one command.
#
# Run this ONCE, before anything else. It produces the measured file count that
# picks the approach, the largest-files list, and every category the inventory
# has to account for. Output is compact on purpose: it is meant to be read into
# context once and pasted into each subagent prompt, so no agent pays to
# re-derive it. Nothing here costs model tokens.
#
#   bash scripts/survey.sh /abs/repo [/abs/out.txt]
#
# Prints to stdout AND saves a copy (default `<repo>/.atlas/survey.txt`),
# creating `.atlas/` if needed. On a first run it never exists, and a
# `> .atlas/survey.txt` redirect would fail in the shell before this script was
# ever reached. A read-only repo degrades to stdout only.
#
# Portable bash + git/grep/find only. No network.
set -uo pipefail

REPO="${1:-.}"
cd "$REPO" || { echo "survey: cannot cd to $REPO" >&2; exit 1; }
OUT="${2:-$PWD/.atlas/survey.txt}"
if mkdir -p "$(dirname "$OUT")" 2>/dev/null && : >"$OUT" 2>/dev/null; then
  exec > >(tee "$OUT")
else
  echo "survey: cannot write $OUT — stdout only" >&2
fi

SRC_RE='\.(ts|tsx|js|jsx|mjs|cjs|py|go|rb|rs|java|swift|kt|kts|m|mm|cs|php|scala|ex|exs)$'
# Directory conventions AND the per-file ones — `_test.go`, `test_x.py`, `x_spec.rb`.
# Leaving the per-file half out doubles the measured size of any Go or Python
# repo and floods the largest-files list with test files.
TEST_RE='(^|/)(tests?|__tests__|spec|specs|fixtures|testdata|locales|vendor|node_modules|dist|build)/|(^|/)test_[^/]*$|_test\.|_spec\.|\.(test|spec)\.'

# `git ls-files` alone is the INDEX, not the working tree: it omits untracked new
# files and still lists files deleted from disk. Mapping either way is mapping
# stale code. --others --exclude-standard adds untracked while honouring
# .gitignore; the existence filter drops the deletions.
if git rev-parse --git-dir >/dev/null 2>&1; then
  list() {
    git ls-files --cached --others --exclude-standard \
      | grep -v '^\.atlas/' \
      | while IFS= read -r f; do [ -e "$f" ] && printf '%s\n' "$f"; done
  }
else
  # .atlas is our own output — scanning it makes each run ingest the last one.
  list() { find . -type d \( -name node_modules -o -name .venv -o -name vendor \
      -o -name dist -o -name build -o -name .next -o -name .git -o -name .atlas \) -prune -o \
      -type f -print | sed 's|^\./||'; }
fi

sect() { printf '\n== %s ==\n' "$1"; }

# grep over the tracked/pruned file list, never `grep -r .` — recursing from the
# repo root walks node_modules and turns a 3-second survey into a hang.
ALL=$(list)
# `head -N` caps lines, not bytes — one match inside a committed minified bundle
# is a single 500KB line, and a 16KB survey became 89KB that way. Cap the line.
scan() { printf '%s\n' "$ALL" | tr '\n' '\0' | xargs -0 grep -I "$@" 2>/dev/null | cut -c1-200; }

printf '# atlas survey: %s\n' "$(pwd)"

sect "SCALE (the number that picks the approach: <20 read-all / 20-500 command-first / 500+ large-repos.md)"
SRC=$(list | grep -E "$SRC_RE" | grep -vE "$TEST_RE" || true)
printf 'real source files: %s\n' "$(printf '%s\n' "$SRC" | grep -c . || true)"
printf '%s\n' "$SRC" | sed -n 's/.*\.\([A-Za-z]*\)$/\1/p' | sort | uniq -c | sort -rn | head -12

sect "LARGEST SOURCE FILES (walk down until <300 lines or the shape repeats)"
printf '%s\n' "$SRC" | tr '\n' '\0' | xargs -0 wc -l 2>/dev/null | sort -rn | sed -n '2,31p'

sect "TREE (depth 2)"
list | awk -F/ 'NF>1{print $1"/"$2; next}{print}' | sort -u | head -60

sect "MANIFESTS (nested ones included — a monorepo keeps them under apps/* and packages/*)"
MANIFEST_RE='(^|/)(package\.json|pyproject\.toml|go\.mod|Cargo\.toml|Gemfile|pom\.xml|build\.gradle(\.kts)?|composer\.json|Package\.swift|requirements\.txt|setup\.py|deno\.json)$'
printf '%s\n' "$ALL" | grep -E "$MANIFEST_RE" | grep -vE '(^|/)(node_modules|vendor|dist|build|\.venv)/' \
  | sort | head -40
for m in go.mod package.json pyproject.toml Cargo.toml; do
  [ -f "$m" ] && { printf -- '--- %s ---\n' "$m"; head -60 "$m"; }
done

sect "ENV VARS (behaviour the map may draw)"
# Node/Vite/Deno, Python (note the lowercase os.getenv, the most common of all),
# Go, Ruby, PHP, Java/Kotlin, C#, Rust. Adding a language means adding it HERE,
# not running a one-off grep — see references/coverage-checklist.md.
scan -hoE "(process\.env\.[A-Z_0-9]+|process\.env\[['\"][A-Z_0-9]+|import\.meta\.env\.[A-Z_0-9]+|Deno\.env\.get\(['\"][A-Z_0-9]+|os\.environ(\.get)?\(?\[?['\"][A-Z_0-9]+|os\.getenv\(['\"][A-Z_0-9]+|os\.Getenv\(\"[A-Z_0-9]+\"|os\.LookupEnv\(\"[A-Z_0-9]+\"|ENV(\[|\.fetch\()['\"][A-Z_0-9]+|getenv\(['\"][A-Z_0-9]+|\\\$_ENV\[['\"][A-Z_0-9]+|System\.getenv\(\"[A-Z_0-9]+\"|Environment\.GetEnvironmentVariable\(\"[A-Z_0-9]+\"|std::env::var\(\"[A-Z_0-9]+\")" \
  | grep -oE '[A-Z][A-Z_0-9]{2,}' | sort | uniq -c | sort -rn | head -40
[ -f .env.example ] && { printf -- '--- .env.example ---\n'; head -30 .env.example; }

sect "SCHEDULED WORK — CI schedules AND queue/job code (a repo with no cron node has to prove it)"
grep -rnE 'schedule:|cron|@daily|@hourly|setInterval|celery|APScheduler|sidekiq|\.delay\(|apply_async|BullMQ|Queue\(' \
  .github/ .gitlab-ci.yml vercel.json app.yaml Procfile 2>/dev/null | head -20
scan -lE 'celery|\.delay\(|apply_async|sidekiq|bullmq|new Worker\(|@task|@shared_task' \
  | grep -vE "$TEST_RE" | head -20

sect "ENTRY POINTS"
list | grep -E '(^|/)(routes?|api|pages|app|cmd|handlers|controllers|functions|lambdas)/' | head -40
list | grep -E '(^|/)(main|index|server|cli|__main__)\.[a-z]+$' | head -20

sect "SCHEMAS / MIGRATIONS"
list | grep -E 'schema|migration|models?\.|\.sql$|\.prisma$' | head -25

sect "EXIT CODES (does the success branch return non-zero?)"
scan -nE 'sys\.exit\(|os\.Exit\(|process\.exit\(|SystemExit|[Ee]xitCode' | grep -vE "$TEST_RE" | head -20
# Return-based failure: a main() that returns a code someone else passes to exit.
# Noisier than the calls above, so it is capped and labelled rather than merged in.
printf -- '--- return-based (noisy; confirm it reaches an exit) ---\n'
scan -nE '\breturn +[1-9][0-9]*\b' | grep -vE "$TEST_RE" | head -10

sect "AI LAYER (empty is a finding, not a gap)"
# Providers, SDK call shapes, agent frameworks and MCP. Absence here is a
# finding to state, not a gap to leave silent.
scan -nE '@ai-sdk|anthropic|openai|AzureOpenAI|generativeai|@google/genai|vertexai|mistralai|cohere-ai|import cohere|from cohere|ollama|groq|replicate\\.com|replicate-python|huggingface|together-ai|bedrock|InvokeModel|litellm|langchain|langgraph|llamaindex|semantic-kernel|generateText|streamText|generateObject|chat\.completions|messages\.create|tool\(\{|@mcp\.tool|modelcontextprotocol|claude-[0-9a-z]|gpt-[0-9]' \
  | grep -vE "$TEST_RE" | head -25

sect "DEV-TIME AI CONFIG"
for f in .mcp.json CLAUDE.md AGENTS.md .cursorrules .claude .github/copilot-instructions.md; do
  [ -e "$f" ] && printf '%s\n' "$f"
done

sect "CI WORKFLOWS"
ls .github/workflows/ 2>/dev/null

printf '\n# end survey\n'
