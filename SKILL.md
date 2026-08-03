---
name: lunaria
description: Use when a Sol primary agent has bounded, independently verifiable coding subtasks that can be delegated without giving up requirements, architecture, or final integration decisions.
---

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

## 사전 점검

- 메인 모델이 정확히 `gpt-5.6-sol`인지 확인한다. 메인 모델을 식별할 수 없거나
  다르면 엄격한 Lunaria 토폴로지가 비활성임을 보고한다.
- 위임 전마다 이 스킬 디렉터리를 기준으로 관리자의 기본 템플릿과 기본 대상을 사용해
  `python3 -B scripts/manage_luna_worker.py check`를 실행한다. 역할 표시만으로는 이
  사전 점검을 충족하지 않는다. `check`가 exit 0을 반환할 때만 진행한다.
- `luna_worker` 커스텀 역할을 확인한다. 다른 모델이나 역할로 자동 대체하지 않는다.
- 성공한 `check` 뒤 첫 실제 `luna_worker` spawn을 discovery, 모델, Max entitlement
  점검으로 취급한다. Luna 또는 Max를 사용할 수 없으면 보고하고, Sol 단독 진행은 그
  선택이 명시된 뒤에만 허용한다.
- 공개된 native spawn 또는 details metadata에서 역할, 모델, reasoning effort를
  확인할 수 있으면 `luna_worker`, `gpt-5.6-luna`, `max`와 대조한다. 관측하지 못한 값을 추정하지 않는다.
  내부 rollout 또는 세션 파일을 읽지 않는다.
- `check`가 설치 누락이나 drift를 보고하면 `plan`을 실행한다. 명시적 승인 뒤에만
  `install`을 실행하고, `verify`와 `check`를 차례로 다시 실행한 뒤 위임한다.

## 위임과 실행

하나의 목표, 명시적인 허용·제외 범위, 충분한 입력, 구체적인 산출물, 필수 검증,
에스컬레이션 조건이 모두 있을 때만 위임한다. 요구사항, 교차 아키텍처, 의존성 순서,
공유 설정, 외부 부수 효과 결정, 최종 통합은 Sol이 유지한다. Luna는 목표를 확장할 수 없다.
Luna는 아키텍처 결정을 내릴 수 없다.

읽기 전용 패킷은 병렬 실행할 수 있다. 병렬 쓰기는 경로가 독점적이고 공유 lockfile,
생성물, 포맷 출력, 마이그레이션, Git 상태가 없을 때만 허용한다. 논리 경로가 소유권의
기준이며 worktree나 branch 분리는 쓰기 범위가 겹치는 작업을 정당화하지 않는다.
겹치는 모든 쓰기는 직렬화한다. 다른 작업자나 사용자의 변경을 되돌리지 않는다.

Luna는 다음 Git 상태를 변경하는 모든 작업을 실행할 수 없다: working tree, index,
refs, branches, tags, stash, worktrees. 금지 작업은 다음을 포함하되 이에 한정되지 않는다:
`git commit`, `git add`, `git reset`, `git merge`, `git rebase`, `git stash`,
`git clean`, `git cherry-pick`, `git revert`, `git tag`, `git switch`,
`git checkout`, `git push`, `git worktree`. Luna는 다른 에이전트를 생성할 수 없다.

## 작업 패킷

Objective:
Allowed scope:
Excluded scope:
Files and ownership:
Interfaces:
Inputs and known decisions:
Deliverable:
Required validation:
Escalate when:

모든 필드를 채운 뒤에만 `luna_worker` 커스텀 역할을 spawn한다. 의존성이 있는 작업은
단계별로 직렬 실행한다. 수락된 패킷 범위 안에서만 워커를 조정하고, 범위를 벗어나면
중단한다. 실패 근거를 반영해 패킷을 수정하며 같은 패킷을 그대로 재시도하지 않는다.
쓰기 충돌은 파괴적 정리 없이 Sol에서 해결한다.

## 결과 수용

다음 결과 계약을 요구한다.

Status: complete | blocked | needs_decision
Summary:
Files changed:
Validation run and results:
Unresolved risks:
Decision requested from Sol:

워커 보고는 검증 전까지 주장으로 취급한다. Sol은 실제 파일, 전체 diff, 허용 범위와
변경 범위를 확인하고 검증 명령을 직접 다시 실행한다. 검증 증거 없는 `complete`는
미완료로 처리한다. 짧은 발췌가 꼭 필요한 증거인 경우를 제외하고 원시 워커 로그를
메인 컨텍스트에 넣지 않는다.

## 설정 안전성

`scripts/manage_luna_worker.py`는 이 SKILL.md를 기준으로 찾는다. `check`, `plan`,
`verify`는 읽기 전용이다. `install`은 선택한 에이전트 대상만 쓰고 기본적으로 교체를
거부하며 `~/.codex/config.toml`을 수정하지 않는다.
