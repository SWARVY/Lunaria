from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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

    def test_repository_agent_template_is_valid(self) -> None:
        template = (ROOT / "assets" / "luna-worker.toml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(manager.validate_agent_text(template), ())

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

    def test_diff_detects_final_newline_only_drift(self) -> None:
        target = Path("/tmp/luna-worker.toml")
        diff = manager.render_diff("same content", "same content\n", target)
        self.assertNotEqual(diff, "")

    def test_diff_preserves_crlf_only_drift(self) -> None:
        target = Path("/tmp/luna-worker.toml")
        diff = manager.render_diff("same content\r\n", "same content\n", target)
        self.assertNotEqual(diff, "")
        self.assertIn("\r\n", diff)

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

    def test_install_rejects_protected_config_before_reading_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            target = home / ".codex" / "config.toml"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"\xff")

            with patch.object(manager.Path, "home", return_value=home):
                with self.assertRaisesRegex(
                    OSError,
                    "protected Codex config",
                ):
                    manager.install_agent(VALID_AGENT, target, replace=True)

            self.assertEqual(target.read_bytes(), b"\xff")

    def test_install_rejects_lexical_alias_of_protected_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            target = home / ".codex" / "config.toml"
            target.parent.mkdir(parents=True)
            target.write_text("protected", encoding="utf-8")
            alias = target.parent / "agents" / ".." / target.name

            with patch.object(manager.Path, "home", return_value=home):
                with self.assertRaisesRegex(
                    OSError,
                    "protected Codex config",
                ):
                    manager.install_agent(VALID_AGENT, alias, replace=True)

            self.assertEqual(target.read_text(encoding="utf-8"), "protected")

    def test_install_rejects_symlink_alias_of_protected_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            target = home / ".codex" / "config.toml"
            target.parent.mkdir(parents=True)
            target.write_text("protected", encoding="utf-8")
            alias = root / "config-alias.toml"
            alias.symlink_to(target)

            with patch.object(manager.Path, "home", return_value=home):
                with self.assertRaisesRegex(
                    OSError,
                    "protected Codex config",
                ):
                    manager.install_agent(VALID_AGENT, alias, replace=True)

            self.assertTrue(alias.is_symlink())
            self.assertEqual(target.read_text(encoding="utf-8"), "protected")

    def test_install_refuses_live_target_symlink_even_with_replace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "destination.toml"
            destination.write_text("keep me", encoding="utf-8")
            target = root / "luna-worker.toml"
            target.symlink_to(destination)

            with self.assertRaisesRegex(OSError, "symlink"):
                manager.install_agent(VALID_AGENT, target, replace=True)

            self.assertTrue(target.is_symlink())
            self.assertEqual(destination.read_text(encoding="utf-8"), "keep me")

    def test_install_refuses_dangling_target_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "luna-worker.toml"
            target.symlink_to(root / "missing.toml")

            with self.assertRaisesRegex(OSError, "symlink"):
                manager.install_agent(VALID_AGENT, target)

            self.assertTrue(target.is_symlink())
            self.assertFalse((root / "missing.toml").exists())

    def test_fresh_install_does_not_clobber_racing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "luna-worker.toml"
            real_fsync = manager.os.fsync

            def create_racing_target(file_descriptor: int) -> None:
                real_fsync(file_descriptor)
                target.write_text("racing writer", encoding="utf-8")

            with patch.object(manager.os, "fsync", side_effect=create_racing_target):
                with self.assertRaises(manager.ExistingAgentError):
                    manager.install_agent(VALID_AGENT, target)

            self.assertEqual(target.read_text(encoding="utf-8"), "racing writer")
            self.assertEqual(list(root.glob(f".{target.name}.*")), [])

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

    def test_replace_refuses_to_overwrite_colliding_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "luna-worker.toml"
            target.write_text("existing", encoding="utf-8")
            backup = Path(f"{target}.bak-20260803T120000Z")
            backup.write_text("older backup", encoding="utf-8")

            with self.assertRaisesRegex(
                FileExistsError,
                "Backup already exists",
            ):
                manager.install_agent(
                    VALID_AGENT,
                    target,
                    replace=True,
                    timestamp="20260803T120000Z",
                )

            self.assertEqual(target.read_text(encoding="utf-8"), "existing")
            self.assertEqual(backup.read_text(encoding="utf-8"), "older backup")
            self.assertEqual(list(root.glob(f".{target.name}.*")), [])


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
    def _run_with_target(
        self,
        command: str,
        template: Path,
        target: Path,
    ) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        argv = [command, "--template", str(template), "--target", str(target)]
        report = manager.EnvironmentReport("0.144.1", True, ())
        try:
            with (
                patch.object(manager, "run_environment_check", return_value=report),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                code = manager.main(argv)
        except BaseException as error:
            self.fail(f"{command} leaked {type(error).__name__}: {error}")
        return code, stdout.getvalue(), stderr.getvalue()

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

    def test_all_commands_map_directory_target_to_environment_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.toml"
            template.write_text(VALID_AGENT, encoding="utf-8")
            target = root / "target-directory"
            target.mkdir()

            for command in ("check", "plan", "install", "verify"):
                with self.subTest(command=command):
                    code, _stdout, stderr = self._run_with_target(
                        command,
                        template,
                        target,
                    )
                    self.assertEqual(code, manager.EXIT_ENVIRONMENT)
                    self.assertIn("Cannot read target", stderr)
                    self.assertIn(str(target), stderr)

    def test_all_commands_map_dangling_symlink_to_environment_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.toml"
            template.write_text(VALID_AGENT, encoding="utf-8")

            for command in ("check", "plan", "install", "verify"):
                with self.subTest(command=command):
                    command_root = root / command
                    command_root.mkdir()
                    target = command_root / "luna-worker.toml"
                    target.symlink_to(command_root / "missing.toml")
                    code, _stdout, stderr = self._run_with_target(
                        command,
                        template,
                        target,
                    )
                    self.assertEqual(code, manager.EXIT_ENVIRONMENT)
                    self.assertIn("symlink", stderr)
                    self.assertTrue(target.is_symlink())

    def test_install_cli_rejects_dangling_symlink_without_replacing_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.toml"
            template.write_text(VALID_AGENT, encoding="utf-8")
            missing = root / "missing.toml"
            target = root / "luna-worker.toml"
            target.symlink_to(missing)

            code, _stdout, stderr = self._run_with_target(
                "install",
                template,
                target,
            )

            self.assertEqual(code, manager.EXIT_ENVIRONMENT)
            self.assertIn("symlink", stderr)
            self.assertTrue(target.is_symlink())
            self.assertFalse(missing.exists())

    def test_install_cli_rejects_protected_config_with_environment_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            template = Path(directory) / "template.toml"
            template.write_text(VALID_AGENT, encoding="utf-8")
            target = home / ".codex" / "config.toml"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"\xff")
            stdout = StringIO()
            stderr = StringIO()

            with (
                patch.object(manager.Path, "home", return_value=home),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                try:
                    code = manager.main([
                        "install",
                        "--template",
                        str(template),
                        "--target",
                        str(target),
                        "--replace",
                    ])
                except BaseException as error:
                    self.fail(
                        "install leaked "
                        f"{type(error).__name__} before protecting config.toml: {error}"
                    )

            self.assertEqual(code, manager.EXIT_ENVIRONMENT)
            self.assertIn("protected Codex config", stderr.getvalue())
            self.assertEqual(target.read_bytes(), b"\xff")

    def test_successful_install_prints_new_task_discovery_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.toml"
            template.write_text(VALID_AGENT, encoding="utf-8")
            target = root / "luna-worker.toml"

            code, stdout, _stderr = self._run_with_target(
                "install",
                template,
                target,
            )

            self.assertEqual(code, manager.EXIT_OK)
            self.assertIn("start a new Codex task", stdout)
            self.assertIn("custom-agent discovery", stdout)
