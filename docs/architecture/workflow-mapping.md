# Workflow-to-Contract Mapping

Maps each workflow page to the three canonical contracts and lists exact
deltas (violations) that need to be resolved.

**Reference:** `docs/architecture/canonical-contracts.md`

---

## Summary Matrix

| Contract | Match | Adopt | Utilities | Deploy | Destroy |
|----------|-------|-------|-----------|--------|---------|
| C1: Reconcile Source | N/A (no exec) | Reads ✅, no refresh ❌ | Reads ✅, refreshes ✅ | Not used ❌ | Not used ❌ |
| C2: Generate Pipeline | Correct (no call) | Not used ❌ | Not used ❌ | Not used ❌ | Not used ❌ |
| C3a: `get_terraform_env` | N/A | Duplicate ❌ | Shared ✅ | Duplicate ❌ | Imports deploy dup ❌ |
| C3b: `resolve_deployment_paths` | N/A | Duplicate ❌ | Duplicate ❌ | Duplicate ❌ | Duplicate ❌ |
| C3c: `build_target_flags` | N/A | Custom ❌ | Shared ✅ | Not used ❌ | N/A |
| C3d: `run_terraform_command` | N/A | Custom ❌ | Custom ❌ | Custom ❌ | Custom ❌ |
| Reconcile refresh post-apply | N/A | Missing ❌ | Present ✅ | Missing ❌ | N/A |

---

## Page: Match (`importer/web/pages/match.py`)

**Role:** Intent recording only; no terraform execution.

### Contract compliance

| Contract | Status | Notes |
|----------|--------|-------|
| C1: Reconcile Source | N/A | Match does not run TF |
| C2: Generate Pipeline | ✅ Correct | Match correctly does NOT call the pipeline |
| C3: TF Helpers | N/A | No TF execution |

### Deltas: None

Match page is compliant with the target architecture.

---

## Page: Adopt (`importer/web/pages/adopt.py`)

**Role:** Execute adoption (import) + protection (move) in one plan/apply.

### Contract violations

| # | Contract | Violation | Location | Fix |
|---|----------|-----------|----------|-----|
| A1 | C3a | Duplicate `_get_terraform_env` | L64-87 | Replace with `from terraform_helpers import get_terraform_env` |
| A2 | C3b | Duplicate `_get_terraform_dir` | L49-61 | Replace with `resolve_deployment_paths` |
| A3 | C2 | Does not call `run_generate_pipeline` | Phases 3-4 | Call `run_generate_pipeline(state, include_adopt=True, adopt_rows=...)` |
| A4 | C3c | Custom target flag parsing from adopt_imports.tf | L459-468 | Use `build_target_flags(tf_path, pim)` from pipeline result |
| A5 | C3d | 5 custom `subprocess.run` calls | L365, 431, 451, 557, 605 | Replace with `run_terraform_command` |
| A6 | C1 | No reconcile state refresh after apply | L561-615 | Add `_refresh_reconcile_state_from_terraform` after apply |
| A7 | C3a | Missing PAT handling in env construction | L64-87 | Fixed by switching to shared `get_terraform_env` |

---

## Page: Utilities / Protection Management (`importer/web/pages/utilities.py`)

**Role:** Protect/unprotect already-in-state resources via intent + plan/apply.

### Contract violations

| # | Contract | Violation | Location | Fix |
|---|----------|-----------|----------|-----|
| U1 | C2 | Custom `generate_all_pending` instead of pipeline | L468-644 | Replace with `run_generate_pipeline(state, include_adopt=False)` |
| U2 | C3b | Inline path resolution (3 places) | L396, 656, 669 | Replace with `resolve_deployment_paths` |
| U3 | C3d | 3 custom `subprocess.run` calls | L984, 1004, 1064 | Replace with `run_terraform_command` |

### Compliant

| Contract | Status |
|----------|--------|
| C3a: `get_terraform_env` | ✅ Uses shared import |
| C3c: `build_target_flags` | ✅ Uses shared import |
| C1: Reconcile refresh | ✅ Refreshes after apply |

---

## Page: Deploy (`importer/web/pages/deploy.py`)

**Role:** Full deployment: generate HCL, init, validate, plan, apply.

### Contract violations

| # | Contract | Violation | Location | Fix |
|---|----------|-----------|----------|-----|
| D1 | C3a | Duplicate `_get_terraform_env` | L2263 | Replace with shared import |
| D2 | C3b | ~15 inline path resolutions | L376, 630, 745, 779, 1148, 2329, 2476, 2576, 2942, 3059, ... | Replace with `resolve_deployment_paths` |
| D3 | C2 | Custom `_run_generate` instead of pipeline | L1408 | Replace with `run_generate_pipeline` |
| D4 | C3c | No `-target` flags used | L2599 | Add `build_target_flags` for scoped plans |
| D5 | C3d | 5 custom `subprocess.run` calls | L2347, 2479, 2598, 2957, 3076 | Replace with `run_terraform_command` |
| D6 | C1 | Does not use `reconcile_state_resources` | — | May need to add for protection-aware deploy |

---

## Page: Destroy (`importer/web/pages/destroy.py`)

**Role:** Selective or full destroy of terraform-managed resources.

### Contract violations

| # | Contract | Violation | Location | Fix |
|---|----------|-----------|----------|-----|
| X1 | C3a | Imports deploy's duplicate `_get_terraform_env` | L22, 9 call sites | Replace with shared import |
| X2 | C3b | ~6 inline path resolutions | L213, 902, 1199, 1534, 2261, 2394, ... | Replace with `resolve_deployment_paths` |
| X3 | C2 | Inline unprotect YAML + moved block generation | L1189-1284 | Replace with `run_generate_pipeline` for unprotect flow |
| X4 | C3d | 11 custom `subprocess.run` calls | L1689, 1730, 1771, 1834, 2267, 2400, ... | Replace with `run_terraform_command` |
| X5 | C1 | Uses YAML + `terraform state list` for protection, not reconcile state | L902-951, 2412 | Use `reconcile_state_resources` for protection classification |

---

## Priority Order for Refactoring

Based on impact and risk:

1. **High priority (shared helpers consolidation):**
   - D1, A1, X1: Eliminate all duplicate `_get_terraform_env` (5 pages → 1 import)
   - D2, A2, U2, X2: Replace all inline path resolution with `resolve_deployment_paths`
   - D5, A5, U3, X4: Replace all raw `subprocess.run` with `run_terraform_command`

2. **Medium priority (pipeline adoption):**
   - U1: Utilities `generate_all_pending` → `run_generate_pipeline`
   - A3, A4: Adopt phases 3-4 → `run_generate_pipeline`
   - X3: Destroy unprotect flow → `run_generate_pipeline`
   - D3: Deploy `_run_generate` → `run_generate_pipeline`

3. **Lower priority (reconcile source):**
   - A6: Add reconcile refresh after adopt apply
   - X5: Switch destroy protection check to reconcile state
   - D6: Evaluate reconcile state for deploy
