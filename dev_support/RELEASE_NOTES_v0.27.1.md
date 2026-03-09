# Release Notes — v0.27.1

**Date:** 2026-03-09  
**Type:** Patch release  
**Previous:** v0.27.0

---

## Summary

Fixes three Terraform module issues discovered during plan/apply cycles after the v0.27.0 S4-S6 resource rollout: IP restrictions attribute syntax, errors_on_lint_failure drift on non-CI jobs, and project_artefacts 404 errors from source-to-target ID mismatch.

---

## Changes

### Fixed

- **IP restrictions `cidrs` attribute** (`modules/projects_v2/ip_restrictions.tf`):
  The `dbtcloud_ip_restrictions_rule` resource expects `cidrs` as a `SetNestedAttribute` (list of objects), not a dynamic block. Changed from `dynamic "cidrs" { ... }` to a list comprehension: `cidrs = [for c in ... : { cidr = c.cidr }]`. Applied to both `rules` and `protected_rules` resource blocks.

- **`errors_on_lint_failure` CI-only guard** (`modules/projects_v2/jobs.tf`):
  Non-CI jobs were planning `errors_on_lint_failure = false -> true` because the default fallback was `true`. Two fixes applied:
  1. Default fallback changed from `true` to `false`
  2. New `errors_on_lint_failure_effective` local introduced that forces `false` when `run_lint_effective` is `false` (i.e., for all non-CI jobs), consistent with the existing `run_lint` CI-only guard pattern.

- **`project_artefacts` 404 on apply** (`importer/normalizer/core.py` + `modules/projects_v2/project_artefacts.tf`):
  Two root causes:
  1. **Source job IDs in YAML**: The normalizer was storing raw source-account `docs_job_id` / `freshness_job_id` numeric IDs. These IDs don't exist on the target. Fix: normalizer now resolves and stores `docs_job_key` / `freshness_job_key` using the project's `job_id_to_key` mapping.
  2. **Project ID resolution**: The Terraform module only looked up project IDs from `dbtcloud_project.projects`, missing protected projects. Fix: uses `local.project_id_lookup` which merges both protected and unprotected project resources.
  3. **Job ID resolution**: New `job_id_by_key` local merges IDs from both `dbtcloud_job.jobs` and `dbtcloud_job.protected_jobs`, enabling `docs_job_key` → target job ID lookup.

---

## Affected Files

| File | Change |
|------|--------|
| `importer/VERSION` | `0.27.0` → `0.27.1` |
| `modules/projects_v2/ip_restrictions.tf` | `cidrs` dynamic block → list comprehension |
| `modules/projects_v2/jobs.tf` | `errors_on_lint_failure_effective` local + default fix |
| `modules/projects_v2/project_artefacts.tf` | `job_id_by_key` local + `project_id_lookup` + key-based resolution |
| `importer/normalizer/core.py` | Store `docs_job_key`/`freshness_job_key` instead of numeric IDs |

---

## Verification

Plan output after fixes:
- **1 to add** (net-new `bigquery` global connection)
- **21 to change** (19 CI jobs correcting `errors_on_lint_failure` drift, 1 environment, 1 job `run_lint`)
- **0 to destroy**
- No `ip_restrictions` errors
- No `project_artefacts` 404 errors
- No non-CI jobs affected by lint settings
