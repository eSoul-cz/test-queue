"""Tests for install.sh with HOME in a temp dir. Run: python3 -m unittest discover -s skills/test-queue/scripts -p 'test_*.py'"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALL = os.path.join(HERE, "install.sh")

OTHER_HOOK = {"matcher": "Bash", "hooks": [{"type": "command", "command": "/usr/bin/other-hook", "timeout": 5}]}
FIXTURE = {
    "model": "opus",
    "permissions": {"allow": ["Bash(ls:*)"]},
    "hooks": {
        "PreToolUse": [OTHER_HOOK],
        "Stop": [{"hooks": [{"type": "command", "command": "echo done"}]}],
    },
}


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="testq-install-")
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.settings = os.path.join(self.home, ".claude", "settings.json")
        self.bin = os.path.join(self.home, ".local", "bin", "testq")
        self.share = os.path.join(self.home, ".local", "share", "testq")
        self.state = os.path.join(self.home, ".local", "state", "testq")

    def write_settings(self, content):
        os.makedirs(os.path.dirname(self.settings), exist_ok=True)
        with open(self.settings, "w") as f:
            f.write(content if isinstance(content, str) else json.dumps(content, indent=2))

    def read_settings(self):
        with open(self.settings) as f:
            return json.load(f)

    def install(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith("TESTQ_")}
        env["HOME"] = self.home
        return subprocess.run(
            ["sh", INSTALL, "--no-widget", *args], env=env, capture_output=True, text=True, timeout=120
        )

    def find_hooks(self, settings):
        return [
            h
            for entry in settings.get("hooks", {}).get("PreToolUse", [])
            for h in entry.get("hooks", [])
            if "testq hook" in h.get("command", "")
        ]

    def test_adds_hook_once_and_keeps_other_settings(self):
        self.write_settings(FIXTURE)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = self.read_settings()
        self.assertEqual(self.find_hooks(settings), [{"type": "command", "command": f"{self.bin} hook", "timeout": 10}])
        self.assertIn(OTHER_HOOK, settings["hooks"]["PreToolUse"])
        self.assertEqual(settings["hooks"]["Stop"], FIXTURE["hooks"]["Stop"])
        self.assertEqual(settings["model"], "opus")
        self.assertEqual(settings["permissions"], FIXTURE["permissions"])
        self.assertTrue(os.access(self.bin, os.X_OK))
        self.assertTrue(os.path.isfile(os.path.join(self.state, "config.json")))
        with open(self.settings + ".bak-testq") as f:
            self.assertEqual(json.load(f), FIXTURE)

    def test_creates_settings_when_missing(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.find_hooks(self.read_settings())), 1)

    def test_rerun_is_idempotent(self):
        self.write_settings(FIXTURE)
        self.assertEqual(self.install().returncode, 0)
        first = self.read_settings()
        self.assertEqual(self.install().returncode, 0)
        second = self.read_settings()
        self.assertEqual(first, second)
        self.assertEqual(len(self.find_hooks(second)), 1)

    def test_no_hook_leaves_settings_untouched(self):
        self.write_settings(FIXTURE)
        with open(self.settings) as f:
            before = f.read()
        result = self.install("--no-hook")
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(self.settings) as f:
            self.assertEqual(f.read(), before)
        self.assertFalse(os.path.exists(self.settings + ".bak-testq"))
        self.assertTrue(os.access(self.bin, os.X_OK))

    def test_uninstall_removes_only_the_testq_hook(self):
        self.write_settings(FIXTURE)
        self.assertEqual(self.install().returncode, 0)
        result = self.install("--uninstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_settings(), FIXTURE)
        self.assertFalse(os.path.lexists(self.bin))
        self.assertFalse(os.path.exists(self.share))
        self.assertTrue(os.path.isdir(self.state), "state is kept without --purge")

    def test_uninstall_purge_deletes_state(self):
        self.write_settings(FIXTURE)
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.install("--uninstall", "--purge").returncode, 0)
        self.assertFalse(os.path.exists(self.state))

    def test_uninstall_drops_empty_hooks_section(self):
        self.write_settings({"model": "opus"})
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.install("--uninstall").returncode, 0)
        self.assertEqual(self.read_settings(), {"model": "opus"})

    def test_invalid_json_aborts_without_changes(self):
        broken = '{"hooks": {"PreToolUse": [ '
        self.write_settings(broken)
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not valid JSON", result.stderr)
        with open(self.settings) as f:
            self.assertEqual(f.read(), broken)
        self.assertFalse(os.path.exists(self.settings + ".bak-testq"))
        self.assertFalse(os.path.exists(self.settings + ".tmp-testq"))

    def test_unknown_option_is_rejected(self):
        result = self.install("--bogus")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
