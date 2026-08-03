---
name: lunaria
description: Use when a Sol primary agent is handling a coding task with bounded, independent analysis, review, implementation, or validation work that may benefit from Luna Max subagents.
---

# Orchestrating with Lunaria

## Core rule

Sol decides and integrates. Luna executes bounded task packets as a leaf worker.

## Preflight

- Confirm the primary thread is Sol. If it is not Sol or cannot be identified,
  report that strict Lunaria topology is inactive.
- Confirm the `luna_worker` custom role is available. Never silently substitute
  another model or role.
- Treat the first `luna_worker` spawn as the model-entitlement check. If Luna or
  Max is unavailable, report it; continue in Sol only after that choice is explicit.
- If setup is missing or drifted, run this skill's manager in `check` and `plan`
  modes. Run `install` only after explicit approval, then run `verify`.

## Delegation gate

Delegate only when one objective, explicit allowed and excluded scope, sufficient
inputs, a concrete deliverable, required validation, and escalation conditions
are all present. Keep requirements, cross-cutting architecture, dependency
ordering, shared configuration, external side-effect decisions, and final
integration in Sol.

Read-only packets may run in parallel. Parallel writes require exclusive paths
and no shared lockfiles, generated artifacts, format output, migrations, or Git
state. Logical paths, not worktrees or branches, define ownership: separate
worktrees and planned conflict resolution never justify overlapping writes.
Serialize all overlapping writes. Luna never commits, rebases, pushes, switches
branches, or spawns agents.

## Task packet

Objective:
Allowed scope:
Excluded scope:
Inputs and known decisions:
Deliverable:
Required validation:
Escalate when:

Spawn the `luna_worker` custom role only after every slot is filled. Stage tasks
with dependencies. Steer a worker only within the accepted packet; stop it on a
scope breach. Retry once only for a clearly transient failure with unchanged
scope. Resolve write conflicts in Sol without destructive cleanup.

## Result acceptance

Require:

Status: complete | blocked | needs_decision
Summary:
Files changed:
Validation run and results:
Unresolved risks:
Decision requested from Sol:

Treat `complete` without validation evidence as incomplete. Inspect diffs and
rerun proportionate checks in Sol before integration. Keep raw worker logs out
of the main context unless a short excerpt is necessary evidence.

## Setup safety

Resolve `scripts/manage_luna_worker.py` relative to this SKILL.md. `check`,
`plan`, and `verify` are read-only. `install` writes only the selected agent
target, refuses replacement by default, and never edits `~/.codex/config.toml`.
