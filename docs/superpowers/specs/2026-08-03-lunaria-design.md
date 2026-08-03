# Lunaria Skill Design

## Summary

`lunaria` is a reusable Codex skill that keeps `gpt-5.6-sol` in the primary
thread as orchestrator and delegates only bounded, independent work to a custom
`gpt-5.6-luna` agent using `model_reasoning_effort = "max"`.

The repository root is the skill package. The skill includes an explicit setup
utility for installing and validating `luna_worker`; ordinary orchestration
does not modify Codex configuration.

## Goals

- Keep requirements, architecture decisions, integration, and final validation
  in the Sol primary thread.
- Move noisy, well-bounded analysis, review, implementation, and test work into
  Luna Max subagent threads.
- Prevent scope drift, overlapping writes, nested delegation, and silent model
  substitution.
- Install `luna_worker` without overwriting unrelated Codex configuration.
- Detect missing, incompatible, or drifted configuration before delegation.

## Non-goals

- Replacing Sol as the primary agent.
- Letting Luna decide product requirements or cross-cutting architecture.
- Automatically changing `~/.codex/config.toml`.
- Automatically committing, rebasing, pushing, or changing branches.
- Guaranteeing model entitlement when an account does not expose
  `gpt-5.6-luna` or `max` reasoning.

## Package Layout

```text
lunaria/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   └── luna-worker.toml
├── scripts/
│   └── manage_luna_worker.py
└── tests/
    └── test_manage_luna_worker.py
```

No README, changelog, or duplicate quick-reference file is included. Runtime
policy stays in `SKILL.md`; deterministic setup behavior stays in the script.

## Roles

### Sol primary agent

Sol owns:

- user intent, constraints, and success criteria;
- requirement and architecture decisions;
- task decomposition and dependency ordering;
- delegation eligibility and task packets;
- steering or stopping workers;
- review of worker evidence, diffs, and test results;
- integration and the final user response.

### `luna_worker`

`luna_worker` is a leaf worker. It may analyze, review, implement, or test only
inside the task packet supplied by Sol. It must not spawn another agent, broaden
the goal, make cross-cutting decisions, or perform Git publication operations.

The custom agent file uses the current standalone-agent schema:

```toml
name = "luna_worker"
description = "Leaf Luna Max worker for bounded, independent work delegated by Sol."
model = "gpt-5.6-luna"
model_reasoning_effort = "max"
developer_instructions = """
Execute only the supplied task packet. Respect allowed and excluded scope.
Return needs_decision before editing when requirements, architecture, or scope
are unclear. Do not spawn agents or perform Git publication operations.
Report changed files, validation evidence, risks, and decisions needed by Sol.
"""
```

Sandbox and approval settings are intentionally omitted so the worker inherits
the parent turn's live policy.

## Delegation Decision

Before delegation, Lunaria confirms that the primary thread is running Sol. If
the active primary model cannot be identified or is not Sol, the skill does not
pretend the topology is active or try to change the current thread's model. It
reports the mismatch and asks for a new Sol task when strict Lunaria operation
is required.

Sol delegates only when every required condition is true:

1. The task has one concrete objective.
2. Allowed scope and excluded scope are explicit.
3. Inputs are sufficient without making product or architecture assumptions.
4. Completion can be demonstrated with named evidence or checks.
5. The task is independently completable and does not block on another worker.
6. Its writes, if any, have exclusive ownership and no shared generated output.

Sol retains work when requirements are ambiguous, the change crosses major
module boundaries, shared state or common configuration is involved, external
side effects need judgment, or the correct solution changes the overall goal.

Read-only work may run in parallel. Write work may run in parallel only when
owned paths are disjoint and neither task can modify shared lockfiles, generated
artifacts, global format output, migrations, or Git state. Otherwise Sol runs
write tasks serially.

## Task Packet

Every delegation supplies this contract:

```text
Objective:
Allowed scope:
Excluded scope:
Inputs and known decisions:
Deliverable:
Required validation:
Escalate when:
```

The packet describes the desired result, not Sol's hidden chain of thought.
The allowed scope names concrete modules or paths when file ownership matters.

## Worker Result Contract

Luna returns:

```text
Status: complete | blocked | needs_decision
Summary:
Files changed:
Validation run and results:
Unresolved risks:
Decision requested from Sol:
```

Raw logs remain in the worker thread unless a short excerpt is necessary as
evidence. A `complete` result without validation evidence is not accepted as
complete by Sol.

## Orchestration Flow

1. **Preflight:** Confirm the primary thread is Sol and the custom agent is
   discoverable with the pinned Luna model and Max reasoning effort. Static
   checks validate configuration; the first spawn is the entitlement check.
2. **Classify:** Separate Sol-owned decisions from delegable work.
3. **Partition:** Build independent task packets and identify read/write sets.
4. **Dispatch:** Spawn `luna_worker` only for eligible packets, up to the
   runtime's available concurrency.
5. **Observe:** Steer a worker when its task remains valid but needs a bounded
   correction. Stop it when it breaches scope.
6. **Collect:** Wait for all workers required by the current dependency stage.
7. **Verify:** Inspect evidence and diffs, then rerun proportionate checks in
   the primary thread when risk warrants it.
8. **Integrate:** Resolve dependencies, make Sol-owned decisions, and produce
   one coherent final result.

Dependencies are staged rather than dispatched prematurely. A task that needs
another worker's result is created only after that result is accepted.

## Setup and Configuration Safety

`scripts/manage_luna_worker.py` provides explicit operations:

- `check`: read-only inspection of the Codex version, multi-agent availability,
  installed TOML syntax, required fields, pinned values, and drift;
- `plan`: print the exact target and unified diff without writing;
- `install`: create the personal agent file after an explicit approval in the
  calling Codex workflow;
- `verify`: repeat structural and environment checks after installation.

The default target is `~/.codex/agents/luna-worker.toml`. Tests override the
target with a temporary directory.

Installation rules:

- Never edit `~/.codex/config.toml`.
- Create a missing agents directory only during explicit installation.
- Refuse to replace an existing target by default.
- A requested replacement first writes a timestamped backup and displays the
  diff.
- Write through a temporary file and atomically rename it into place.
- Tell the user to start a new Codex task if agent discovery cannot refresh in
  the current task.

## Failure Handling

- **Agent missing or drifted:** show `check` output and the setup action; do not
  silently use a different worker.
- **Primary thread is not Sol:** report that strict Lunaria topology is inactive
  and require a new Sol task rather than changing the current model implicitly.
- **Model or Max effort unavailable:** report the capability failure. Sol may
  continue locally only when that choice is made explicit.
- **Ambiguous packet:** Luna returns `needs_decision` without editing.
- **Scope breach:** Sol stops the worker and reassesses the packet.
- **Worker failure:** retry once only for a clearly transient failure and with
  unchanged scope; otherwise Sol handles or reports the task.
- **Conflicting writes:** stop integration, preserve evidence, and resolve from
  the primary thread without destructive cleanup.
- **Approval required:** the worker does not bypass it; the request remains
  attributable to the originating task.

## Testing Strategy

### Skill behavior

Before authoring `SKILL.md`, run realistic prompts without the skill and record
whether the agent over-delegates, sends ambiguous packets, allows overlapping
writes, accepts unsupported conclusions, or substitutes models silently. After
authoring, run the same scenarios with `lunaria` and require compliance with the
delegation and result contracts.

Required scenarios include:

- an independent three-part read-only review;
- two apparently independent implementations that share a lockfile;
- a bounded implementation that uncovers an architecture decision;
- unavailable `luna_worker` configuration;
- a worker result that claims completion without validation evidence.

### Setup utility

Unit tests cover:

- missing, valid, invalid, and drifted agent files;
- refusal to overwrite;
- backup and replacement behavior;
- unified diff output;
- atomic installation into a temporary home;
- version and feature-command parsing;
- stable exit codes and actionable error messages.

### Deployment checks

- Run the setup utility unit tests.
- Run the skill validator against the repository root.
- Validate `agents/openai.yaml` against `SKILL.md` metadata.
- Run the behavior scenarios again with the completed skill.
- Confirm the repository contains no placeholders or unrelated files.

## Compatibility

The initial implementation targets the locally observed `codex-cli 0.144.1`
and the official standalone custom-agent requirements current on 2026-08-03:
`name`, `description`, and `developer_instructions`. `model` and
`model_reasoning_effort` pin Luna Max behavior.

The manager validates observable local capabilities instead of assuming that a
version number alone guarantees agent discovery or model entitlement.

## Acceptance Criteria

The skill is complete when:

- Codex can discover `lunaria` from valid skill metadata;
- setup can safely plan, install, and verify `luna_worker`;
- Sol delegates only contract-compliant bounded work;
- Luna escalates decisions and scope expansion without continuing edits;
- parallel write ownership cannot overlap by policy;
- Sol verifies worker evidence before integration;
- all automated and forward behavior tests pass.
