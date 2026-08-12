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

## 위임 경제성 게이트

위임 전에 작업 패킷 작성, 대기, 결과 수용과 재검증 비용을 포함해 Sol의 직접 처리와
비교한다. 예상 5분 미만이면서 기계적 단일 단계인 작업은 Sol이 직접 처리한다. 파일 수나
예상 시간 같은 숫자만으로 위임을 차단하지 않는다. 깊은 분석이나 독립 검증 가치가 그
비용보다 크면 작은 파일 범위도 위임할 수 있다.

위임할 때는 예상 소요 시간과 중단 조건, 워커·수용·통합 중 어느 검증 단계인지 작업
패킷에 기록한다. 중단 조건에 도달하면 반복 대기하지 말고 근거를 확인해 작업을 분할하거나
Sol로 회수한다.

## 오케스트레이션 소유권

위임 전에 현재 단계의 실행 오케스트레이터와 Lunaria 적용 모드를 선언한다. 한 단계의
실행 오케스트레이터는 하나뿐이며 작업 분배, 구현 순서, 리뷰, 재시도와 대기를 소유한다.
다른 skill이 작업별 구현자·리뷰어·수정 루프를 요구해도 각 skill의 에이전트 루프를
자동 합산하지 않는다.

다른 skill과 함께 쓰는 품질 게이트 모드에서는 Lunaria가 실행 예산을 소유한다. 다른
skill은 계획·기법만 제공하고 자체 fresh implementer, 작업별 reviewer, 수정·재리뷰
loop를 실행하지 않으며 작업별 리뷰를 중복하지 않는다. Sol 또는 경계가 명확한 Luna
implementer가 작업하고, Sol이 결과를 수용한 뒤 단계 경계에서 독립 리뷰어 1명을 사용한다.
여기서 단계는 개별 task가 아니라 사용자 가치나 milestone 하나를 완료해 하나의 통합 검증을
실행하는 작업 묶음이다. 첫 위임 전에 단계 경계와 리뷰 시작 조건을 작업 패킷에 고정한다.
외부 workflow의 final whole-branch reviewer가 필요하면 Lunaria의 단계 리뷰어 1명으로 간주하고
별도로 추가하지 않는다.

사용자가 다른 workflow의 전체 작업별 구현·리뷰 loop를 명시적으로 요구하면 Lunaria
조합 모드를 비활성화하고 그 workflow만 실행 오케스트레이터로 사용한다. 두 mode가 실행
예산을 동시에 소유할 수 없다. 요청만으로 어느 mode인지 확정할 수 없으면 첫 spawn 전에 선택을 요청한다.

사용자 요청이나 프로젝트 규칙이 소유자를 지정하면 이를 따른다. 어느 규칙이 구현·리뷰·
재시도를 소유하는지 불명확하면 첫 spawn 전에 결정을 요청한다.

## 동시성과 대기 예산

기본 활성 Luna 예산은 2명이다. 플랫폼 상한이 더 작으면 더 작은 값을 따른다. 독립 리뷰가
예정되고 세 번째 슬롯을 사용할 수 있으면 리뷰어용 슬롯으로 남긴다. 슬롯을 채우기 위해
불필요한 작업을 만들지 않으며 이 값은 전체 생성 수가 아니라 동시 활성 수다.

Sol이 진행할 수 있는 요구사항 정리, 수용 검증이나 통합 작업이 남아 있으면 먼저 수행한다.
더 진행할 일이 없을 때만 실행 중 worker들을 묶어서 한 번만 기다린다.
상태 변화 없이 개별 worker를 반복 polling하지 않는다. timeout 뒤에도 상태가 같으면 중단
조건과 남은 Sol 작업을 확인한 뒤 backoff하거나 회수한다.

결과 수용과 허용된 동일 목표 보정이 끝나면 완료된 worker를 닫아 슬롯을 반환한다.

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

Lunaria 단독 모드의 구현 단계 기본 리뷰 예산은 구현자 1명과 리뷰어 1명이다. 다른 skill과
함께 쓰는 품질 게이트 모드에서는 작업별 리뷰 대신 단계 리뷰 1명만 사용한다. Minor
지적만 남으면 Sol이 직접 수정하고 검증한다. Important 또는 Critical 문제가 해결되지 않았을 때만 같은
리뷰어에게 재리뷰를 한 번 요청한다. 그 뒤에도 해결되지 않으면 Sol이 작업을 분할하거나
결정을 요청하며 리뷰 루프를 계속하지 않는다.

완료된 워커에 대한 후속 지시는 동일 목표의 보정 1회로 제한한다. 목표, 허용 범위, 파일
소유권이나 산출물이 바뀌면 새 작업 패킷으로 새 `luna_worker`를 생성하거나 Sol이 직접
처리한다. 여러 목표를 계속 맡기는 catch-all worker로 재사용하지 않는다.

Luna는 다음 상태를 변경하는 모든 Git 작업/명령을 실행할 수 없다: working tree, index,
refs, branches, tags, stash, worktrees. 단, 수락된 작업 패킷의
`Files and ownership:`에 속한 일반 파일 편집은 허용된다.
금지 작업은 다음을 포함하되 이에 한정되지 않는다:
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
Expected duration and stop condition:
Validation tier:
Orchestration owner and mode:
Active worker and wait budget:
Stage boundary and review trigger:
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

검증은 다음 단계로 나눈다.

- 워커 검증: 작업 패킷의 좁은 `Required validation`을 실행한다.
- 수용 검증: Sol이 범위와 diff를 확인하고 같은 좁은 검증을 한 번 다시 실행한다.
- 단계 통합 검증: 수용된 작업을 모은 뒤 전체 test, typecheck, build를 단계당 한 번 실행한다.
- 최종 검증: commit, PR, 배포처럼 별도 workflow가 요구하는 최신 전체 검증을 실행한다.

실패 수정이나 새 변경이 없는 상태에서는 관련 변경 없이 동일한 전체 검증을 반복하지 않는다.
다른 skill이나 외부 계약이 최신 검증을 요구하면 최종 검증이 우선한다.

## 단계 경계

큰 통합 또는 PR 병합 뒤 다음 단계의 목표가 독립적이고 결정 문서, 계획, 테스트가 인계에
충분하면 새 Codex 작업을 제안한다. 사용자가 같은 작업 유지를 원하면 따르되, 원시 로그
대신 결정 문서와 미해결 위험만 다음 단계의 컨텍스트로 유지한다.

## Sol 오케스트레이션 요약

Lunaria를 사용한 단계가 끝나면 Sol이 다음 집계를 짧게 보고한다.

Delegations:
Completed / cancelled:
Worker elapsed:
Peak active workers:
Wait calls / unchanged timeouts:
Follow-ups / interrupts / retries:
Validation matrix:
Main-thread turns:
Token evidence:

집계는 공개된 도구와 모델 metadata만 사용한다. 토큰이나 턴 값을 관측할 수 없으면
`unavailable`로 기록한다. 즉, 관측할 수 없으면 `unavailable`이며 값을 추정하지 않는다.
이 요약을 위해 내부 rollout 또는 세션 파일을 읽지 않는다.

## 설정 안전성

`scripts/manage_luna_worker.py`는 이 SKILL.md를 기준으로 찾는다. `check`, `plan`,
`verify`는 읽기 전용이다. `install`은 선택한 에이전트 대상만 쓰고 기본적으로 교체를
거부하며 `~/.codex/config.toml`을 수정하지 않는다.
