# Ralph Guardrails (Signs)

> Lessons learned from past failures. READ THESE BEFORE ACTING.

## Core Signs

### Sign: Read Before Writing
- **Trigger**: Before modifying any file
- **Instruction**: Always read the existing file first
- **Added after**: Core principle

### Sign: Test After Changes
- **Trigger**: After any code change
- **Instruction**: Run tests to verify nothing broke
- **Added after**: Core principle

### Sign: Commit Checkpoints
- **Trigger**: Before risky changes
- **Instruction**: Commit current working state first
- **Added after**: Core principle

---

## Learned Signs

(Signs added from observed failures will appear below)

### Sign: One Reconcile Truth
- **Trigger**: Any intent workflow computes mismatches, generates artifacts, or marks sync
- **Instruction**: Use a single canonical reconcile source for UI and generation; do not mix in-memory reconcile and direct tfstate parsing without explicit reconciliation
- **Evidence**: Protection mismatch drift and stale `moved` behavior despite successful plan/apply
- **Added after**: 2026-02-17 protection workflow incident

### Sign: Refresh After Sync
- **Trigger**: plan/apply indicates intent synchronization
- **Instruction**: Immediately refresh reconcile state from `terraform show -json`, persist, and reload UI before reporting final counters
- **Evidence**: Plan showed no changes while UI still reported non-zero mismatch/pending intents
- **Added after**: 2026-02-17 protection workflow incident

### Sign: Clear Empty Derived Artifacts
- **Trigger**: computed intent deltas are empty during generation
- **Instruction**: Explicitly clear generated move/import artifacts to avoid stale operations
- **Evidence**: stale `protection_moves.tf` produced recurring `Moved object still exists`
- **Added after**: 2026-02-17 protection workflow incident

### Sign: Summary/Table Parity
- **Trigger**: UI summary cards and table rows disagree on protected or pending counts
- **Instruction**: Build table rows from the same reconcile source as summary cards; include state-only rows and keep `Intent` and `State` distinct
- **Evidence**: `TF State Protected = 1` while intent table showed only synced rows and hid `GRP:member`
- **Added after**: 2026-02-18 protection visibility incident

