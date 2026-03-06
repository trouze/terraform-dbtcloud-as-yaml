# Release Notes — v0.26.0

**Date:** 2026-03-05  
**Type:** Minor release  
**Previous:** v0.25.0

---

## Summary

Fixes the deploy_token pre-flight probe so verified repositories actually use `deploy_token` in the Terraform plan (previously the probe verified correctly but the module gate was never opened). Also improves GitHub App installation matching for multi-org accounts, fixes SAO/cost_optimization_features mapping, and cleans up job completion trigger management.

---

## Changes

### Fixed

- **GitLab deploy_token tfvars not written** — The pre-flight probe verified deploy_token access via API create+delete but never wrote the result to the generated Terraform files. The generated `main.tf` now includes a `variable "enable_gitlab_deploy_token"` declaration and passes it to the module. A `gitlab_probe.auto.tfvars` file is written with `enable_gitlab_deploy_token = true` when the probe keeps any repos as deploy_token.

- **Job completion triggers** — Removed the separate `dbtcloud_job_completion_trigger` resource block from `job_triggers.tf`. The provider manages triggers inline via the job's `job_completion_trigger_condition` attribute (which is in `ignore_changes`). The standalone resource was causing conflicts.

- **SAO / cost_optimization_features mapping** — Jobs with `cost_optimization_features = ["state_aware_orchestration"]` in the YAML now correctly map to `force_node_selection = false` on the `dbtcloud_job` resource, instead of attempting to set the unsupported `cost_optimization_features` attribute directly.

### Added

- **GitHub installation owner matching** — `data_sources.tf` now parses the GitHub installations response to build a map of owner login to installation ID. This supports accounts connected to multiple GitHub organizations where repos need to be matched to the correct installation.

- **Deploy UI local provider override** — When a project `.terraformrc` file exists (e.g., for provider debugging with a local binary), `terraform_helpers.py` now sets `TF_CLI_CONFIG_FILE` so Terraform Init/Plan/Apply from the UI automatically pick up the dev override.

---

## Files Changed

| File | Change |
|------|--------|
| `importer/web/pages/deploy.py` | Capture probe result, write `gitlab_probe.auto.tfvars` |
| `importer/yaml_converter.py` | Add `enable_gitlab_deploy_token` variable and module arg to generated `main.tf` |
| `importer/web/utils/terraform_helpers.py` | Set `TF_CLI_CONFIG_FILE` when `.terraformrc` exists |
| `modules/projects_v2/data_sources.tf` | GitHub installation owner-based matching |
| `modules/projects_v2/job_triggers.tf` | Replaced standalone trigger resource with inline comment |
| `modules/projects_v2/jobs.tf` | SAO mapping via `cost_optimization_features` → `force_node_selection` |

---

## Verification

```bash
cat importer/VERSION
# Expected: 0.26.0

python3 -c "from importer import get_version; print(get_version())"
# Expected: 0.26.0
```

For deploy_token fix: run Generate + Plan on an account with GitLab repos and confirm `git_clone_strategy = "deploy_token"` appears in the plan output for verified repos.
