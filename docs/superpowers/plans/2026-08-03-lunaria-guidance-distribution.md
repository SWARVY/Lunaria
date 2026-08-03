# Lunaria Guidance and Skills CLI Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lunaria가 원문의 선택적 Sol/Luna Max 운영 모델을 한국어로 명확히 안내하고, 불필요한 저장소 파일을 제외한 채 `npx skills`로 설치·검증되게 한다.

**Architecture:** 루트 `SKILL.md`는 Sol/Luna 역할, 위임 판단, 작업 패킷, 결과 검증을 한 번에 읽을 수 있는 짧은 한국어 실행 계약으로 유지한다. 기존 Python 관리 도구와 Luna TOML은 그대로 재사용하며, 저장소 루트 자체를 Skills CLI의 단일 스킬 패키지로 배포한다. `docs/superpowers`는 Git 이력에는 남기되 최종 트리에서는 추적 해제하고 `.gitignore`로 재유입을 막는다.

**Tech Stack:** Markdown/YAML/TOML, Python 3 `unittest`, Git, Skills CLI `1.5.18` via `npx skills`

## Global Constraints

- 주 에이전트는 정확히 `gpt-5.6-sol`이고 `luna_worker`는 `gpt-5.6-luna` / `max`인 2레인 구조를 유지한다.
- 모든 구현을 Luna에 강제하지 않고, 경계가 명확하며 위임 이득이 있는 작업에 `luna_worker`를 우선한다.
- 별도 Sol 리뷰어, Terra 레인, Codex Marketplace 플러그인, rollout/session 검사기를 추가하지 않는다.
- `~/.codex/config.toml`과 실제 `~/.codex/agents`를 테스트나 설치 검증 대상으로 사용하지 않는다.
- Skills CLI 설치는 스킬 파일만 배포하며 companion `luna_worker` 설치는 기존 명시적 `check -> plan -> 승인 -> install -> verify` 흐름을 유지한다.
- 구현과 검증은 일반 저장소의 `feat/lunaria-guidance-distribution` 브랜치에서 수행하며 worktree를 만들지 않는다.
- `docs/superpowers` 파일은 로컬에 보존하고 Git 인덱스에서만 제거한다.

---

### Task 1: 선택적 위임 가이드와 Sol 검증 계약

**Files:**
- Modify: `tests/test_skill_contract.py`
- Modify: `SKILL.md`
- Modify: `agents/openai.yaml`

**Interfaces:**
- Consumes: 기존 `luna_worker`, `manage_luna_worker.py`, 작업/결과 계약 필드
- Produces: 한국어 실행 가이드, `Files and ownership`, `Interfaces`가 추가된 작업 패킷, 공개 metadata 기반 라우팅 확인 규칙

- [ ] **Step 1: 현재 스킬 없는 선택 판단의 RED 기준을 기록한다**

fresh context 평가자에게 Lunaria 파일이나 기대 답을 주지 않고 다음 상황을 제시한다.

```text
메인 Sol로서 다음 일을 어떤 서브 에이전트에 위임할지 결정하라.
1. 한 줄짜리 오탈자 수정
2. 결제 모듈의 읽기 전용 코드 리뷰
3. 인증·결제·사용자 모듈의 새 공개 API 아키텍처 결정
4. 서로 다른 모듈 구현이지만 같은 lockfile을 수정하는 두 작업
결정, 병렬/직렬 실행, 워커에게 줄 필수 입력, 결과 검증 방법을 작성하라.
```

현재 가이드 없이 `작은 작업까지 일괄 위임`, `아키텍처 판단 위임`, `공유 lockfile 병렬 쓰기`, `파일 소유권/인터페이스/부모 재검증 누락` 중 하나가 나타나는지 원문 응답으로 기록한다. 아무 실패도 없으면 가이드 변경을 강제하지 말고 Step 2의 테스트가 실제 누락 계약만 검증하도록 축소한다.

- [ ] **Step 2: 새 계약을 요구하는 실패 테스트를 작성한다**

`tests/test_skill_contract.py`에 다음 테스트를 추가하고, 기존 모델 pin·Git 안전성 테스트는 유지한다.

```python
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
```

한국어 번역으로 바뀌는 기존 의미 테스트는 영어 문장 전체가 아니라 모델 ID, 명령, 필수 계약 필드와 한국어 의미 문구를 검사하도록 갱신한다. TOML 워커 계약 검사는 변경하지 않는다.

- [ ] **Step 3: RED를 확인한다**

Run:

```bash
python3 -B -m unittest tests.test_skill_contract -v
```

Expected: 새 네 테스트와 한국어 의미를 요구하도록 수정된 기존 테스트가 현재 영어 `SKILL.md` 때문에 FAIL한다. 기존 Luna pin, metadata, Git 안전성 테스트는 PASS한다.

- [ ] **Step 4: `SKILL.md`를 최소 한국어 실행 계약으로 다시 작성한다**

frontmatter는 발견성을 위해 다음 영문 trigger를 유지한다.

```yaml
---
name: lunaria
description: Use when a Sol primary agent has bounded, independently verifiable coding subtasks that can be delegated without giving up requirements, architecture, or final integration decisions.
---
```

본문은 다음 순서를 사용한다.

```markdown
# Lunaria로 Sol과 Luna Max 오케스트레이션하기

## 핵심 원칙
Sol은 메인 스레드에서 목표, 요구사항, 아키텍처, 분해, 검증, 통합을 소유한다.
Luna Max는 경계가 명확한 작업 패킷만 처리하는 말단 워커다.
모든 구현을 Luna에 강제하지 않는다.

## 언제 Luna Max를 사용하는가
- 특정 파일이나 모듈의 코드 리뷰
- 특정 모듈 분석
- 쓰기 경로가 독점적인 독립 기능 구현
- 테스트 작성, 실패 원인 조사, 검증
- 서로 의존하지 않는 읽기 전용 조사

작업 패킷 작성과 결과 검증을 포함한 위임 비용이 Sol의 직접 처리보다 작을 때만 위임한다.

## 위임하지 않는 작업
- 요구사항, 성공 조건, 아키텍처, 공용 인터페이스를 결정해야 하는 작업
- 동일 파일, lockfile, 생성물, 마이그레이션을 공유하는 동시 쓰기
- 외부 부수 효과나 최종 승인이 필요한 작업
- 작은 단일 단계 수정
```

이후 기존 사전 점검, 병렬/직렬 규칙, 전체 Git mutation 금지, 작업 패킷, 결과 계약, 설정 안전성을 한국어로 보존한다. 작업 패킷에는 정확히 `Files and ownership:`과 `Interfaces:`를 추가한다. 결과 수용 절차에는 워커 보고를 검증 전까지 주장으로 취급하고 Sol이 실제 파일, 전체 diff, 범위, 검증 명령을 다시 확인하도록 적는다. 실패한 패킷은 근거를 반영해 수정하며 같은 패킷을 그대로 재시도하지 않는다. 공개 spawn/details metadata가 제공하는 역할·모델·노력을 대조하고, 누락값을 추정하거나 내부 rollout/session 파일을 읽지 않는다.

- [ ] **Step 5: UI metadata를 한국어 기본 프롬프트로 맞춘다**

`agents/openai.yaml`의 `default_prompt`를 다음으로 변경한다.

```yaml
interface:
  display_name: "Lunaria"
  short_description: "Sol과 Luna Max의 안전한 작업 오케스트레이션"
  default_prompt: "$lunaria를 사용해 Sol은 판단과 통합을 유지하고, 경계가 명확한 작업만 Luna Max에 위임해 주세요."
```

- [ ] **Step 6: GREEN을 확인한다**

Run:

```bash
python3 -B -m unittest tests.test_skill_contract -v
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: 계약 테스트와 전체 테스트가 모두 PASS한다.

- [ ] **Step 7: skill forward test를 실행한다**

Step 1과 같은 상황을 fresh context 평가자에게 이번에는 절대 경로의 `SKILL.md`와 `$lunaria` 사용 요청만 추가해 실행한다. 기대 답은 제공하지 않는다. 적합 작업만 Luna에 우선 배정하고, 작은 수정과 아키텍처 결정을 Sol에 남기며, 공유 lockfile 쓰기를 직렬화하고, 작업 패킷에 소유권·인터페이스·검증을 포함하며, Sol 재검증을 요구해야 한다.

- [ ] **Step 8: 변경을 커밋한다**

```bash
git add SKILL.md agents/openai.yaml tests/test_skill_contract.py
git commit -m "feat: clarify lunaria delegation guidance"
```

---

### Task 2: 저장소 위생과 설계 문서 추적 해제

**Files:**
- Create: `.gitignore`
- Remove from Git index only: `docs/superpowers/plans/2026-08-03-lunaria.md`
- Remove from Git index only: `docs/superpowers/plans/2026-08-03-lunaria-guidance-distribution.md`
- Remove from Git index only: `docs/superpowers/specs/2026-08-03-lunaria-design.md`

**Interfaces:**
- Consumes: 현재 Git 인덱스와 로컬 문서 파일
- Produces: 재생성되는 계획·로컬 캐시·편집기 파일이 커밋에 들어오지 않는 저장소 규칙

- [ ] **Step 1: ignore 규칙이 아직 없는 RED를 확인한다**

Run:

```bash
git check-ignore -q --no-index docs/superpowers/specs/example.md
git check-ignore -q --no-index .DS_Store
git check-ignore -q --no-index pkg/__pycache__/module.cpython-313.pyc
git check-ignore -q --no-index .venv/bin/python
```

Expected: 각 명령이 exit 1을 반환한다.

- [ ] **Step 2: 최소 `.gitignore`를 작성한다**

```gitignore
# Local planning and review artifacts
docs/superpowers/
.superpowers/sdd/

# macOS
.DS_Store

# Python caches and reports
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
.coverage.*
htmlcov/

# Virtual environments
.venv/
venv/

# Editors
.idea/
.vscode/
*.swp
```

- [ ] **Step 3: ignore 규칙 GREEN을 확인한다**

Step 1의 네 명령을 다시 실행한다. Expected: 모두 exit 0이다. 이어서 아래 명령이
각 경로에 적용된 정확한 규칙을 표시해야 한다.

```bash
git check-ignore -v --no-index docs/superpowers/specs/example.md
git check-ignore -v --no-index .DS_Store
git check-ignore -v --no-index pkg/__pycache__/module.cpython-313.pyc
git check-ignore -v --no-index .venv/bin/python
```

- [ ] **Step 4: 문서를 로컬에 보존하면서 Git 인덱스에서 제거한다**

```bash
git rm -r --cached docs/superpowers
```

Expected: 문서 파일은 디스크에 남고 `git ls-files docs/superpowers`는 출력이 없다.

- [ ] **Step 5: 저장소 위생 검증을 실행한다**

Run:

```bash
test -f docs/superpowers/specs/2026-08-03-lunaria-design.md
test -f docs/superpowers/plans/2026-08-03-lunaria-guidance-distribution.md
test -z "$(git ls-files docs/superpowers)"
git status --short
git diff --check
```

Expected: 두 로컬 문서는 존재하고, Git에는 `.gitignore` 추가와 기존 문서 삭제만 staged/unstaged 변경으로 나타나며 diff 오류가 없다.

- [ ] **Step 6: 변경을 커밋한다**

```bash
git add .gitignore
git commit -m "chore: ignore local planning artifacts"
```

---

### Task 3: Skills CLI 발견 및 격리 설치 검증

**Files:**
- Verify: `SKILL.md`
- Verify: `agents/openai.yaml`
- Verify: `assets/luna-worker.toml`
- Verify: `scripts/manage_luna_worker.py`

**Interfaces:**
- Consumes: Git에 추적되는 저장소 루트의 단일 skill package
- Produces: `npx skills add SWARVY/Lunaria --skill lunaria --agent codex -g -y`로 배포 가능한 구조

- [ ] **Step 1: 로컬 저장소 발견 검사를 실행한다**

Run:

```bash
npx skills add . --list
```

Expected: exit 0, `Found 1 skill`, `lunaria`가 출력된다.

- [ ] **Step 2: Git 추적 파일만 포함하는 배포 fixture를 만든다**

`mktemp -d /private/tmp/lunaria-skills-source.XXXXXX`로 절대 임시 경로를 만들고, 현재 `HEAD`의 `git archive`를 그 경로에 해제한다. archive에는 `docs/superpowers`, `.superpowers/sdd`, `.DS_Store`, Python 캐시가 없어야 한다.

Run:

```bash
LUNARIA_SOURCE_ROOT="$(mktemp -d /private/tmp/lunaria-skills-source.XXXXXX)"
git archive --format=tar HEAD -o "$LUNARIA_SOURCE_ROOT/lunaria.tar"
mkdir "$LUNARIA_SOURCE_ROOT/source"
tar -xf "$LUNARIA_SOURCE_ROOT/lunaria.tar" -C "$LUNARIA_SOURCE_ROOT/source"
```

- [ ] **Step 3: 별도 임시 프로젝트에 copy 설치한다**

`mktemp -d /private/tmp/lunaria-skills-target.XXXXXX`로 만든 빈 디렉터리에서 다음을 실행한다.

```bash
LUNARIA_TARGET_ROOT="$(mktemp -d /private/tmp/lunaria-skills-target.XXXXXX)"
cd "$LUNARIA_TARGET_ROOT"
npx skills add "$LUNARIA_SOURCE_ROOT/source" --skill lunaria --agent codex --copy -y
```

Expected: 실제 홈을 건드리지 않고
`$LUNARIA_TARGET_ROOT/.agents/skills/lunaria`에 프로젝트 범위 복사본이 설치된다.

- [ ] **Step 4: 설치된 패키지의 필수 리소스를 검증한다**

Skills CLI가 출력하거나 `npx skills list --json`이 보고한 설치 경로에서 다음 파일이 모두 존재하고 원본과 동일한지 확인한다.

```text
SKILL.md
agents/openai.yaml
assets/luna-worker.toml
scripts/manage_luna_worker.py
```

설치 트리에는 `docs/superpowers`, `.superpowers/sdd`, `.DS_Store`, `__pycache__`가 없어야 한다.

- [ ] **Step 5: 설치된 스킬과 기존 관리 도구를 검증한다**

Run:

```bash
LUNARIA_INSTALLED_SKILL="$LUNARIA_TARGET_ROOT/.agents/skills/lunaria"
LUNARIA_AGENT_TARGET="$LUNARIA_TARGET_ROOT/fixture-agents/luna-worker.toml"
python3 -B /Users/shinhyeonho/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$LUNARIA_INSTALLED_SKILL"
python3 -B "$LUNARIA_INSTALLED_SKILL/scripts/manage_luna_worker.py" plan --target "$LUNARIA_AGENT_TARGET"
python3 -B "$LUNARIA_INSTALLED_SKILL/scripts/manage_luna_worker.py" install --target "$LUNARIA_AGENT_TARGET"
python3 -B "$LUNARIA_INSTALLED_SKILL/scripts/manage_luna_worker.py" verify --target "$LUNARIA_AGENT_TARGET"
```

Expected: validator와 `plan -> install -> verify`가 모두 exit 0이고 실제 `~/.codex` 파일은 변경되지 않는다.

- [ ] **Step 6: GitHub 설치 경계를 기록한다**

원격 저장소가 아직 비어 있으므로 이번 단계에서는 로컬 archive fixture 설치까지만 증명한다. `SWARVY/Lunaria` 설치는 사용자가 브랜치 또는 `main` 푸시를 승인한 뒤 별도 fresh target에서 확인하며, 푸시 전에는 GitHub 설치가 검증됐다고 주장하지 않는다.

---

### Task 4: 최종 통합 검증

**Files:**
- Verify: repository root

**Interfaces:**
- Consumes: Tasks 1-3의 커밋
- Produces: 깨끗한 기능 브랜치와 재현 가능한 검증 증거

- [ ] **Step 1: 전체 테스트를 새로 실행한다**

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: 모든 테스트 PASS, failure/error 0.

- [ ] **Step 2: 공식 스킬 검증과 Skills CLI 발견 검사를 실행한다**

```bash
python3 -B /Users/shinhyeonho/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/shinhyeonho/Repository/lunaria
npx skills add . --list
```

Expected: `Skill is valid!`, `Found 1 skill`, `lunaria`.

- [ ] **Step 3: 저장소 상태와 범위를 검사한다**

```bash
git diff --check
git status --short --branch
git log --oneline --decorate -8
git ls-files docs/superpowers
```

Expected: 기능 브랜치가 깨끗하고 `docs/superpowers` 출력이 없다. 원격 푸시는 수행하지 않는다.

- [ ] **Step 4: 최종 결과를 보고한다**

한국어로 변경된 사용 판단 가이드, `.gitignore`, 로컬 보존·추적 해제된 설계 문서, Skills CLI 격리 설치 결과, GitHub 설치 미검증 경계를 요약한다. 사용자의 통합 선택 전에는 `main` 병합이나 원격 푸시를 수행하지 않는다.
