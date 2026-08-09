<p align="center">
  <br/>
  ◯ ─────────── ◯
  <br/><br/>
  <strong>L U N A R I A</strong>
  <br/><br/>
  ◯ ─────────── ◯
  <br/>
</p>

<p align="center">
  <strong>판단은 Sol에, 경계가 분명한 실행은 Luna Max에.</strong>
  <br/>
  <sub>Sol이 목표와 통합을 유지하고, 독립적으로 검증할 수 있는 작업만 Luna Max에 위임하는 Codex orchestration skill.</sub>
</p>

<p align="center">
  <code>npx skills add https://github.com/SWARVY/Lunaria -g --all</code>
</p>

<p align="center">
  <a href="#빠른-시작">빠른 시작</a> ·
  <a href="#왜-lunaria인가">철학</a> ·
  <a href="#작동-구조">구조</a> ·
  <a href="#언제-사용하는가">사용 조건</a> ·
  <a href="#안전장치">안전장치</a> ·
  <a href="#명령어">명령어</a>
</p>

> *메인 에이전트는 더 많은 일을 직접 하는 대신, 더 중요한 판단을 계속 소유해야 합니다.*

Lunaria는 `gpt-5.6-sol`을 메인 에이전트로 유지하고, 범위와 성공 조건이 명확한 작업만
`gpt-5.6-luna`의 Max reasoning worker에 맡기는 Codex skill입니다.

Sol은 요구사항, 아키텍처, 작업 분해, 결과 검증과 최종 통합을 소유합니다. Luna Max는
코드 리뷰, 모듈 분석, 독립 구현, 테스트처럼 경계가 분명한 작업을 별도 컨텍스트에서
수행합니다.

---

## 빠른 시작

Lunaria는 두 단계로 설치합니다.

### 1. Skill 설치

```bash
npx skills add https://github.com/SWARVY/Lunaria -g --all
```

설치 후 새 Codex 작업을 시작해 `$lunaria`가 검색되는지 확인합니다. 설치 도구가 다른
skill 디렉터리를 선택했다면 아래 명령의 경로도 그 위치에 맞춥니다.

### 2. `luna_worker` 확인 및 설치

```bash
python3 -B ~/.agents/skills/lunaria/scripts/manage_luna_worker.py check
```

`check`가 설치 누락이나 drift를 보고하면 먼저 변경 내용을 확인합니다.

```bash
python3 -B ~/.agents/skills/lunaria/scripts/manage_luna_worker.py plan
```

diff가 의도와 맞을 때만 worker를 설치합니다.

```bash
python3 -B ~/.agents/skills/lunaria/scripts/manage_luna_worker.py install
python3 -B ~/.agents/skills/lunaria/scripts/manage_luna_worker.py verify
python3 -B ~/.agents/skills/lunaria/scripts/manage_luna_worker.py check
```

설치 기본 대상은 `~/.codex/agents/luna-worker.toml`입니다. 설치 후 현재 작업이 custom
agent 목록을 갱신하지 못했다면 새 Codex 작업을 시작합니다.

### 사용

```text
$lunaria를 사용해서 독립적으로 검증 가능한 작업만 Luna Max에 위임하고,
요구사항과 아키텍처 판단, 최종 검증과 통합은 Sol이 유지해줘.
```

Skill이 적용돼도 모든 작업을 Luna에 강제로 위임하지 않습니다. 위임 준비와 검증 비용이
Sol의 직접 처리보다 작을 때만 `luna_worker`를 사용합니다.

---

## 왜 Lunaria인가

큰 작업을 하나의 스레드에서 처리하면 코드 탐색, 테스트 로그, 실패 분석과 중간 추론이
요구사항과 아키텍처 결정을 밀어낼 수 있습니다. 반대로 기준 없이 여러 에이전트를 실행하면
범위 확대, 중복 작업, 쓰기 충돌과 검증 책임의 공백이 생깁니다.

Lunaria는 역할과 책임을 먼저 고정합니다.

| Sol | Luna Max |
|:---|:---|
| 목표와 성공 조건 이해 | 전달받은 작업 패킷 수행 |
| 요구사항과 아키텍처 결정 | 범위가 명확한 분석·구현·테스트 |
| 작업 분해와 의존성 관리 | 허용된 파일만 편집 |
| 결과 재검증과 최종 통합 | 검증 결과와 위험 보고 |
| 외부 상태와 Git 결정 | Git 상태 변경 금지 |

이 구조의 주된 가치는 다음과 같습니다.

- **메인 컨텍스트 보호**: 원시 탐색 로그 대신 검증 가능한 요약만 Sol에 반환
- **병렬 처리**: 서로 독립적인 읽기·검토·테스트 작업을 동시에 수행
- **독립 검토**: 별도 컨텍스트에서 구현과 가정을 다시 확인
- **책임 유지**: 최종 판단과 통합 책임이 메인 에이전트에서 사라지지 않음
- **범위 통제**: 파일 소유권, 제외 범위, 검증과 에스컬레이션 조건을 작업 전에 명시

---

## 작동 구조

```text
사용자 요청
    ↓
Sol — 목표 · 요구사항 · 아키텍처 · 성공 조건
    ↓
독립적으로 완료하고 검증할 수 있는가?
    ├─ 아니오 → Sol이 직접 처리하거나 결정을 요청
    └─ 예
        ↓
    작업 패킷 작성
        ↓
    Luna Max — 제한된 분석 · 구현 · 테스트
        ↓
    결과 계약으로 보고
        ↓
Sol — 실제 diff · 파일 범위 · 테스트 재검증
    ↓
최종 통합과 사용자 보고
```

Luna의 완료 보고는 검증 전까지 주장으로 취급합니다. Sol은 실제 파일과 전체 diff를
확인하고 필수 검증을 직접 다시 실행한 뒤에만 결과를 수용합니다.

<details>
<summary><strong>작업 패킷</strong></summary>

```text
Objective:
Allowed scope:
Excluded scope:
Files and ownership:
Interfaces:
Inputs and known decisions:
Deliverable:
Required validation:
Escalate when:
```

</details>

<details>
<summary><strong>결과 계약</strong></summary>

```text
Status: complete | blocked | needs_decision
Summary:
Files changed:
Validation run and results:
Unresolved risks:
Decision requested from Sol:
```

</details>

---

## 언제 사용하는가

- 특정 파일이나 모듈의 코드 리뷰
- 특정 모듈의 구조와 동작 분석
- 파일 소유권이 분리된 독립 기능 구현
- 테스트 작성, 실패 원인 조사와 검증
- 서로 의존하지 않는 읽기 전용 조사
- 여러 결과를 Sol이 최종 비교·통합해야 하는 작업

읽기 전용 작업은 병렬 실행할 수 있습니다. 쓰기 작업은 논리적인 파일 소유권이 겹치지
않고 공유 lockfile, 생성물, 마이그레이션, 포맷 출력이나 Git 상태 변경이 없을 때만
병렬로 실행합니다.

## 위임하지 않는 작업

- 요구사항이나 성공 조건을 결정해야 하는 작업
- 아키텍처와 공용 인터페이스를 선택해야 하는 작업
- 동일 파일, lockfile, 생성물이나 마이그레이션을 함께 수정하는 작업
- 외부 부수 효과나 최종 승인이 필요한 작업
- 의존성이 강해 순차적으로 처리해야 하는 작업
- 작업 패킷과 재검증 비용이 더 큰 작은 단일 단계 수정

Luna는 목표를 확장하거나 불명확한 아키텍처를 임의로 결정하지 않습니다. 경계를 넘는
판단이 필요하면 `needs_decision`으로 Sol에 반환합니다.

---

## 안전장치

### 고정된 topology

- 메인 모델: `gpt-5.6-sol`
- worker 역할: `luna_worker`
- worker 모델: `gpt-5.6-luna`
- reasoning: `model_reasoning_effort = "max"`

모델이나 역할이 확인되지 않으면 값을 추정하지 않습니다. 다른 worker로 조용히
대체하지도 않습니다.

### 매 위임 전 사전 점검

`check`는 현재 Codex CLI 버전, `multi_agent` 기능, worker 설치 여부와 관리 템플릿의
일치 상태를 읽기 전용으로 검사합니다. exit code가 `0`일 때만 위임합니다.

### 작업 경계

- 하나의 명시적인 목표와 산출물만 허용
- 허용·제외 범위와 파일 소유권을 사전 선언
- 겹치는 쓰기는 직렬화
- 다른 작업자나 사용자의 변경을 되돌리지 않음
- Luna가 다른 에이전트를 생성하지 않음

### Git 상태 보호

Luna는 일반 파일 편집은 할 수 있지만 working tree, index, refs, branch, tag, stash,
worktree를 변경하는 Git 명령은 실행할 수 없습니다. commit, add, reset, merge, rebase,
stash, clean, cherry-pick, revert, tag, switch, checkout, push와 worktree 작업이 모두
금지됩니다.

### 설정 보호

관리 스크립트는 `~/.codex/config.toml`을 수정하지 않습니다. 기존 worker를 기본적으로
덮어쓰지 않으며, 교체가 명시된 경우에도 기존 파일의 백업을 만든 뒤 원자적으로
설치합니다.

---

## 명령어

| 명령 | 상태 변경 | 역할 |
|:---|:---:|:---|
| `manage_luna_worker.py check` | 없음 | CLI, `multi_agent`, 설치 상태와 template drift 확인 |
| `manage_luna_worker.py plan` | 없음 | 현재 대상과 관리 template의 unified diff 출력 |
| `manage_luna_worker.py install` | 있음 | 기본 target에 worker 설치, 기존 파일 덮어쓰기 거부 |
| `manage_luna_worker.py verify` | 없음 | 설치 후 환경과 worker 설정 유효성 검증 |

기본 경로가 아닌 별도 설치 위치를 사용한다면 모든 명령에 `--template`과 `--target`을
명시할 수 있습니다. 기존 worker 교체는 diff를 검토하고 백업 정책을 이해한 경우에만
`install --replace`를 사용합니다.

---

## 기대치와 측정

Lunaria는 **토큰 절약을 보장하는 도구가 아닙니다.** 각 worker가 별도 컨텍스트에서 모델과
도구를 사용하므로 전체 토큰은 늘어날 수 있습니다. 목표는 총 토큰 최소화가 아니라 Sol의
메인 컨텍스트를 보호하고, 독립 작업의 완료 시간과 검증 품질을 개선하는 것입니다.

권장 지표는 다음 순서입니다.

1. Sol 메인 스레드 input tokens와 context 압축 횟수
2. 작업 완료 시간
3. 첫 검증 성공률과 재작업 횟수
4. 리뷰에서 발견한 결함과 회귀 수
5. Sol과 모든 Luna worker를 합친 전체 토큰

짧거나 강하게 결합된 작업에서 작업당 토큰이 증가한다면 위임하지 않는 것이 정상입니다.

---

## 저장소 구조

| 경로 | 역할 |
|:---|:---|
| [`SKILL.md`](./SKILL.md) | Sol이 따르는 오케스트레이션 규칙 |
| [`agents/openai.yaml`](./agents/openai.yaml) | Codex UI metadata와 기본 prompt |
| [`assets/luna-worker.toml`](./assets/luna-worker.toml) | 고정된 Luna Max leaf worker template |
| [`scripts/manage_luna_worker.py`](./scripts/manage_luna_worker.py) | worker 점검, diff, 설치와 검증 도구 |
| [`tests/`](./tests) | 설정·설치 안전성과 skill 계약 회귀 테스트 |

개발 검증:

```bash
python3 -m unittest discover -s tests -v
```

---

<p align="center">
  <em>Sol은 방향을 잃지 않고, Luna는 경계를 넘지 않습니다.</em>
  <br/><br/>
  <strong>좋은 오케스트레이션은 역할보다 책임을 먼저 나눕니다.</strong>
</p>
