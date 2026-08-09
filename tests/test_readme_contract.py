from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReadmeContractTests(unittest.TestCase):
    def test_readme_is_a_complete_public_entrypoint(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        for phrase in (
            "판단은 Sol에",
            "## 빠른 시작",
            "## 왜 Lunaria인가",
            "## 작동 구조",
            "## 언제 사용하는가",
            "## 위임하지 않는 작업",
            "## 안전장치",
            "## 명령어",
            "## 저장소 구조",
        ):
            self.assertIn(phrase, text)

    def test_readme_documents_both_installation_layers(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(
            "npx skills add https://github.com/SWARVY/Lunaria -g --all",
            text,
        )
        self.assertIn("gpt-5.6-sol", text)
        self.assertIn("gpt-5.6-luna", text)
        self.assertIn("model_reasoning_effort = \"max\"", text)
        for command in ("check", "plan", "install", "verify"):
            self.assertIn(f"manage_luna_worker.py {command}", text)

    def test_readme_sets_realistic_expectations(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("토큰 절약", text)
        self.assertIn("메인 컨텍스트", text)
        self.assertIn("작업 완료 시간", text)
        self.assertIn("재작업", text)

    def test_readme_explains_the_efficiency_boundaries(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        for phrase in (
            "위임 경제성",
            "5분 미만",
            "구현자 1명과 리뷰어 1명",
            "동일 목표의 보정 1회",
            "단계별 검증",
            "새 Codex 작업",
            "오케스트레이션 요약",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
