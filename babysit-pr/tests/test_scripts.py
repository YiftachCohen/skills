"""Tests for babysit-pr/scripts against a fake `gh` and a fake clock.

The fake `gh` answers from a scenario file: each kind of call (pr view,
pr checks, graphql, api path) returns the next response in its list, repeating
the last one. `--jq` / `-q` filters are applied with the real `jq`, so the
scripts' filters are exercised too. `sleep` advances a fake clock that `date`
reads, so multi-minute waits run instantly.
"""
import json
import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
WAIT = os.path.join(SCRIPTS, "wait-for-pr.sh")
FAILED_LOG = os.path.join(SCRIPTS, "failed-log.sh")

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, subprocess, sys

d = os.environ["FAKE_DIR"]
scen = json.load(open(os.path.join(d, "scenario.json")))
args = sys.argv[1:]
with open(os.path.join(d, "calls.log"), "a") as f:
    f.write(json.dumps(args) + "\n")

jq = None
for flag in ("--jq", "-q"):
    if flag in args:
        jq = args[args.index(flag) + 1]

def nxt(kind, seq):
    path = os.path.join(d, "counts.json")
    counts = json.load(open(path)) if os.path.exists(path) else {}
    i = counts.get(kind, 0)
    counts[kind] = i + 1
    json.dump(counts, open(path, "w"))
    return seq[min(i, len(seq) - 1)]

def emit(value):
    if isinstance(value, str) and jq is None:
        sys.stdout.write(value)
        return
    text = value if isinstance(value, str) else json.dumps(value)
    if jq is None:
        print(text)
        return
    out = subprocess.run(["jq", "-r", jq], input=text, capture_output=True, text=True)
    sys.stdout.write(out.stdout)
    sys.exit(out.returncode)

if args[:2] == ["pr", "view"]:
    if "url" in args:
        print(scen["pr_url"])
    else:
        emit(nxt("pr_view", scen["pr_view"]))
elif args[:2] == ["pr", "checks"]:
    resp = nxt("checks", scen["checks"])
    if resp is None:
        sys.stderr.write("no checks reported on the 'x' branch\n")
        sys.exit(1)
    emit(resp)
elif args[:2] == ["api", "graphql"]:
    emit(nxt("graphql", scen["graphql"]))
elif args[0] == "api":
    for key, resp in scen.get("api", {}).items():
        if key in args[1]:
            emit(resp)
            break
    else:
        sys.stderr.write("HTTP 404: not found\n")
        sys.exit(1)
else:
    sys.stderr.write("fake gh: unhandled %r\n" % (args,))
    sys.exit(3)
'''

FAKE_DATE = '#!/bin/sh\ncat "$FAKE_DIR/clock"\n'
FAKE_SLEEP = '#!/bin/sh\nt=$(cat "$FAKE_DIR/clock"); echo $((t + ${1%%s})) > "$FAKE_DIR/clock"\n'

SHA = "a" * 40
URL = "https://github.com/acme/widgets/pull/7"


def pr(sha=SHA, state="OPEN", **extra):
    base = {"state": state, "headRefOid": sha, "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN", "reviewDecision": "", "isDraft": False}
    base.update(extra)
    return base


def check(name, bucket):
    return {"name": name, "bucket": bucket, "state": bucket.upper(), "link": "", "workflow": "ci"}


def reviews(n_comments=0, thread_updated="2026-01-01T00:00:00Z", pending_review=False):
    rs = [{"id": "R1", "state": "COMMENTED", "updatedAt": "2026-01-01T00:00:00Z"}]
    if pending_review:
        rs.append({"id": "R2", "state": "PENDING", "updatedAt": "2026-01-02T00:00:00Z"})
    return {"data": {"repository": {"pullRequest": {
        "comments": {"totalCount": n_comments,
                     "nodes": [{"id": "C%d" % i, "updatedAt": "t"} for i in range(n_comments)]},
        "reviews": {"totalCount": len(rs), "nodes": rs},
        "reviewThreads": {"totalCount": 1, "nodes": [{"id": "T1", "isResolved": False, "comments": {
            "totalCount": 1, "nodes": [{"id": "TC1", "updatedAt": thread_updated}]}}]},
    }}}}


class FakeGhCase(unittest.TestCase):
    def setUp(self):
        if not shutil.which("jq"):
            self.skipTest("jq not installed")
        self.dir = tempfile.mkdtemp()
        self.bin = os.path.join(self.dir, "bin")
        os.mkdir(self.bin)
        for name, body in (("gh", FAKE_GH), ("date", FAKE_DATE), ("sleep", FAKE_SLEEP)):
            p = os.path.join(self.bin, name)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        self.set_clock(1000)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def set_clock(self, t):
        with open(os.path.join(self.dir, "clock"), "w") as f:
            f.write(str(t))

    def clock(self):
        return int(open(os.path.join(self.dir, "clock")).read())

    def scenario(self, **scen):
        scen.setdefault("pr_url", URL)
        for name in ("counts.json", "calls.log"):
            p = os.path.join(self.dir, name)
            if os.path.exists(p):
                os.remove(p)
        with open(os.path.join(self.dir, "scenario.json"), "w") as f:
            json.dump(scen, f)

    def calls(self):
        with open(os.path.join(self.dir, "calls.log")) as f:
            return [json.loads(line) for line in f]

    def run_script(self, script, *args):
        env = dict(os.environ, FAKE_DIR=self.dir, PATH=self.bin + os.pathsep + os.environ["PATH"])
        return subprocess.run(["bash", script] + list(args), capture_output=True, text=True,
                              env=env, cwd=self.dir, timeout=60)


class WaitForPrTest(FakeGhCase):
    def wait(self, *args):
        res = self.run_script(WAIT, "7", "--sha", SHA, *args)
        self.assertEqual(res.returncode, 0, res.stderr)
        first, _, rest = res.stdout.partition("\n")
        self.assertTrue(first.startswith("WAIT_RESULT: "), res.stdout)
        return set(first[len("WAIT_RESULT: "):].split(",")), json.loads(rest)

    def test_settled_when_all_checks_pass(self):
        self.scenario(pr_view=[pr()], checks=[[check("test", "pass"), check("lint", "skipping")]],
                      graphql=[reviews()])
        reasons, out = self.wait()
        self.assertEqual(reasons, {"settled"})
        self.assertEqual(out["pr"]["headRefOid"], SHA)
        self.assertEqual(len(out["checks"]), 2)

    def test_failure_returns_after_settle_window(self):
        self.scenario(pr_view=[pr()], checks=[[check("test", "pending")], [check("test", "fail")]],
                      graphql=[reviews()])
        reasons, out = self.wait("--interval", "60", "--settle", "90")
        self.assertEqual(reasons, {"failing"})
        # first poll pending, second poll fails at t+60, then 90s of settle
        self.assertGreaterEqual(self.clock() - 1000, 150)
        self.assertEqual(out["checks"][0]["bucket"], "fail")

    def test_new_review_while_ci_still_running(self):
        self.scenario(pr_view=[pr()], checks=[[check("test", "pending")]],
                      graphql=[reviews(0), reviews(0), reviews(1)])
        reasons, _ = self.wait("--settle", "0")
        self.assertEqual(reasons, {"new-review"})

    def test_review_and_failure_within_settle_come_back_together(self):
        self.scenario(pr_view=[pr()],
                      checks=[[check("test", "pending")], [check("test", "pending")], [check("test", "fail")]],
                      graphql=[reviews(0), reviews(1)])
        reasons, _ = self.wait("--interval", "30", "--settle", "120")
        self.assertEqual(reasons, {"new-review", "failing"})

    def test_edited_thread_comment_counts_as_new_review(self):
        self.scenario(pr_view=[pr()], checks=[[check("test", "pending")]],
                      graphql=[reviews(thread_updated="t1"), reviews(thread_updated="t2")])
        reasons, _ = self.wait("--settle", "0")
        self.assertEqual(reasons, {"new-review"})

    def test_pending_review_is_not_new_feedback(self):
        self.scenario(pr_view=[pr()], checks=[[check("test", "pending")], [check("test", "pass")]],
                      graphql=[reviews(), reviews(pending_review=True)])
        reasons, _ = self.wait()
        self.assertEqual(reasons, {"settled"})

    def test_closed_or_merged_stops_immediately(self):
        self.scenario(pr_view=[pr(state="MERGED")], checks=[[check("test", "pending")]],
                      graphql=[reviews()])
        reasons, out = self.wait()
        self.assertEqual(reasons, {"closed"})
        self.assertEqual(out["pr"]["state"], "MERGED")

    def test_head_lagging_after_push_is_waited_out(self):
        self.scenario(pr_view=[pr(sha="b" * 40), pr(sha="b" * 40), pr()],
                      checks=[[check("test", "pass")]], graphql=[reviews()])
        reasons, _ = self.wait("--interval", "10")
        self.assertEqual(reasons, {"settled"})
        # checks are only read once the PR head is the pushed commit, so the old
        # commit's results can't be mistaken for this one's
        calls = self.calls()
        views = [i for i, c in enumerate(calls) if c[:2] == ["pr", "view"] and "url" not in c]
        first_check = next(i for i, c in enumerate(calls) if c[:2] == ["pr", "checks"])
        self.assertGreater(first_check, views[2])

    def test_head_moved_by_someone_else(self):
        self.scenario(pr_view=[pr(), pr(sha="c" * 40)], checks=[[check("test", "pending")]],
                      graphql=[reviews()])
        reasons, _ = self.wait()
        self.assertEqual(reasons, {"head-moved"})

    def test_head_never_reaches_sha(self):
        self.scenario(pr_view=[pr(sha="b" * 40)], checks=[[check("test", "pass")]], graphql=[reviews()])
        reasons, _ = self.wait("--register", "120", "--interval", "30")
        self.assertEqual(reasons, {"head-mismatch"})

    def test_no_checks_ever_register(self):
        self.scenario(pr_view=[pr()], checks=[None], graphql=[reviews()])
        reasons, out = self.wait("--register", "120", "--settle", "0")
        self.assertEqual(reasons, {"no-checks"})
        self.assertIsNone(out["checks"])

    def test_timeout_when_nothing_happens(self):
        self.scenario(pr_view=[pr()], checks=[[check("test", "pending")]], graphql=[reviews()])
        reasons, out = self.wait("--timeout", "300")
        self.assertEqual(reasons, {"timeout"})
        self.assertGreaterEqual(out["waited_seconds"], 300)

    def test_review_grace_catches_bot_review_after_green(self):
        self.scenario(pr_view=[pr()], checks=[[check("test", "pass")]],
                      graphql=[reviews(0), reviews(0), reviews(0), reviews(1)])
        reasons, _ = self.wait("--review-grace", "300", "--settle", "0")
        self.assertEqual(reasons, {"new-review"})

    def test_required_flag_is_passed_to_gh(self):
        self.scenario(pr_view=[pr()], checks=[[check("test", "pass")]], graphql=[reviews()])
        self.wait("--required")
        checks_calls = [c for c in self.calls() if c[:2] == ["pr", "checks"]]
        self.assertTrue(checks_calls)
        self.assertTrue(all("--required" in c for c in checks_calls))

    def test_stall_minutes_accumulate_across_waits(self):
        state = os.path.join(self.dir, "state", "7.json")
        self.scenario(pr_view=[pr()], checks=[[check("test", "pending")]], graphql=[reviews()])
        _, first = self.wait("--timeout", "600", "--state", state)
        self.scenario(pr_view=[pr()], checks=[[check("test", "pending")]], graphql=[reviews()])
        _, second = self.wait("--timeout", "600", "--state", state)
        self.assertEqual(first["stall"]["fingerprint"], second["stall"]["fingerprint"])
        self.assertGreaterEqual(second["stall"]["unchanged_minutes"], 10)
        # something changes -> the stall clock restarts
        self.scenario(pr_view=[pr()], checks=[[check("test", "fail")]], graphql=[reviews()])
        _, third = self.wait("--state", state, "--settle", "0")
        self.assertNotEqual(third["stall"]["fingerprint"], second["stall"]["fingerprint"])
        self.assertEqual(third["stall"]["unchanged_minutes"], 0)

    def test_rejects_unknown_arguments(self):
        self.scenario(pr_view=[pr()], checks=[[]], graphql=[reviews()])
        res = self.run_script(WAIT, "7", "--bogus")
        self.assertEqual(res.returncode, 2)


LOG = textwrap.dedent("""\
    2026-01-01T00:00:00.0000000Z ##[group]Run actions/checkout@v4
    2026-01-01T00:00:01.0000000Z checkout noise
    2026-01-01T00:00:02.0000000Z ##[endgroup]
    2026-01-01T00:00:03.0000000Z ##[group]Run npm test
    2026-01-01T00:00:04.0000000Z > jest
    2026-01-01T00:00:05.0000000Z FAIL src/sum.test.js
    2026-01-01T00:00:06.0000000Z   expected 3, received 4
    2026-01-01T00:00:07.0000000Z ##[error]Process completed with exit code 1.
    2026-01-01T00:00:08.0000000Z Post job cleanup.
    2026-01-01T00:00:09.0000000Z cleanup noise
    """)

JOB = {"id": 456, "name": "test (3.12)", "conclusion": "failure", "status": "completed",
       "steps": [{"name": "Checkout", "conclusion": "success"}, {"name": "Run tests", "conclusion": "failure"}]}
ANNOTATIONS = [
    {"path": "src/sum.js", "start_line": 3, "annotation_level": "failure", "message": "expected 3\nreceived 4"},
    {"path": ".github", "start_line": 1, "annotation_level": "notice", "message": "Node 16 is deprecated"},
]


class FailedLogTest(FakeGhCase):
    def test_job_url_prints_failed_step_annotations_and_error(self):
        self.scenario(api={"actions/jobs/456/logs": LOG, "actions/jobs/456": JOB,
                           "check-runs/456/annotations": ANNOTATIONS})
        res = self.run_script(FAILED_LOG, "https://github.com/acme/widgets/actions/runs/123/job/456")
        self.assertEqual(res.returncode, 0, res.stderr)
        out = res.stdout
        self.assertIn("failed step: Run tests", out)
        self.assertIn("src/sum.js:3 [failure] expected 3 received 4", out)
        self.assertNotIn("Node 16 is deprecated", out)
        self.assertIn("##[group]Run npm test", out)
        self.assertIn("expected 3, received 4", out)
        self.assertIn("##[error]Process completed", out)
        self.assertNotIn("checkout noise", out)
        self.assertNotIn("cleanup noise", out)
        self.assertNotIn("2026-01-01T", out)

    def test_run_id_selects_only_failed_jobs(self):
        ok = dict(JOB, id=455, name="lint", conclusion="success")
        self.scenario(api={"actions/runs/123/jobs": {"jobs": [ok, JOB]},
                           "actions/jobs/456/logs": LOG, "check-runs/456/annotations": []})
        res = self.run_script(FAILED_LOG, "123")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("=== job: test (3.12) (456)", res.stdout)
        self.assertNotIn("lint", res.stdout)

    def test_max_bytes_keeps_lines_nearest_the_error(self):
        self.scenario(api={"actions/jobs/456/logs": LOG, "actions/jobs/456": JOB,
                           "check-runs/456/annotations": []})
        res = self.run_script(FAILED_LOG, "https://github.com/acme/widgets/actions/runs/123/job/456",
                              "--max-bytes", "80")
        self.assertIn("earlier lines trimmed", res.stdout)
        self.assertIn("##[error]Process completed", res.stdout)
        self.assertNotIn("> jest", res.stdout)

    def test_no_failed_jobs_yet(self):
        self.scenario(api={"actions/runs/123/jobs": {"jobs": [dict(JOB, conclusion=None, status="in_progress")]}})
        res = self.run_script(FAILED_LOG, "123")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("No failed jobs found for run 123", res.stdout)


if __name__ == "__main__":
    unittest.main()
