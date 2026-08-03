from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import manage_luna_worker as manager

VALID_AGENT = '''name = "luna_worker"
description = "Leaf worker"
model = "gpt-5.6-luna"
model_reasoning_effort = "max"
developer_instructions = "Stay bounded."
'''


class ValidationTests(unittest.TestCase):
    def test_valid_agent_has_no_errors(self) -> None:
        self.assertEqual(manager.validate_agent_text(VALID_AGENT), ())

    def test_invalid_toml_reports_syntax_error(self) -> None:
        errors = manager.validate_agent_text('name = "unterminated')
        self.assertTrue(any("TOML" in error for error in errors))

    def test_required_and_pinned_values_are_checked(self) -> None:
        errors = manager.validate_agent_text('name = "wrong"\ndescription = "x"\n')
        self.assertTrue(any("developer_instructions" in error for error in errors))
        self.assertTrue(any("gpt-5.6-luna" in error for error in errors))
        self.assertTrue(any("max" in error for error in errors))


class FileOperationTests(unittest.TestCase):
    def test_missing_target_diff_is_an_addition(self) -> None:
        target = Path("/tmp/luna-worker.toml")
        diff = manager.render_diff(None, VALID_AGENT, target)
        self.assertIn("--- /dev/null", diff)
        self.assertIn(f"+++ {target}", diff)

    def test_install_creates_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "agents" / "luna-worker.toml"
            backup = manager.install_agent(VALID_AGENT, target)
            self.assertIsNone(backup)
            self.assertEqual(target.read_text(encoding="utf-8"), VALID_AGENT)

    def test_install_refuses_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "luna-worker.toml"
            target.write_text("existing", encoding="utf-8")
            with self.assertRaises(manager.ExistingAgentError):
                manager.install_agent(VALID_AGENT, target)

    def test_replace_creates_timestamped_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "luna-worker.toml"
            target.write_text("existing", encoding="utf-8")
            backup = manager.install_agent(
                VALID_AGENT,
                target,
                replace=True,
                timestamp="20260803T120000Z",
            )
            self.assertEqual(backup, Path(f"{target}.bak-20260803T120000Z"))
            self.assertEqual(backup.read_text(encoding="utf-8"), "existing")
            self.assertEqual(target.read_text(encoding="utf-8"), VALID_AGENT)
