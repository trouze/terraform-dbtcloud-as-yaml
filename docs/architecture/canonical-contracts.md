# Canonical Workflow Contracts

This document defines the three canonical shared contracts that all intent-driven
workflows (adopt, protect, deploy, destroy) must consume. No page may implement
its own variant of these contracts.

**Source PRD:** [43.03 -- Unified Protect & Adopt Pipeline](../../prd/43.03-Unified-Protect-Adopt-Pipeline.md)

---

## Contract 1: Reconcile Source

**Canonical source:** `state.deploy.reconcile_state_resources`
(populated from `terraform show -json` via `terraform_state_reader.parse_state_json`)

### Rules

1. **One source for all decisions.** UI status cards, mismatch detection,
   grid row data, artifact generation, and sync decisions must all derive
   from `reconcile_state_resources`.

2. **No parallel parsing.** Pages must NOT parse `terraform.tfstate` directly
   when `reconcile_state_resources` is loaded. The only exception is the
   pipeline's initial `read_tf_state_addresses()` call when reconcile data
   is unavailable.

3. **Refresh after mutation.** After any successful `terraform apply` or
   `terraform plan` with no changes, the reconcile source must be refreshed
   from `terraform show -json`, persisted, and the UI reloaded.

4. **Dense representation.** Every resource in reconcile state that is
   protection-capable (element codes `PRJ`, `REP`, `PREP`, `GRP`) must be
   representable in intent grids, even when no explicit intent exists.

### Key format

Reconcile rows use `element_code` + `resource_index` as their natural key.
When projected into intent-space, keys are formatted as `TYPE:resource_index`
(e.g. `PRJ:sse_dm_fin_fido`, `GRP:member`).

### Consumers

| Consumer | File | Usage |
|----------|------|-------|
| Protection status cards | `utilities.py:_create_protection_status_section` | Count protected/unprotected |
| Protection grid | `utilities.py:_create_protection_management_section` | Merge intent + state rows |
| Mismatch detection | `utilities.py` | Compare YAML vs state |
| Generate pipeline | `generate_pipeline.py:run_generate_pipeline` | Build moved blocks |
| Destroy classification | `destroy.py:_run_terraform_destroy_all` | Split protected/unprotected |
| Deploy plan/apply | `deploy.py` | Resource targeting |

---

## Contract 2: Generate Entrypoint

**Canonical entrypoint:** `generate_pipeline.run_generate_pipeline()`
in `importer/web/utils/generate_pipeline.py`

### Rules

1. **Single pipeline for all pages.** Match, Adopt, Utilities, and any future
   intent pages must call `run_generate_pipeline()` for artifact generation.
   No page may have its own baseline merge, HCL regeneration, or moved-block
   generation code.

2. **Headless by design.** The pipeline has no NiceGUI imports, no UI side
   effects. Progress is reported via the `on_progress` callback.

3. **Idempotent reruns.** Running the pipeline twice with the same inputs
   must produce identical output.

4. **Clear stale artifacts.** When computed deltas are empty, the pipeline
   must explicitly clear derived files (`protection_moves.tf`,
   `adopt_imports.tf`) to prevent stale operations.

### Signature

```python
async def run_generate_pipeline(
    state: AppState,
    *,
    include_adopt: bool = False,
    adopt_rows: list[dict] | None = None,
    include_protection_moves: bool = True,
    merge_baseline: bool = True,
    regenerate_hcl: bool = True,
    on_progress: Callable[[str], None] | None = None,
    is_cancelled_fn: Callable[[], bool] | None = None,
) -> PipelineResult:
```

### Page call patterns

| Page | Call |
|------|------|
| Match | Does NOT call pipeline. Records intents only. |
| Adopt | `run_generate_pipeline(state, include_adopt=True, adopt_rows=...)` |
| Utilities (Protection Mgmt) | `run_generate_pipeline(state, include_adopt=False)` |
| Deploy | Uses pipeline result artifacts for plan/apply |

---

## Contract 3: Terraform Helpers

**Canonical module:** `importer/web/utils/terraform_helpers.py`

### Rules

1. **One implementation per helper.** Pages must NOT have their own
   `_get_terraform_env()`, path resolution, or target-flag construction.
   All pages import from `terraform_helpers`.

2. **No duplicated env construction.** `deploy.py:_get_terraform_env`,
   `match.py:_get_terraform_env`, and `adopt.py:_get_terraform_env` must
   be replaced with calls to `terraform_helpers.get_terraform_env()`.

3. **Target flags from artifacts.** `build_target_flags()` reads from
   `protection_moves.tf` and `adopt_imports.tf` on disk. It must be called
   after the generate pipeline has written those files.

### Exported functions

| Function | Purpose |
|----------|---------|
| `resolve_deployment_paths(state)` | Returns `(tf_path, yaml_file, baseline_yaml_path)` |
| `get_terraform_env(state)` | Builds subprocess env dict with TF_VAR_* |
| `build_target_flags(tf_path, pim)` | Builds `-target` flag list |
| `run_terraform_command(cmd, tf_path, env)` | Async subprocess wrapper |
| `read_tf_state_addresses(tf_path)` | Parses tfstate for address set |

### Known violators (to be consolidated)

| Duplicate | Location | Action |
|-----------|----------|--------|
| `deploy.py:_get_terraform_env` | L2263 | Replace with `terraform_helpers.get_terraform_env` |
| `match.py` path resolution | L270-276 | Replace with `resolve_deployment_paths` |
| `adopt.py:_get_terraform_env` | L64-87 | Replace with `terraform_helpers.get_terraform_env` |
| `utilities.py` inline path resolution | L656-662 | Replace with `resolve_deployment_paths` |

---

## Contract Enforcement

These contracts are enforced via:

1. **Cursor rule:** `.cursor/rules/intent-workflow-guardrails.mdc`
2. **Cursor rule:** `.cursor/rules/state-key-conventions.mdc`
3. **Tests:** `test_cross_page_pipeline_consistency.py`
4. **Code review:** any new page-specific generation logic requires explicit
   justification in the PR description.
