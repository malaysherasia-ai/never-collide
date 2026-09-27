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


def run(command, cwd, env=None, stdin=None):
    return subprocess.run(command, cwd=str(cwd), env=env, text=True, input=stdin,
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

    def ncl(self, agent, *args, expect=0, stdin=None):
        env = os.environ.copy()
        env.pop("AGENT_TOOL", None)
        env.pop("AGENT_NAME", None)
        if agent:
            env["AGENT_NAME"] = agent
        result = run([sys.executable, str(SCRIPT)] + list(args), self.repo, env, stdin)
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


class PathMatchTests(unittest.TestCase):
    def test_double_star_spans_directories(self):
        self.assertTrue(ncl.path_matches("src/app/**", "src/app/a/b/page.tsx"))
        self.assertTrue(ncl.path_matches("src/app/**/page.tsx", "src/app/page.tsx"))
        self.assertTrue(ncl.path_matches("src/app/**/page.tsx", "src/app/x/y/page.tsx"))
        self.assertTrue(ncl.path_matches("**/*.py", "tests/test_ncl.py"))
        self.assertTrue(ncl.path_matches("**/*.py", "setup.py"))
        self.assertTrue(ncl.path_matches("**", "anything/at/all"))

    def test_single_star_stays_in_one_segment(self):
        self.assertTrue(ncl.path_matches("src/app/*.tsx", "src/app/page.tsx"))
        self.assertFalse(ncl.path_matches("src/app/*.tsx", "src/app/x/page.tsx"))
        self.assertFalse(ncl.path_matches("src/lib/**", "src/library/db.ts"))

    def test_literal_pattern_covers_the_subtree(self):
        self.assertTrue(ncl.path_matches("src/lib", "src/lib/db.ts"))
        self.assertTrue(ncl.path_matches("src/lib/db.ts", "src/lib/db.ts"))
        self.assertFalse(ncl.path_matches("src/lib", "src/lib2/db.ts"))

    def test_relative_to_root(self):
        root = "C:/work/site" if os.name == "nt" else "/work/site"
        self.assertEqual(ncl.relative_to_root(root + "/src/app/page.tsx", root), "src/app/page.tsx")
        self.assertEqual(ncl.relative_to_root("src\\app\\page.tsx", root), "src/app/page.tsx")
        self.assertIsNone(ncl.relative_to_root(root + "-other/x.ts", root))
        self.assertIsNone(ncl.relative_to_root("/elsewhere/x.ts", root))

    def test_payload_paths_for_each_agent_shape(self):
        claude = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "/r/a.ts"}})
        antigravity = json.dumps({"toolCall": {"args": {"TargetFile": "/r/b.ts", "Cwd": "/r"}}})
        copilot = json.dumps({"toolName": "edit", "toolArgs": {"path": "/r/c.ts"}})
        self.assertEqual(ncl.payload_paths(claude), ["/r/a.ts"])
        self.assertEqual(ncl.payload_paths("\ufeff" + antigravity), ["/r/b.ts"])
        self.assertEqual(ncl.payload_paths(copilot), ["/r/c.ts"])
        self.assertEqual(ncl.payload_paths("not json"), [])
        self.assertEqual(ncl.payload_paths(json.dumps({"tool_input": {"command": "ls"}})), [])


class CheckTests(RepoFixture):
    def payload(self, relative):
        return json.dumps({"tool_name": "Write",
                           "tool_input": {"file_path": str(self.repo / relative)}})

    def test_check_reports_unclaimed_then_covered(self):
        result = self.ncl("claude", "check", "src/app/page.tsx", expect=2)
        self.assertIn("src/app/page.tsx is not claimed by claude", result.stdout)
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/app/**", "--intent", "x")
        self.ncl("claude", "check", "src/app/page.tsx", "src/app/x/y.tsx")
        held = self.ncl("antigravity", "check", "src/app/page.tsx", expect=2)
        self.assertIn("is held by claude (T-1)", held.stdout)

    def test_check_without_agent_name(self):
        result = self.ncl(None, "check", "src/app/page.tsx", expect=2)
        self.assertIn("AGENT_NAME is unset", result.stdout)

    def test_hook_modes(self):
        payload = self.payload("src/app/page.tsx")
        asked = self.ncl("claude", "check", "--hook", "claude", "--payload", stdin=payload)
        decision = json.loads(asked.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "ask")
        self.assertIn("not claimed by claude", decision["permissionDecisionReason"])

        self.ncl("claude", "enforce", "deny")
        denied = self.ncl("claude", "check", "--hook", "claude", "--payload", stdin=payload)
        self.assertEqual(json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"],
                         "deny")

        self.ncl("claude", "enforce", "off")
        quiet = self.ncl("claude", "check", "--hook", "claude", "--payload", stdin=payload)
        self.assertEqual(quiet.stdout.strip(), "")
        self.assertEqual(self.ncl("claude", "enforce").stdout.strip(), "off")

        self.ncl("claude", "enforce", "warn")
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/app/**", "--intent", "x")
        allowed = self.ncl("claude", "check", "--hook", "claude", "--payload", stdin=payload)
        self.assertEqual(allowed.stdout.strip(), "")

    def test_hook_dialects(self):
        payload = self.payload("src/app/page.tsx")
        gemini = json.loads(self.ncl("claude", "check", "--hook", "gemini", "--payload",
                                     stdin=payload).stdout)
        self.assertIn("systemMessage", gemini)
        antigravity = json.loads(self.ncl("claude", "check", "--hook", "antigravity",
                                          "--payload", stdin=payload).stdout)
        self.assertEqual(antigravity["decision"], "ask")
        self.assertTrue(antigravity["allow_tool"])
        codex = json.loads(self.ncl("claude", "check", "--hook", "codex", "--payload",
                                    stdin=payload).stdout)
        self.assertEqual(codex["hookSpecificOutput"]["permissionDecision"], "allow")
        self.assertIn("additionalContext", codex["hookSpecificOutput"])

    def test_paths_outside_repo_and_exempt_paths_are_allowed(self):
        outside = json.dumps({"tool_input": {"file_path": str(self.root / "elsewhere.txt")}})
        self.assertEqual(self.ncl("claude", "check", "--hook", "claude", "--payload",
                                  stdin=outside).stdout.strip(), "")
        (self.repo / ".agents").mkdir()
        (self.repo / ".agents" / "never-collide.json").write_text(
            json.dumps({"enforce": "warn", "exempt": ["docs/**"]}), encoding="utf-8")
        self.ncl("claude", "check", "docs/notes.md")
        self.ncl("claude", "check", "src/x.ts", expect=2)

    def test_git_hook_warns_then_denies(self):
        self.git("checkout", "-q", "-b", "claude/T-1")
        (self.repo / "a.txt").write_text("x\n", encoding="utf-8")
        self.git("add", "a.txt")
        warned = self.ncl("claude", "check", "--hook", "git", "--staged")
        self.assertIn("a.txt is not claimed by claude", warned.stderr)

        self.ncl("claude", "enforce", "deny")
        refused = self.ncl("claude", "check", "--hook", "git", "--staged", expect=1)
        self.assertIn("commit refused", refused.stderr)

        self.ncl("claude", "claim", "--task", "T-1", "--paths", "a.txt", "--intent", "x")
        clean = self.ncl("claude", "check", "--hook", "git", "--staged")
        self.assertEqual(clean.stderr.strip(), "")

        self.git("checkout", "-q", "-b", "main")
        on_main = self.ncl("claude", "check", "--hook", "git", "--staged", expect=1)
        self.assertIn("commit is on main", on_main.stderr)

    def test_check_uses_cache_when_origin_is_unreachable(self):
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/**", "--intent", "x")
        self.git("remote", "set-url", "origin", str(self.root / "gone.git"))
        (self.repo / ".ncl" / "fetched_at").write_text("2000-01-01T00:00:00Z", encoding="utf-8")
        result = self.ncl("claude", "check", "src/a.ts")
        self.assertIn("note: could not fetch the ledger", result.stdout)


class InstallHooksTests(RepoFixture):
    def test_install_hooks_registers_claude_and_git(self):
        first = self.ncl("claude", "install-hooks").stdout
        self.assertIn("never-collide.json created", first)
        self.assertIn("AGENT_NAME=claude", first)
        self.assertIn("pre-commit stub installed", first)
        settings = json.loads((self.repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["env"]["AGENT_NAME"], "claude")
        group = settings["hooks"]["PreToolUse"][0]
        self.assertEqual(group["matcher"], ncl.EDIT_MATCHER)
        self.assertIn("hooks/ncl/dispatch", group["hooks"][0]["command"])

        second = self.ncl("claude", "install-hooks").stdout
        self.assertIn("kept", second)
        self.assertIn("already registers", second)
        self.assertIn("already calls never-collide", second)
        settings_again = json.loads((self.repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(len(settings_again["hooks"]["PreToolUse"]), 1)

    def test_install_hooks_keeps_existing_settings_and_joins_never_again_stub(self):
        claude_dir = self.repo / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text(json.dumps({
            "env": {"AGENT_NAME": "codex"},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
                {"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/na/dispatch"}]}]},
        }), encoding="utf-8")
        hooks_dir = pathlib.Path(self.git("rev-parse", "--git-path", "hooks").strip())
        if not hooks_dir.is_absolute():
            hooks_dir = self.repo / hooks_dir
        hooks_dir.mkdir(parents=True, exist_ok=True)
        stub = hooks_dir / "pre-commit"
        stub.write_text('#!/bin/sh\n# never-again pre-commit stub\nr="x"\nexec "$r" "$@"\n',
                        encoding="utf-8")
        out = self.ncl("claude", "install-hooks").stdout
        self.assertIn("added to the never-again pre-commit stub", out)
        lines = stub.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[-1], 'exec "$r" "$@"')
        self.assertIn("hooks/ncl/pre-commit", lines[-2])
        settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["env"]["AGENT_NAME"], "codex")
        self.assertEqual(len(settings["hooks"]["PreToolUse"]), 2)


class EndToEndCommitTests(RepoFixture):
    """install.sh into a real clone, then commit through git's own hook."""

    def test_installed_hook_guards_real_commits(self):
        install = run(["bash", str(ROOT / "install.sh"), str(self.repo)], ROOT)
        self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "install never-collide")
        self.git("checkout", "-q", "-b", "claude/T-1")
        self.ncl("claude", "enforce", "deny")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "a.ts").write_text("export {}\n", encoding="utf-8")
        self.git("add", "-A")

        env = os.environ.copy()
        env["AGENT_NAME"] = "claude"
        refused = run(["git", "commit", "-q", "-m", "unclaimed"], self.repo, env)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("src/a.ts is not claimed by claude", refused.stderr)

        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/**", "--intent", "x")
        allowed = run(["git", "commit", "-q", "-m", "claimed"], self.repo, env)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

        dispatch = run(["bash", str(self.repo / ".claude" / "hooks" / "ncl" / "dispatch")],
                       self.repo, env, stdin=json.dumps({"tool_name": "Edit", "tool_input": {
                           "file_path": str(self.repo / "README.md")}}))
        self.assertEqual(dispatch.returncode, 0, dispatch.stderr)
        decision = json.loads(dispatch.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("README.md is not claimed", decision["permissionDecisionReason"])


class VerifyPrTests(RepoFixture):
    def setUp(self):
        super().setUp()
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("push", "-q", "-u", "origin", "main")
        self.git("checkout", "-q", "-b", "claude/T-1")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "a.ts").write_text("export {}\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "work")

    def verify(self, *extra, expect):
        return self.ncl("ci", "verify-pr", "--base", "origin/main", "--head", "HEAD",
                        "--branch", "claude/T-1", *extra, expect=expect)

    def test_no_ledger_and_no_claim_fail(self):
        self.assertIn("no agents/ledger branch", self.verify(expect=1).stdout)
        self.ncl("claude", "claim", "--task", "T-9", "--paths", "src/**", "--intent", "x")
        self.git("checkout", "-q", "-b", "claude/other")
        result = self.ncl("ci", "verify-pr", "--base", "origin/main", "--head", "HEAD",
                          "--branch", "claude/other", expect=1)
        self.assertIn("no claim on branch claude/other", result.stdout)

    def test_claim_must_be_done_and_cover_every_path(self):
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/**", "--intent", "x")
        result = self.verify(expect=1)
        self.assertIn("T-1 is claimed, needs done", result.stdout)

        self.ncl("claude", "done", "--task", "T-1", "--pr", "1")
        self.assertIn("OK   1 changed path(s) covered by 1 claim(s)", self.verify(expect=0).stdout)
        self.assertIn("T-1 is done, needs tested", self.verify("--require", "tested", expect=1).stdout)

        (self.repo / "docs.md").write_text("x\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "more")
        result = self.verify(expect=1)
        self.assertIn("docs.md changed without a claim on this branch", result.stdout)

        self.ncl("claude", "tested", "--task", "T-1", "--evidence", "ran")
        self.ncl("claude", "release", "--task", "T-1")
        (self.repo / "docs.md").unlink()
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "undo")
        self.verify("--require", "tested", expect=0)

    def test_task_named_in_branch_counts_even_if_claimed_elsewhere(self):
        self.git("checkout", "-q", "main")
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/**", "--intent", "x")
        self.ncl("claude", "done", "--task", "T-1")
        self.git("checkout", "-q", "claude/T-1")
        self.verify(expect=0)


class FeedbackTests(RepoFixture):
    """A local HTTP server stands in for the site endpoint."""

    def setUp(self):
        super().setUp()
        import http.server
        import threading
        received = self.received = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                received.append((self.path, self.headers.get("User-Agent", ""),
                                 json.loads(self.rfile.read(length).decode("utf-8"))))
                body = b'{"ok": true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:{}/api/never-collide/feedback".format(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def feedback(self, *args, expect=0, stdin=None, tty_home=None):
        env = os.environ.copy()
        env["NCL_FEEDBACK_URL"] = self.url
        env["NCL_HOME"] = tty_home or str(self.root / "home")
        env.pop("NCL_NO_PROMPT", None)
        result = run([sys.executable, str(SCRIPT), "feedback"] + list(args), self.repo, env, stdin)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return result

    def test_dry_run_sends_nothing_and_shows_payload(self):
        result = self.feedback("--dry-run", "--message", "works well", "--name", "Sam")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["event"], "feedback")
        self.assertEqual(payload["message"], "works well")
        self.assertEqual(payload["name"], "Sam")
        self.assertNotIn("email", payload)
        self.assertEqual(self.received, [])

    def test_count_and_feedback_are_posted_only_with_yes(self):
        declined = self.feedback("--count", stdin="n\n")
        self.assertIn("Nothing sent", declined.stdout)
        self.assertEqual(self.received, [])

        sent = self.feedback("--count", "--yes")
        self.assertIn("Sent (200", sent.stdout)
        path, agent, payload = self.received[-1]
        self.assertEqual(path, "/api/never-collide/feedback")
        self.assertTrue(agent.startswith("never-collide/"))
        self.assertEqual(payload["event"], "count")
        self.assertEqual(set(payload), {"project", "event", "version", "os", "python", "ts"})

        self.feedback("--yes", "--email", "sam@example.invalid", "-m", "add a tui")
        self.assertEqual(self.received[-1][2]["email"], "sam@example.invalid")
        self.assertEqual(self.received[-1][2]["message"], "add a tui")

    def test_nothing_to_send_without_a_tty_fails_cleanly(self):
        result = self.feedback(expect=1, stdin="")
        self.assertIn("nothing to send", result.stderr)

    def test_install_prompt_is_silent_without_a_tty(self):
        result = self.feedback("--install-prompt", stdin="")
        self.assertEqual(result.stdout, "")
        self.assertFalse((self.root / "home" / "prompted").exists())
        self.assertEqual(self.received, [])

    def test_unreachable_endpoint_is_reported(self):
        env = os.environ.copy()
        env["NCL_FEEDBACK_URL"] = "http://127.0.0.1:9/nowhere"
        result = run([sys.executable, str(SCRIPT), "feedback", "--count", "--yes"], self.repo, env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not send feedback", result.stderr)


class UpgradeTests(RepoFixture):
    def stage_source(self, version):
        import shutil
        source = self.root / ("source-" + version)
        for relative in ("install.sh", "VERSION", ".claude/never-collide/ncl",
                         ".claude/never-collide/ncl.cmd", ".claude/hooks/ncl/dispatch",
                         ".claude/hooks/ncl/pre-commit", ".claude/skills/never-collide/SKILL.md",
                         "templates/AGENTS.md", "templates/OWNERSHIP.md", "templates/PROTOCOL.md",
                         "templates/never-collide.yml"):
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, target)
        (source / "VERSION").write_text(version + "\n", encoding="utf-8")
        cli = source / ".claude" / "never-collide" / "ncl"
        cli.write_text(cli.read_text(encoding="utf-8").replace(
            'VERSION = "{}"'.format(ncl.VERSION), 'VERSION = "{}"'.format(version)), encoding="utf-8")
        return source

    def test_upgrade_from_a_local_source(self):
        env = os.environ.copy()
        env["NCL_NO_PROMPT"] = "1"
        install = run(["bash", str(ROOT / "install.sh"), str(self.repo)], ROOT, env)
        self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
        installed = self.repo / ".claude" / "never-collide" / "ncl"

        same = run([sys.executable, str(installed), "upgrade", "--from", str(ROOT)], self.repo, env)
        self.assertEqual(same.returncode, 0, same.stderr)
        self.assertIn("up to date", same.stdout)

        newer = self.stage_source("9.9.9")
        check = run([sys.executable, str(installed), "upgrade", "--check", "--from", str(newer)],
                    self.repo, env)
        self.assertIn("available  9.9.9", check.stdout)
        self.assertIn("Run ncl upgrade", check.stdout)
        self.assertEqual(run([sys.executable, str(installed), "version"], self.repo, env).stdout.strip(),
                         "ncl " + ncl.VERSION)

        declined = run([sys.executable, str(installed), "upgrade", "--from", str(newer)],
                       self.repo, env, stdin="n\n")
        self.assertEqual(declined.returncode, 1)

        done = run([sys.executable, str(installed), "upgrade", "--yes", "--from", str(newer)],
                   self.repo, env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(run([sys.executable, str(installed), "version"], self.repo, env).stdout.strip(),
                         "ncl 9.9.9")

    def test_upgrade_without_network_explains(self):
        env = os.environ.copy()
        env["NCL_UPDATE_URL"] = "http://127.0.0.1:9/releases"
        result = run([sys.executable, str(SCRIPT), "upgrade", "--check"], self.repo, env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not reach GitHub", result.stderr)


class LogAndReportTests(RepoFixture):
    def log_lines(self):
        path = self.repo / ".claude" / "never-collide" / "ncl.log"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def test_ledger_writes_hook_decisions_and_errors_are_logged(self):
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/**", "--intent", "x")
        payload = json.dumps({"tool_input": {"file_path": str(self.repo / "docs" / "a.md")}})
        self.ncl("claude", "check", "--hook", "claude", "--payload", stdin=payload)
        self.ncl("claude", "check", "--hook", "claude", "--payload",
                 stdin=json.dumps({"tool_input": {"file_path": str(self.repo / "src" / "a.ts")}}))
        self.ncl("antigravity", "done", "--task", "T-1", expect=1)

        kinds = [(item["kind"], item.get("status") or item.get("decision") or item.get("command"))
                 for item in self.log_lines()]
        self.assertEqual(kinds, [("ledger", "claimed"), ("hook", "ask"), ("hook", "allow"),
                                 ("error", "done")])
        asked = self.log_lines()[1]
        self.assertEqual(asked["paths"], ["docs/a.md"])
        self.assertEqual(asked["mode"], "warn")

        report = self.ncl("claude", "report").stdout
        self.assertIn("claimed      1", report)
        self.assertIn("claude:ask           1", report)
        self.assertIn("Errors: 1", report)
        self.assertIn("is held by claude", report)

        summary = json.loads(self.ncl("claude", "report", "--json").stdout)
        self.assertEqual(summary["events"], 4)
        self.assertEqual(summary["hooks"], {"claude:ask": 1, "claude:allow": 1})
        self.assertNotIn("paths", json.dumps(summary))

    def test_empty_report(self):
        self.assertIn("No events logged yet", self.ncl("claude", "report").stdout)

    def test_feedback_report_attaches_counts_only(self):
        self.ncl("claude", "claim", "--task", "T-1", "--paths", "src/secret/**", "--intent", "x")
        result = self.ncl("claude", "feedback", "--dry-run", "--count", "--report")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["report"]["ledger"], {"claimed": 1})
        self.assertNotIn("secret", result.stdout)


class DoctorAndUninstallTests(RepoFixture):
    def test_doctor_reports_and_uninstall_reverts(self):
        env = os.environ.copy()
        env["NCL_NO_PROMPT"] = "1"
        install = run(["bash", str(ROOT / "install.sh"), str(self.repo)], ROOT, env)
        self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
        (self.repo / "CLAUDE.md").write_text("# Mine\n\n<!-- never-collide:start -->\n@AGENTS.md\n"
                                             "<!-- never-collide:end -->\n", encoding="utf-8")

        without_name = self.ncl(None, "doctor", expect=1)
        self.assertIn("FAIL AGENT_NAME: unset", without_name.stdout)
        healthy = self.ncl("claude", "doctor")
        self.assertIn("All good", healthy.stdout)
        self.assertIn("OK   .claude/settings.json registers the edit hook", healthy.stdout)
        self.assertIn("OK   .git/hooks/pre-commit calls never-collide", healthy.stdout)
        self.assertIn("WARN ledger branch agents/ledger not created yet", healthy.stdout)

        declined = self.ncl("claude", "uninstall", expect=1, stdin="n\n")
        self.assertIn("Nothing changed", declined.stdout)
        self.assertTrue((self.repo / ".claude" / "hooks" / "ncl" / "dispatch").exists())

        removed = self.ncl("claude", "uninstall", "--yes").stdout
        self.assertIn("removed  .claude/hooks/ncl/", removed)
        self.assertIn("removed  .git/hooks/pre-commit stub", removed)
        self.assertIn("removed  CLAUDE.md never-collide block", removed)
        self.assertFalse((self.repo / ".claude" / "never-collide").exists())
        self.assertFalse((self.repo / ".claude" / "skills" / "never-collide").exists())
        self.assertFalse((self.repo / ".github" / "workflows" / "never-collide.yml").exists())
        settings = json.loads((self.repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertNotIn("hooks", settings)
        self.assertEqual(settings["env"]["AGENT_NAME"], "claude")
        self.assertEqual((self.repo / "CLAUDE.md").read_text(encoding="utf-8").strip(), "# Mine")
        self.assertTrue((self.repo / "AGENTS.md").exists())
        self.assertTrue((self.repo / ".agents" / "never-collide.json").exists())

    def test_uninstall_leaves_a_never_again_stub_in_place(self):
        env = os.environ.copy()
        env["NCL_NO_PROMPT"] = "1"
        hooks_dir = pathlib.Path(self.git("rev-parse", "--git-path", "hooks").strip())
        if not hooks_dir.is_absolute():
            hooks_dir = self.repo / hooks_dir
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (hooks_dir / "pre-commit").write_text(
            '#!/bin/sh\n# never-again pre-commit stub\nr="x"\nexec "$r" "$@"\n', encoding="utf-8")
        run(["bash", str(ROOT / "install.sh"), str(self.repo)], ROOT, env)
        self.assertIn("hooks/ncl/pre-commit", (hooks_dir / "pre-commit").read_text(encoding="utf-8"))
        self.ncl("claude", "uninstall", "--yes")
        self.assertEqual((hooks_dir / "pre-commit").read_text(encoding="utf-8"),
                         '#!/bin/sh\n# never-again pre-commit stub\nr="x"\nexec "$r" "$@"\n')


if __name__ == "__main__":
    unittest.main()
