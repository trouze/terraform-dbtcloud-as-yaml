---
name: Intent vs Reality Architecture
overview: "Refactor the deploy generate pipeline around a first-class target intent artifact grounded in TF state. Default: keep + adopt all TF-managed resources. Source focus upserts. Target intent (with confirmation) is the top-priority winner. Orphans flagged for removal with notice. Unadoption via Match + Utilities UI."
todos:
  - id: target-intent-model
    content: "Create importer/web/utils/target_intent.py: TargetIntent dataclass, TargetIntentManager (load/save/compute), get_tf_state_resource_keys()"
    status: completed
  - id: target-intent-compute
    content: "Implement compute(): TF state keys as floor (default keep+adopt), upsert source focus, merge adoptions, apply removals, detect orphans"
    status: completed
  - id: target-intent-artifact
    content: Persist target-intent.json to deployment dir as first-class auditable artifact with full provenance
    status: completed
  - id: deploy-refactor
    content: Replace baseline-scanning in deploy.py with TargetIntentManager.compute() -> validated merged YAML
    status: completed
  - id: validate-coverage
    content: "Post-compute validation: every TF state key accounted for (retained, upserted, adopted, or explicitly removed)"
    status: completed
  - id: removal-intent-model
    content: "Add removal_intent to TargetIntent: set of keys flagged for removal from TF state, generates terraform state rm commands"
    status: completed
  - id: orphan-detection
    content: Detect TF state resources not in target account (via target fetch). Auto-flag for removal with notice, user confirms before state rm.
    status: completed
  - id: drift-resolution
    content: When target intent disagrees with TF state, surface drift with confirmation prompt before proceeding
    status: cancelled
  - id: unadoption-ui
    content: "Future: Add 'Remove from TF' action on Match tab + removal management on Utilities tab (like protection)"
    status: cancelled
  - id: unit-tests
    content: "Unit tests for target_intent.py: compute logic, orphan detection, disposition precedence, serialization round-trip"
    status: completed
  - id: integration-tests
    content: "Integration tests: deploy generate with target intent replacing baseline scanning, end-to-end YAML merge validation"
    status: completed
  - id: ui-smoke-tests
    content: "Playwright smoke tests: orphan warnings in deploy, removal flags in utilities, target intent artifact generation"
    status: completed
  - id: e2e-scenario-tests
    content: "E2E scenario tests: partial source + full TF state, orphan in state not in target, adoption + retention, removal flow"
    status: completed
isProject: false
---

# Intent vs Reality: Target Intent Architecture

## Problem Statement

The current deploy generate pipeline tries to reconstruct "what TF should manage" by scanning for baseline YAMLs (existing deployment YAML, normalization YAMLs). This is fragile -- if the baseline is corrupted or partial, Terraform destroys everything. The root cause: there is no first-class "target intent" artifact.

## Architecture: 4 Realities + 3 Intents

### Realities (data sources, read-only)

- **Source fetch** -- full normalized YAML from source dbt Cloud account
- **Target fetch** -- API snapshot of target account (`state.target_fetch.last_report_items_file`)
- **Terraform state** -- `terraform.tfstate` in `deployments/migration/` (ground truth of what TF manages)
- **Protection intent** -- `protection-intent.json` (user decisions about `prevent_destroy`)

### Intents (derived, mutable)

- **Source focus** -- filtered/selected subset of source fetch (`state.map.last_yaml_file`). Already working well.
- **Target intent** -- **NEW**: the complete set of resources TF should manage after `terraform apply`. This is the critical missing piece.
- **Protection overlay** -- compared against TF state to produce `moved` blocks. Already mostly working.

## Target Intent Computation

The target intent is computed by `compute_target_intent()`, a pure function:

```python
def compute_target_intent(
    tf_state_projects: set[str],       # project keys from terraform.tfstate
    source_focus_config: dict,          # parsed source focus YAML (filtered/selected)
    adopt_rows: list[dict],            # resources to adopt from target fetch
    removal_intent: set[str],          # resources explicitly marked for removal (new concept)
) -> TargetIntentResult:
    """
    Returns:
      - retained_keys: projects in TF state kept as-is (not in source focus, not removed)
      - upserted_keys: projects from source focus (added or updated)
      - adopted_keys: resources from target fetch being imported
      - removed_keys: resources explicitly removed from TF control
      - output_config: complete YAML config covering all retained + upserted + adopted
    """
```

### Precedence rules:

1. **TF state is the floor** -- every project key in `terraform.tfstate` defaults to "retain"
2. **Source focus upserts** -- source focus projects are added (new) or update (existing) the baseline
3. **Adoptions import** -- target fetch resources marked for adoption get import blocks
4. **Removals are explicit** -- only resources explicitly flagged for removal are excluded
5. **Protection is an overlay** -- applied after the YAML is composed, does not affect which resources are included

## Key Changes to [deploy.py](importer/web/pages/deploy.py)

### Replace the fragile baseline-scanning with TF-state-grounded intent

Currently (lines 1296-1396): scans for baseline YAMLs by file existence and project count heuristics.

Replace with:

1. **Read TF state project keys** directly from `terraform.tfstate` (fast JSON parse, no `terraform show`)
2. **Find the best available config for each TF-managed project** (from existing deployment YAML, normalization YAMLs, or source focus)
3. **Upsert source focus** into that baseline
4. **Validate** the output covers ALL TF state keys (minus explicit removals)
5. **Persist** the target intent as `deployments/migration/target-intent.json` for auditability

### New utility: `compute_target_intent()` in [importer/web/utils/target_intent.py](importer/web/utils/target_intent.py)

```python
def get_tf_state_project_keys(tfstate_path: Path) -> set[str]:
    """Parse terraform.tfstate JSON to extract all managed project keys."""

def compute_target_intent(
    tfstate_path: Path,
    source_focus_yaml: str,
    baseline_yaml: Optional[str],   # existing deployment or normalization YAML
    adopt_rows: list[dict],
    removal_keys: set[str],
) -> dict:
    """
    Compute the complete target intent.
    Returns the merged YAML config + metadata about retained/upserted/adopted/removed.
    """

def validate_intent_coverage(
    intent_config: dict,
    tf_state_keys: set[str],
    removal_keys: set[str],
) -> list[str]:
    """
    Validate that intent covers all TF state keys.
    Returns list of warnings for any uncovered keys.
    """
```

### Persist the intent artifact: `target-intent.json`

```json
{
  "version": 1,
  "computed_at": "2026-02-04T...",
  "tf_state_keys": ["bt_data_ops_db", "bt_data_ops_dp", ...],
  "source_focus_keys": ["sse_dm_fin_fido"],
  "retained_keys": ["bt_data_ops_db", "bt_data_ops_dp", ...],
  "upserted_keys": ["sse_dm_fin_fido"],
  "adopted_keys": [],
  "removed_keys": [],
  "coverage_warnings": []
}
```

## What About Unadoption / Removal?

This is **not** implemented today and is a new concept. For now:

- Default policy: retain all TF-state resources (no destroys)
- Future: add a "Remove from TF" action on the Match page that adds keys to `removal_keys`
- Removal would generate `terraform state rm` commands, not `terraform destroy`

This can be a follow-up. The critical fix is establishing "retain all" as the default.

## Summary of Missing Pieces (from user's question)


| Gap                                 | Status   | Plan                                                                       |
| ----------------------------------- | -------- | -------------------------------------------------------------------------- |
| Default "retain all" policy         | Missing  | Core of this change -- TF state keys are the floor                         |
| Unadoption / removal intent         | Missing  | Stub the concept; implement later                                          |
| Target intent as persisted artifact | Missing  | New `target-intent.json`                                                   |
| Explicit composition function       | Missing  | New `compute_target_intent()`                                              |
| Conflict resolution precedence      | Implicit | Document in function; source focus wins for upserts                        |
| Orphan detection                    | Missing  | `validate_intent_coverage()` warns about TF-state resources with no config |


