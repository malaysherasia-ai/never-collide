import datetime as dt
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude" / "never-collide" / "ncl"
LOADER = importlib.machinery.SourceFileLoader("ncl", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
ncl = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(ncl)


def run(command, cwd, env=None):
    return subprocess.run(command, cwd=str(cwd), env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class PatternOverlapTests(unittest.TestCase):
    def test_equal_and_nested_globs_overlap(self):
        self.assertTrue(ncl.patterns_overlap("src/app/**", "src/app/page.tsx"))
        self.assertTrue(ncl.patterns_overlap("src/app/page.tsx", "src/app/**"))

    def test_disjoint_literal_prefixes_do_not_overlap(self):
        self.assertFalse(ncl.patterns_overlap("src/lib/**", "src/components/**"))
        self.assertFalse(ncl.patterns_overlap("src/lib/db.ts", "src/lib2/db.ts"))

    def test_root_globs_are_treated_conservatively(self):
        self.assertTrue(ncl.patterns_overlap("**/*.py", "tests/**"))
        self.assertTrue(ncl.patterns_overlap("**", "docs/index.md"))

    def test_backslashes_are_normalised(self):
        self.assertTrue(ncl.patterns_overlap("src\\app\\**", "src/app/page.tsx"))


class ClaimExpiryTests(unittest.TestCase):
    def test_claim_expires_after_ttl(self):
        now = dt.datetime(2026, 9, 27, 12, tzinfo=dt.timezone.utc)
        record = {"status": "claimed", "ts": "2026-09-27T07:00:00Z", "ttl_h": 4}
        self.assertFalse(ncl.is_active(record, now))
        self.assertTrue(ncl.is_expired(record, now))

    def test_claim_is_active_inside_ttl(self):
        now = dt.datetime(2026, 9, 27, 12, tzinfo=dt.timezone.utc)
        record = {"status": "in_progress", "ts": "2026-09-27T10:00:00Z", "ttl_h": 4}
        self.assertTrue(ncl.is_active(record, now))

    def test_released_claim_is_inactive(self):
        record = {"status": "released", "ts": "2026-09-27T12:00:00Z", "ttl_h": 4}
        self.assertFalse(ncl.is_active(record))
        self.assertFalse(ncl.is_expired(record))

    def test_messages_do_not_change_task_state(self):
        records = [
            {"task": "T", "agent": "claude", "status": "claimed", "ts": "2026-09-27T12:00:00Z"},
            {"kind": "message", "task": "T", "agent": "antigravity", "status": "requested",
             "ts": "2026-09-27T12:05:00Z"},
        ]
        self.assertEqual(ncl.latest_states(records)["T"]["agent"], "claude")


class RepoFixture(unittest.TestCase):
    """A clone with a local bare origin, so ledger pushes are real."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp_dir.name)
        self.remote = self.root / "origin.git"
        self.repo = self.root / "repo"
        run(["git", "init", "--bare", "-q", str(self.remote)], self.root)
        run(["git", "clone", "-q", str(self.remote), str(self.repo)], self.root)
        self.git("config", "user.name", "ncl tests")
        self.git("config", "user.email", "ncl-tests@example.invalid")
        self.git("checkout", "-q", "-b", "main")

    def tearDown(self):
        self.temp_dir.cleanup()

    def git(self, *args):
        result = run(["git"] + list(args), self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def ncl(self, agent, *args, expect=0):
        env = os.environ.copy()
        env["AGENT_NAME"] = agent
        env.pop("AGENT_TOOL", None)
        result = run([sys.executable, str(SCRIPT)] + list(args), self.repo, env)
        if expect is not None:
            self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return result

    def ledger(self):
        show = run(["git", "show", "refs/remotes/origin/agents/ledger:ledger.jsonl"], self.repo)
        return [json.loads(line) for line in show.stdout.splitlines() if line.strip()]


class LedgerIntegrationTests(RepoFixture):
    def test_whoami_requires_agent_name(self):
        env = os.environ.copy()
        env.pop("AGENT_NAME", None)
        result = run([sys.executable, str(SCRIPT), "whoami"], self.repo, env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("AGENT_NAME is unset", result.stderr)

    def test_status_before_any_claim(self):
        result = self.ncl("claude", "status")
        self.assertIn("No active claims", result.stdout)

    def test_claim_persists_and_overlapping_agent_is_refused(self):
        self.ncl("claude", "claim", "--task", "TASK-1", "--paths", "src/app/**",
                 "--intent", "Build page")
        self.ncl("claude", "start", "--task", "TASK-1")

        conflict = self.ncl("antigravity", "claim", "--task", "TASK-2", "--paths",
                            "src/app/page.tsx", "--intent", "Restyle page", expect=1)
        self.assertIn("claim refused", conflict.stderr)
        self.assertIn("TASK-1 held by claude", conflict.stderr)

        disjoint = self.ncl("antigravity", "claim", "--task", "TASK-3", "--paths",
                            "src/components/**", "--intent", "Buttons")
        self.assertIn("Claimed TASK-3", disjoint.stdout)

        self.assertEqual([entry["status"] for entry in self.ledger()],
                         ["claimed", "in_progress", "claimed"])

    def test_full_lifecycle_keeps_intent_and_frees_paths(self):
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/lib/**",
                 "--intent", "Add db layer")
        self.ncl("claude", "start", "--task", "T-1")
        self.ncl("claude", "note", "--task", "T-1", "Schema changed: users.email is unique")
        self.ncl("claude", "done", "--task", "T-1", "--pr", "118")
        self.ncl("claude", "tested", "--task", "T-1", "--evidence", "CI green",
                 "--preview", "https://preview.example/118")
        status = self.ncl("claude", "status").stdout
        self.assertIn("Add db layer", status)
        self.assertIn("PR 118", status)
        self.assertIn("preview https://preview.example/118", status)

        blocked = self.ncl("codex", "claim", "--task", "T-2", "--paths", "src/lib/x.ts",
                           "--intent", "Tweak", expect=1)
        self.assertIn("claim refused", blocked.stderr)

        self.ncl("claude", "release", "--task", "T-1")
        self.ncl("codex", "claim", "--task", "T-2", "--paths", "src/lib/x.ts",
                 "--intent", "Tweak")
        statuses = [entry["status"] for entry in self.ledger()]
        self.assertEqual(statuses, ["claimed", "in_progress", "in_progress", "done",
                                    "tested", "released", "claimed"])

    def test_other_agent_cannot_transition_a_held_task(self):
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/lib/**",
                 "--intent", "Add db layer")
        result = self.ncl("antigravity", "done", "--task", "T-1", expect=1)
        self.assertIn("held by claude", result.stderr)
        result = self.ncl("antigravity", "done", "--task", "NOPE", expect=1)
        self.assertIn("no active claim", result.stderr)

    def test_refused_agent_can_request_without_changing_state(self):
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/app/**",
                 "--intent", "Build page")
        result = self.ncl("antigravity", "handoff", "--task", "T-1", "--to", "claude",
                          "--paths", "src/app/hero.tsx", "-m", "Need the hero file for styling")
        self.assertIn("Requested T-1 from claude", result.stdout)

        status = self.ncl("claude", "status").stdout
        self.assertIn("claude       claimed", status)
        self.assertIn("antigravity -> claude", status)
        self.assertIn("Need the hero file", status)
        self.assertEqual(self.ledger()[-1]["kind"], "message")

    def test_holder_handoff_releases_whole_claim(self):
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/app/**",
                 "--intent", "Build page")
        self.ncl("claude", "handoff", "--task", "T-1", "--to", "antigravity",
                 "-m", "Logic is in; styling is yours")
        self.assertEqual(self.ledger()[-1]["status"], "handoff")
        self.ncl("antigravity", "claim", "--task", "T-1-UI", "--paths", "src/app/**",
                 "--intent", "Style page")

    def test_holder_handoff_of_some_paths_keeps_the_rest(self):
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/lib/**",
                 "src/components/Hero.tsx", "--intent", "Hero logic")
        result = self.ncl("claude", "handoff", "--task", "T-1", "--to", "antigravity",
                          "--paths", "src/components/Hero.tsx", "-m", "Hero props are final")
        self.assertIn("still holds src/lib/**", result.stdout)
        self.assertEqual(self.ledger()[-1]["paths"], ["src/lib/**"])
        self.ncl("antigravity", "claim", "--task", "T-2", "--paths",
                 "src/components/Hero.tsx", "--intent", "Style hero")

    def test_log_lists_events_and_filters(self):
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "a/**", "--intent", "A")
        self.ncl("antigravity", "claim", "--task", "T-2", "--paths", "b/**", "--intent", "B")
        self.ncl("claude", "note", "--task", "T-1", "halfway")
        everything = self.ncl("claude", "log").stdout.splitlines()
        self.assertEqual(len(everything), 3)
        self.assertIn("halfway", everything[-1])
        only_t2 = self.ncl("claude", "log", "--task", "T-2").stdout.splitlines()
        self.assertEqual(len(only_t2), 1)
        last = self.ncl("claude", "log", "-n", "1").stdout.splitlines()
        self.assertEqual(len(last), 1)


class InstallerTests(unittest.TestCase):
    def test_installer_is_idempotent_and_keeps_existing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp) / "site"
            target.mkdir()
            (target / "CLAUDE.md").write_text("# Existing notes\n", encoding="utf-8")
            (target / "AGENTS.md").write_text("# Keep me\n", encoding="utf-8")
            for _ in range(2):
                result = run(["bash", str(ROOT / "install.sh"), str(target)], ROOT)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((target / ".claude" / "never-collide" / "ncl").exists())
            self.assertTrue((target / ".agents" / "OWNERSHIP.md").exists())
            self.assertTrue((target / ".agents" / "PROTOCOL.md").exists())
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), "# Keep me\n")
            claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertTrue(claude.startswith("# Existing notes"))
            self.assertEqual(claude.count("<!-- never-collide:start -->"), 1)
            ignore = (target / ".gitignore").read_text(encoding="utf-8")
            self.assertEqual(ignore.count(".ncl/"), 1)


if __name__ == "__main__":
    unittest.main()
