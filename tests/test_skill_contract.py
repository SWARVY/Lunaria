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
        self.assertIn("Luna Max", description.group(1))

    def test_strict_topology_pins_an_identifiable_sol_primary(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("primary model is exactly `gpt-5.6-sol`", text)
        self.assertIn("If the primary model cannot be identified", text)

    def test_luna_cannot_broaden_goals_or_decide_architecture(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Luna must not broaden goals", text)
        self.assertIn("Luna must not make architecture decisions", text)

    def test_skill_contains_required_delegation_and_result_slots(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for required in (
            "Objective:",
            "Allowed scope:",
            "Excluded scope:",
            "Deliverable:",
            "Required validation:",
            "Escalate when:",
            "Status: complete | blocked | needs_decision",
            "Validation run and results:",
        ):
            self.assertIn(required, text)

    def test_skill_forbids_silent_fallback_and_overlapping_writes(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("never silently substitute", text)
        self.assertIn("overlapping writes", text)
        self.assertIn("shared lockfiles", text)

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
