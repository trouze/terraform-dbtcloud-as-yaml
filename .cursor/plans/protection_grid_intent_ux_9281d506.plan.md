---
name: Protection Grid Intent UX
overview: Implement dense-baseline protection intent management on Protection Management, with shared resource-detail dialog reuse from Set Target Intent, standard filters, and bulk intent editing for both existing and state-only resources.
todos:
  - id: row-model-unification
    content: "Extend existing _build_state_protection_map + merge logic (Contract 1: reconcile_state_resources); add intent_origin field; do NOT rewrite from scratch"
    status: pending
  - id: dense-baseline
    content: Implement dense baseline fill via ProtectionIntentManager.set_intent with source='dense_baseline', reason='auto-fill from TF state'; intent_origin derivable from source field
    status: pending
  - id: filters-selection
    content: Add standard filters, selected-only toggle, reset, shown/total counters; use resolve_deployment_paths for any path access; default hide-unprotected
    status: pending
  - id: bulk-intent-edit
    content: Add single/bulk protect/unprotect/reset for selected rows; persist intents ONLY (no inline generation); generation stays on 'Generate All Pending' button per Contract 2
    status: pending
  - id: shared-detail-dialog
    content: Reuse show_match_detail_dialog via adapter (_build_dialog_payload_from_protection_row); populate drift_status from state vs intent comparison
    status: pending
  - id: tests-and-validation
    content: Extend test_state_visibility_regression + test_contract_enforcement; add test_protection_grid_actions.py; reuse mock_state fixtures from test_terraform_helpers_equivalence
    status: pending
isProject: false
---

# Protection Management Intent Editing Plan

## Objectives

- Make Protection Management a first-class intent editing surface (not only a status view).
- Adopt a **dense baseline** model: every TF-state resource is representable with an intent row.
- Reuse the existing Set Target Intent resource-detail dialog via shared code path.
- Add standard grid filter/selection UX and bulk intent actions.

## Architectural Constraints (from Workflow Alignment Matrix)

- **Contract 1 — Reconcile Source:** All row data must derive from `state.deploy.reconcile_state_resources`. No direct `terraform.tfstate` parsing.
- **Contract 2 — Generate Entrypoint:** Artifact generation goes through `run_generate_pipeline()`. Bulk intent edits persist intents only; generation is a separate user action.
- **Contract 3 — Terraform Helpers:** Use `resolve_deployment_paths` for path resolution, `get_terraform_env` for env, `run_terraform_command` for subprocess. No inline duplicates.
- `**set_intent()` signature:** Requires `source` and `reason` arguments (added in prior iteration). Dense baseline must use `source="dense_baseline"`.
- **Canonical docs:** `docs/architecture/canonical-contracts.md`, `docs/architecture/workflow-mapping.md`, `.cursor/rules/canonical-workflow-contracts.mdc`

## Scope and Key Files

- Grid/data model and actions: [importer/web/pages/utilities.py](importer/web/pages/utilities.py)
- Shared detail dialog and tabs: [importer/web/components/entity_table.py](importer/web/components/entity_table.py)
- Match page call pattern reference: [importer/web/pages/match.py](importer/web/pages/match.py)
- Match grid callback wiring reference: [importer/web/components/match_grid.py](importer/web/components/match_grid.py)
- Intent manager behavior (dense baseline persistence hooks): [importer/web/utils/protection_intent.py](importer/web/utils/protection_intent.py)
- Shared helpers (paths, env, subprocess): [importer/web/utils/terraform_helpers.py](importer/web/utils/terraform_helpers.py)
- Tests (existing — extend, don't duplicate):
  - [importer/web/tests/test_state_visibility_regression.py](importer/web/tests/test_state_visibility_regression.py) — row merge and summary parity
  - [importer/web/tests/test_contract_enforcement.py](importer/web/tests/test_contract_enforcement.py) — no inline path/env violations
  - [importer/web/tests/test_terraform_helpers_equivalence.py](importer/web/tests/test_terraform_helpers_equivalence.py) — shared helper fixtures
  - [importer/web/tests/test_adopt_protection.py](importer/web/tests/test_adopt_protection.py), [importer/web/tests/test_intent_key_consistency.py](importer/web/tests/test_intent_key_consistency.py)
  - New: `importer/web/tests/test_protection_grid_actions.py` for bulk intent edit logic

## Implementation Steps

### Step 1. Normalize protection rows into a unified model

- **Extend** the existing `_build_state_protection_map` and state-only merge logic in `_create_protection_management_section` (do NOT rewrite from scratch — this code is covered by `test_state_visibility_regression.py`).
- Row source: `state.deploy.reconcile_state_resources` (Contract 1). All supported types: `PRJ`, `REP`, `PREP`, `GRP`, `ENV`, `JOB`, `CONN`.
- Each row carries:
  - `intent_protected` (explicit or default-unprotected)
  - `state_protected` (from TF state `lifecycle.prevent_destroy`)
  - `yaml_protected` (when available, derived via `resolve_deployment_paths` YAML file)
  - `intent_origin` (`explicit` vs `baseline`) — derivable from the `source` field on the persisted intent
  - `status` (`Pending Generate`, `Pending TF Intents`, `State Mismatch`, `Synced`, `State Only`)

### Step 2. Implement dense baseline persistence strategy

- Add a baseline sync path in `utilities.py` that writes intents for all in-scope state rows (default unprotected unless protected in state/yaml rules).
- Use `ProtectionIntentManager.set_intent(key, protected, source="dense_baseline", reason="auto-fill from TF state")` — the `source` and `reason` args are **required** (enforced since the prior iteration).
- `intent_origin` is derived from the `source` field: `source == "dense_baseline"` → baseline, anything else → explicit.
- Keep existing reconciliation semantics; baseline fill is additive and deterministic.
- After implementation, verify `test_contract_enforcement.py` and `test_state_visibility_regression.py` still pass.

### Step 3. Add standard filters and selection controls

- In `utilities.py`, align with other grid pages (Destroy/Match patterns):
  - type filter with counts
  - status filter with counts
  - search quick filter
  - selected-only toggle
  - reset filters action
  - "X shown / Y total" badge
- Default view behavior: hide unprotected rows initially (toggleable).
- Use `resolve_deployment_paths` (Contract 3) for any new path access. Do not inline path resolution.

### Step 4. Add single-row and bulk intent editing from grid

- Add actions for selected rows:
  - Set intent Protect
  - Set intent Unprotect
  - Clear/Reset selected to baseline rule
- Ensure actions work for both pre-existing intent rows and baseline/state-only rows.
- **Intent persistence only** — bulk actions call `ProtectionIntentManager.set_intent()` and refresh the grid/cards. They do NOT trigger generation or pipeline runs. Generation remains a separate user action via the "Generate All Pending" button (Contract 2).
- After update: persist intent manager, refresh row model, keep counters and cards consistent.

### Step 5. Reuse shared resource detail dialog from Set Target Intent

- Wire a "View details" action in utilities grid to call `show_match_detail_dialog` from `entity_table.py`.
- Build adapter via `_build_dialog_payload_from_protection_row(row, state)` that maps protection grid row shape → dialog input shape (`source_data`, `grid_row`, `state_resource`).
- Populate `drift_status` from `state_protected` vs `intent_protected` comparison (e.g., `"in_sync"` or `"protection_mismatch"`).
- Prefer opening on intent/protection-relevant tab/context (shared code path, no duplicate dialog implementation).

### Step 6. Validation and consistency checks

- Verify card counts and grid rows are parity-consistent.
- Verify typed-key consistency and no regressions in status transitions.
- Verify `test_contract_enforcement.py` passes (no inline path/env violations introduced).
- Verify `test_state_visibility_regression.py` passes (row merge and summary parity intact).
- Keep current debug instrumentation active until user confirms final closeout.

## Test Plan

- **Extend** `test_state_visibility_regression.py` with cases for dense baseline fill (all state rows get intent rows).
- **Extend** `test_contract_enforcement.py` to verify no new inline path/env construction in `utilities.py`.
- **New** `test_protection_grid_actions.py`: unit tests for bulk protect/unprotect/reset logic on mixed explicit + baseline rows.
- **Reuse** `mock_state` and `intent_manager` fixture patterns from `test_terraform_helpers_equivalence.py`.
- Unit tests for filter defaults and selected-only behavior.
- Integration/UI-level checks for:
  - detail dialog opens from protection grid and displays protection intent/state context
  - default hide-unprotected behavior and toggle reveal
  - sync/generate/apply status transitions remain correct.

## Acceptance Criteria

- Protection grid can directly set intent for any visible resource.
- State-only resources are editable without first visiting another page.
- Detail dialog is shared with Set Target Intent path.
- Default view is focused (unprotected hidden) but reversible via filters.
- Counters, row state, and persisted intents remain consistent across reloads.
- All existing alignment tests (`test_contract_enforcement`, `test_state_visibility_regression`, `test_terraform_helpers_equivalence`, `test_cross_page_pipeline_consistency`) continue to pass.
- Bulk intent edits do NOT trigger inline generation (Contract 2 compliance).

