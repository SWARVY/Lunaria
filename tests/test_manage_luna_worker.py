from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

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


class EnvironmentTests(unittest.TestCase):
    def test_multi_agent_feature_must_be_enabled(self) -> None:
        enabled = manager.multi_agent_is_enabled(
            "multi_agent  stable  true\nplugins stable true\n"
        )
        disabled = manager.multi_agent_is_enabled(
            "multi_agent  stable  false\nplugins stable true\n"
        )
        self.assertTrue(enabled)
        self.assertFalse(disabled)

    def test_version_parser_accepts_current_cli_output(self) -> None:
        self.assertEqual(
            manager.parse_codex_version("codex-cli 0.144.1\n"),
            "0.144.1",
        )

    def test_feature_command_os_error_returns_environment_report(self) -> None:
        version_run = subprocess.CompletedProcess(
            ["codex", "--version"],
            0,
            stdout="codex-cli 0.144.1\n",
            stderr="",
        )
        with patch.object(
            manager.subprocess,
            "run",
            side_effect=[version_run, OSError("feature command unavailable")],
        ):
            report = manager.run_environment_check()

        self.assertEqual(report.version, "0.144.1")
        self.assertFalse(report.multi_agent_enabled)
        self.assertEqual(
            report.errors,
            ("Cannot run codex features list: feature command unavailable",),
        )


class CliTests(unittest.TestCase):
    def test_check_returns_drift_for_missing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "template.toml"
            template.write_text(VALID_AGENT, encoding="utf-8")
            target = Path(directory) / "missing.toml"
            report = manager.EnvironmentReport("0.144.1", True, ())
            with patch.object(manager, "run_environment_check", return_value=report):
                code = manager.main([
                    "check", "--template", str(template), "--target", str(target)
                ])
            self.assertEqual(code, manager.EXIT_DRIFT)

    def test_plan_prints_diff_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "template.toml"
            template.write_text(VALID_AGENT, encoding="utf-8")
            target = Path(directory) / "missing.toml"
            output = StringIO()
            with redirect_stdout(output):
                code = manager.main([
                    "plan", "--template", str(template), "--target", str(target)
                ])
            self.assertEqual(code, manager.EXIT_OK)
            self.assertFalse(target.exists())
            self.assertIn("+++", output.getvalue())

    def test_install_requires_replace_for_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "template.toml"
            target = Path(directory) / "luna-worker.toml"
            template.write_text(VALID_AGENT, encoding="utf-8")
            target.write_text("existing", encoding="utf-8")
            code = manager.main([
                "install", "--template", str(template), "--target", str(target)
            ])
            self.assertEqual(code, manager.EXIT_DRIFT)
            self.assertEqual(target.read_text(encoding="utf-8"), "existing")
