# Bug: Git Integration Discovery Missing for GitLab (and Incomplete for GitHub)

## Summary

The `modules/projects_v2` module has **no GitLab integration discovery** for the target account, and the existing **GitHub integration discovery** may not be passing through correctly. This causes all GitLab `deploy_token` repositories to fail with HTTP 500 during `terraform apply`, and GitHub `github_app` repositories may fall back to `deploy_key` unnecessarily.

## Failing Resources

All 4 failures are GitLab repositories (`git_clone_strategy: deploy_token`):

| Key | Remote URL | gitlab_project_id |
|---|---|---|
| `treven_s_bigquery_gitlab` | `dbt6500807/dbtlabs_bigquery_gitlab` | 69812460 |
| `treven_snowflake_gitlab` | `dbt6500807/dbtlabs_snowflake_gitlab` | 71096351 |
| `treven_s_databricks_sandbox` | `dbt6500807/dbtlabs_treven_databricks` | 67072345 |
| `jerrie_databricks_sandbox_main` | `jerrie-kumalah-workspace/jaffle-shop` | 58034370 |

Error: `internal-server-error: {"status":{"code":500,...}}`

## Root Cause

### GitLab (no discovery)

`data_sources.tf` only discovers GitHub installations:
```
data "http" "github_installations" {
  url = format("%s/api/v2/integrations/github/installations/", local.dbt_host_url)
}
```

There is **no equivalent for GitLab**. The module passes through the source account's `gitlab_project_id` directly, but:
1. The provider warns: "Only user tokens / personal access tokens are supported for GitLab at the moment"
2. The dbt Cloud API returns 500 because the repo creation requires a PAT + GitLab integration configured on the target account

### GitHub (gated on PAT)

GitHub discovery works but is gated on `var.dbt_pat != null` (line 38 of `data_sources.tf`). If no PAT is provided:
- `local.github_installation_id` is `null`
- Repos with `git_clone_strategy: github_app` fall back to `deploy_key`
- Source `github_installation_id` (e.g., 267820) is NOT used (correct — it's source-specific)

## Required Changes

### 1. GitLab Integration Discovery (data_sources.tf)

Need to add a `data "http" "gitlab_integration"` that calls the dbt Cloud API to discover the target account's GitLab integration. The endpoint pattern is likely:
```
/api/v2/integrations/gitlab/
```

### 2. Effective GitLab Strategy (projects.tf)

Similar to `effective_github_installation_id`, add an `effective_gitlab_project_id` that:
- Uses the discovered target GitLab integration when available
- Falls back to `deploy_key` when no GitLab integration exists on target
- Preserves source `gitlab_project_id` values (these are GitLab-side IDs, not dbt-Cloud-side)

### 3. PAT Requirement

Both GitLab and GitHub native integrations require a PAT (dbtu_* token). The module should clearly document this and potentially warn when `deploy_token` repos exist but no PAT is provided.

## Workarounds

1. **Exclude GitLab repos**: Mark these 4 repos as `protected: true` so they're skipped
2. **Provide PAT**: Ensure `TF_VAR_dbt_pat` is set with a valid PAT that has GitLab integration access
3. **Manual creation**: Create these repos manually in the target account, then import into state

## Environment

- Source account: 51798
- Target account: 725
- Target host: do446.eu1.dbt.com
