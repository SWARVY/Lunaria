from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_frontmatter_discovers_lunaria_for_bounded_delegation(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: lunaria\n"))
        description = re.search(r"^description: (.+)$", text, re.MULTILINE)
        self.assertIsNotNone(description)
        self.assertTrue(description.group(1).startswith("Use when "))
        self.assertIn("Sol", description.group(1))
        self.assertIn("bounded, independently verifiable", description.group(1))

    def test_strict_topology_pins_an_identifiable_sol_primary(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`gpt-5.6-sol`", text)
        self.assertIn("메인 모델을 식별할 수 없거나", text)

    def test_luna_cannot_broaden_goals_or_decide_architecture(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("목표를 확장할 수 없다", text)
        self.assertIn("아키텍처 결정을 내릴 수 없다", text)

    def test_skill_explains_when_to_use_and_not_use_luna(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "## 언제 Luna Max를 사용하는가",
            "코드 리뷰",
            "특정 모듈 분석",
            "독립 기능 구현",
            "테스트",
            "## 위임하지 않는 작업",
            "위임 비용",
            "모든 구현을 Luna에 강제하지 않는다",
        ):
            self.assertIn(phrase, text)

    def test_task_packet_includes_ownership_interfaces_and_concurrent_edit_safety(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "Files and ownership:",
            "Interfaces:",
            "다른 작업자나 사용자의 변경을 되돌리지 않는다",
        ):
            self.assertIn(phrase, text)

    def test_sol_treats_worker_reports_as_claims_and_reverifies(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "검증 전까지 주장",
            "전체 diff",
            "검증 명령을 직접 다시 실행",
            "같은 패킷을 그대로 재시도하지 않는다",
        ):
            self.assertIn(phrase, text)

    def test_runtime_evidence_uses_public_metadata_without_session_inspection(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("native spawn 또는 details metadata", text)
        self.assertIn("관측하지 못한 값을 추정하지 않는다", text)
        self.assertIn("내부 rollout 또는 세션 파일을 읽지 않는다", text)

    def test_skill_contains_required_delegation_and_result_slots(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for required in (
            "Objective:",
            "Allowed scope:",
            "Excluded scope:",
            "Inputs and known decisions:",
            "Deliverable:",
            "Required validation:",
            "Escalate when:",
            "Status: complete | blocked | needs_decision",
            "Summary:",
            "Files changed:",
            "Validation run and results:",
            "Unresolved risks:",
            "Decision requested from Sol:",
        ):
            self.assertIn(required, text)

    def test_every_delegation_requires_default_template_check_exit_zero(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("위임 전마다", text)
        self.assertIn("기본 템플릿", text)
        self.assertIn("manage_luna_worker.py check", text)
        self.assertIn("exit 0", text)
        self.assertIn("역할 표시만으로", text)

    def test_first_live_spawn_checks_discovery_model_and_max_entitlement(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("첫 실제 `luna_worker` spawn", text)
        self.assertIn("discovery", text)
        self.assertIn("모델", text)
        self.assertIn("Max entitlement", text)
        self.assertIn("다른 모델이나 역할로 자동 대체하지 않는다", text)

    def test_skill_forbids_silent_fallback_and_overlapping_writes(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("다른 모델이나 역할로 자동 대체하지 않는다", text)
        self.assertIn("쓰기 범위가 겹치는", text)
        self.assertIn("lockfile", text)

    def test_openai_metadata_mentions_skill_in_default_prompt(self) -> None:
        text = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Lunaria"', text)
        self.assertIn("$lunaria", text)

    def test_agent_is_pinned_leaf_luna_max(self) -> None:
        text = (ROOT / "assets/luna-worker.toml").read_text(encoding="utf-8")
        self.assertIn('name = "luna_worker"', text)
        self.assertIn('model = "gpt-5.6-luna"', text)
        self.assertIn('model_reasoning_effort = "max"', text)
        self.assertIn("Do not spawn agents", text)

    def test_git_mutations_are_forbidden_but_owned_file_edits_are_allowed(self) -> None:
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("모든 Git 작업/명령을 실행할 수 없다", skill_text)
        self.assertIn("다음을 포함하되 이에 한정되지 않는다", skill_text)
        self.assertIn(
            "`Files and ownership:`에 속한 일반 파일 편집은 허용된다",
            skill_text,
        )

        worker_text = (ROOT / "assets/luna-worker.toml").read_text(
            encoding="utf-8"
        ).lower()
        self.assertRegex(worker_text, r"any git operation that\s+mutates")
        self.assertTrue(
            "including but not limited to" in worker_text
            or "without limitation" in worker_text
        )

        for path, text in (
            (ROOT / "SKILL.md", skill_text.lower()),
            (ROOT / "assets/luna-worker.toml", worker_text),
        ):
            with self.subTest(path=path.name):
                for state in (
                    "working tree",
                    "index",
                    "refs",
                    "branches",
                    "tags",
                    "stash",
                    "worktrees",
                ):
                    self.assertIn(state, text)
                for operation in (
                    "commit",
                    "add",
                    "reset",
                    "merge",
                    "rebase",
                    "stash",
                    "clean",
                    "cherry-pick",
                    "revert",
                    "tag",
                    "switch",
                    "checkout",
                    "push",
                    "worktree",
                ):
                    self.assertRegex(text, rf"\bgit {operation}\b")
