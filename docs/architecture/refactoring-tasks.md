# Refactoring Task List — Workflow Alignment

Derived from the workflow mapping (`docs/architecture/workflow-mapping.md`).
Tracks what has been done and what remains.

---

## Priority 1: Shared Helper Consolidation (env, paths, subprocess)

### 1a. `get_terraform_env` — eliminate all duplicates

| File | Status | Notes |
|------|--------|-------|
| `adopt.py` | **DONE** | Delegated to `terraform_helpers.get_terraform_env` |
| `deploy.py` | **DONE** | Delegated to `terraform_helpers.get_terraform_env` |
| `destroy.py` | **DONE** | Now imports from `terraform_helpers` (was importing deploy's copy) |
| `utilities.py` | Already compliant | Was already importing from `terraform_helpers` |

### 1b. `resolve_deployment_paths` — eliminate all inline path resolution

| File | Status | Notes |
|------|--------|-------|
| `adopt.py:_get_terraform_dir` | **DONE** | Delegated to `resolve_deployment_paths` |
| `utilities.py:load_state_action` | **DONE** | Replaced inline resolution |
| `utilities.py:generate_all_pending` | **DONE** | Replaced inline resolution |
| `utilities.py:_resolve_tf_path` | **DONE** | Delegated to `resolve_deployment_paths` |
| `deploy.py` (~15 inline sites) | DEFERRED | Large page; requires careful audit of each usage |
| `destroy.py` (~6 inline sites) | DEFERRED | Same pattern, requires page-level refactor |

### 1c. `run_terraform_command` — replace raw `subprocess.run`

| File | Status | Notes |
|------|--------|-------|
| `adopt.py` (5 calls) | DEFERRED | Requires matching on_output callback wiring |
| `utilities.py` (3 calls) | DEFERRED | Requires TF action refactor |
| `deploy.py` (5 calls) | DEFERRED | Largest page, most calls |
| `destroy.py` (11 calls) | DEFERRED | Most calls of any page |

> The subprocess consolidation is deferred because each call site has
> page-specific output handling (terminal widgets, progress callbacks) that
> needs careful 1:1 mapping to `run_terraform_command`'s `on_output` callback.

---

## Priority 2: Pipeline Adoption

### 2a. Replace custom generation with `run_generate_pipeline`

| File | Status | Notes |
|------|--------|-------|
| `utilities.py:generate_all_pending` | PLANNED | Replace ~180 lines with pipeline call |
| `adopt.py` phases 3-4 | PLANNED | Replace with `run_generate_pipeline(include_adopt=True)` |
| `destroy.py` unprotect flow | PLANNED | Replace inline YAML + moved block gen |
| `deploy.py:_run_generate` | PLANNED | Replace custom generation |

---

## Priority 3: Reconcile Source Consistency

### 3a. Refresh reconcile state after apply

| File | Status | Notes |
|------|--------|-------|
| `utilities.py` | Already compliant | Refreshes via `_refresh_reconcile_state_from_terraform` |
| `adopt.py` | TODO | Add refresh after successful apply |
| `deploy.py` | TODO | Add refresh after successful apply |
| `destroy.py` | N/A | Destroy removes state, no reconcile needed |

### 3b. Use reconcile source for protection classification

| File | Status | Notes |
|------|--------|-------|
| `utilities.py` | Already compliant | Uses `reconcile_state_resources` |
| `destroy.py` | TODO | Currently uses YAML + `terraform state list` |

---

## Completed in This Iteration

1. `adopt.py`: `_get_terraform_env` → delegates to `terraform_helpers`
2. `adopt.py`: `_get_terraform_dir` → delegates to `resolve_deployment_paths`
3. `deploy.py`: `_get_terraform_env` → delegates to `terraform_helpers`
4. `destroy.py`: Import source changed from `deploy._get_terraform_env` to `terraform_helpers.get_terraform_env`
5. `utilities.py`: 3 inline path resolutions → `resolve_deployment_paths`
6. Created `docs/architecture/canonical-contracts.md`
7. Created `docs/architecture/workflow-mapping.md`
8. Created `.cursor/rules/canonical-workflow-contracts.mdc`
