# January Next Steps: Repository & Connection Linking

**Created:** 2025-12-20  
**Status:** Planning  
**Priority:** High

---

## Problem Statement

After the initial migration, projects are created but:
1. **Repositories** are not linked to projects (missing `github_installation_id` from target account)
2. **Connections** are created but environments may not be referencing the correct target connection IDs
3. **Git integrations** require target-account-specific IDs that cannot be migrated from source

---

## Root Cause Analysis

### Repository Linking Issues

The dbt Cloud repository resource requires **target-account-specific** integration IDs:

| Git Provider | Required Field | Source Account Value | Target Account Requirement |
|--------------|---------------|---------------------|---------------------------|
| GitHub | `github_installation_id` | Source's GitHub App installation ID | **Must use target's GitHub App installation ID** |
| GitLab | `gitlab_project_id` | Source's GitLab project ID | Can use same value if same GitLab project |
| Azure DevOps | `azure_active_directory_project_id`, `azure_active_directory_repository_id` | Source's ADO IDs | Can use same value if same ADO org |

**Key Insight:** The `github_installation_id` is the ID of the GitHub App installation in the dbt Cloud account, NOT the GitHub organization ID. Each dbt Cloud account has its own installation ID.

### How to Get GitHub Installation ID

Per the [dbt Cloud provider documentation](https://registry.terraform.io/providers/dbt-labs/dbtcloud/latest/docs/resources/repository):

```hcl
# Requires a USER token (PAT), not a service token
data "http" "github_installations_response" {
  url = format("%s/v2/integrations/github/installations/", var.dbt_host_url)
  request_headers = {
    Authorization = format("Bearer %s", var.dbt_token)
  }
}

locals {
  github_installation_id = jsondecode(data.http.github_installations_response.response_body)[0].id
}
```

**Requirement:** User must authenticate with a PAT (`dbtu_*`) to retrieve GitHub installation IDs.

### Connection Linking Issues

Connections are created via `dbtcloud_global_connection`, but environments need to reference the **target account's connection IDs**, not source IDs.

Current flow:
1. `dbtcloud_global_connection.connections` creates new connections in target
2. `dbtcloud_environment.environments` should reference `dbtcloud_global_connection.connections[key].id`

This should work currently via `connection_key` → `dbtcloud_global_connection.connections[key].id` mapping in `resolve_connection_id` local.

---

## Implementation Plan

### Phase 1: Target Account Integration Discovery (Automated)

**Goal:** Automatically retrieve target account integration IDs during Terraform init/plan.

#### 1.1 Add HTTP Data Source for GitHub Installations

**File:** `modules/projects_v2/data_sources.tf`

```hcl
# Retrieve GitHub App installations from target account
# NOTE: Requires PAT token (dbtu_*), not service token
data "http" "github_installations" {
  count = var.dbt_pat != null ? 1 : 0
  
  url = format("%s/v2/integrations/github/installations/", var.dbt_host_url)
  request_headers = {
    Authorization = format("Bearer %s", var.dbt_pat)
  }
}

locals {
  # Parse GitHub installations response
  github_installations = var.dbt_pat != null ? jsondecode(data.http.github_installations[0].response_body) : []
  
  # Get primary GitHub installation ID (first one, typically there's only one)
  github_installation_id = length(local.github_installations) > 0 ? local.github_installations[0].id : null
}
```

#### 1.2 Add PAT Variable for Integration Discovery

**File:** `modules/projects_v2/variables.tf`

```hcl
variable "dbt_pat" {
  description = "dbt Cloud Personal Access Token (dbtu_*) for retrieving integration IDs. Required for GitHub App integration."
  type        = string
  default     = null
  sensitive   = true
}

variable "dbt_host_url" {
  description = "dbt Cloud host URL (e.g., https://cloud.getdbt.com)"
  type        = string
  default     = "https://cloud.getdbt.com"
}
```

#### 1.3 Update Repository Resource to Use Target GitHub ID

**File:** `modules/projects_v2/projects.tf`

```hcl
resource "dbtcloud_repository" "repositories" {
  for_each = local.projects_with_repositories

  project_id = dbtcloud_project.projects[each.key].id
  remote_url = local.resolve_repository[each.key].remote_url

  # Use target account's GitHub installation ID (not source)
  github_installation_id = (
    try(local.resolve_repository[each.key].git_clone_strategy, "") == "github_app" ?
    local.github_installation_id :  # Use discovered target ID
    null
  )

  git_clone_strategy = try(
    local.resolve_repository[each.key].git_clone_strategy,
    "deploy_key"  # Default to deploy key if not specified
  )

  # ... rest of resource
}
```

### Phase 2: GitLab Integration Support

#### 2.1 Add GitLab Project Discovery

If the target account has GitLab integration, we may need to discover GitLab project IDs. However, GitLab project IDs are tied to the GitLab repository itself, not the dbt Cloud account, so source values should work.

**Action:** Document that GitLab integration requires:
- Same GitLab organization/project access in target account
- GitLab integration configured in target account

### Phase 3: Azure DevOps Integration Support

#### 3.1 Add ADO Data Sources

The provider already has data sources for Azure DevOps:

```hcl
data "dbtcloud_azure_dev_ops_project" "my_devops_project" {
  name = "my-devops-project"
}

data "dbtcloud_azure_dev_ops_repository" "my_devops_repo" {
  azure_dev_ops_project_id = data.dbtcloud_azure_dev_ops_project.my_devops_project.id
  name                     = "my-repo"
}
```

**Action:** Add logic to use ADO data sources when `git_clone_strategy = "azure_active_directory_app"`.

### Phase 4: Connection Validation & Debugging

#### 4.1 Add Connection ID Output Validation

**File:** `modules/projects_v2/outputs.tf`

```hcl
output "connection_mapping" {
  description = "Debug: Connection key to ID mapping"
  value = {
    for key, conn in dbtcloud_global_connection.connections :
    key => {
      id   = conn.id
      name = conn.name
    }
  }
}

output "environment_connections" {
  description = "Debug: Environment to connection mapping"
  value = {
    for key, env in dbtcloud_environment.environments :
    key => {
      environment_id = env.id
      connection_id  = env.connection_id
    }
  }
}
```

### Phase 5: E2E Test Script Updates

#### 5.1 Add PAT Support to E2E Test

**File:** `test/run_e2e_test.sh`

- Add `DBT_TARGET_PAT` environment variable
- Pass PAT to Terraform via `TF_VAR_dbt_pat`
- Add warning if PAT not provided for GitHub repositories

#### 5.2 Add Integration Discovery Phase

Add a new phase to the E2E test to:
1. Check for GitHub installations in target account
2. Warn if no GitHub installation found and repositories use `github_app` strategy
3. Suggest fallback to `deploy_key` strategy if no PAT available

---

## Implementation Checklist

### Required Changes

- [ ] **Add `dbt_pat` variable** to root module and projects_v2 module
- [ ] **Add `dbt_host_url` variable** to modules (if not already present)
- [ ] **Add HTTP data source** for GitHub installations discovery
- [ ] **Update repository resource** to use target GitHub installation ID
- [ ] **Add fallback logic** for repositories without GitHub integration
- [ ] **Update E2E test script** to support PAT for integration discovery
- [ ] **Add validation outputs** for debugging connection/repository issues

### Documentation Updates

- [ ] **Update README** with PAT requirements for GitHub integration
- [ ] **Add troubleshooting guide** for repository linking issues
- [ ] **Document supported Git integration strategies**

### Testing

- [ ] **Test GitHub App integration** with target account PAT
- [ ] **Test deploy_key fallback** when no PAT provided
- [ ] **Test connection linking** end-to-end
- [ ] **Verify environments reference correct connections**

---

## Alternative Approaches

### Option A: Pre-Flight Integration Check (Recommended)

Add a `--check-integrations` flag to the E2E test that:
1. Calls target account API to list available integrations
2. Compares with source account repositories
3. Warns about integration mismatches
4. Suggests manual setup steps

### Option B: Interactive Integration Configuration

Add interactive prompts during normalize phase:
1. Detect repository integration types from source
2. Prompt user for target integration IDs
3. Save to `.env` or config file

### Option C: Deploy Key Fallback (Simplest)

Default all repositories to `deploy_key` strategy:
- Works without integration setup
- Requires manual deploy key configuration in Git provider
- Less automated CI/CD integration

---

## API Endpoints Reference

### GitHub Installations

```
GET /api/v2/integrations/github/installations/
Authorization: Bearer <user_token>

Response:
[
  {
    "id": 267820,
    "access_tokens_url": "https://api.github.com/..."
  }
]
```

### GitLab Integrations

```
GET /api/v2/integrations/gitlab/
Authorization: Bearer <user_token>
```

### Azure DevOps Projects

Use data source `dbtcloud_azure_dev_ops_project`:
```hcl
data "dbtcloud_azure_dev_ops_project" "project" {
  name = "project-name"
}
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| PAT required for GitHub integration | Medium | Document requirement, provide deploy_key fallback |
| Different GitHub installation IDs | High | Auto-discover target IDs via API |
| GitLab project not in target account | Medium | Warn user, require manual setup |
| ADO integration not configured | Medium | Use data sources to verify |

---

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: GitHub Discovery | 4-6 hours | HTTP provider, PAT token |
| Phase 2: GitLab Support | 2-4 hours | GitLab API access |
| Phase 3: ADO Support | 2-4 hours | ADO data sources |
| Phase 4: Connection Validation | 2-3 hours | Debug outputs |
| Phase 5: E2E Updates | 3-4 hours | PAT variable, warnings |
| Documentation | 2-3 hours | All phases complete |

**Total:** 15-24 hours

---

## Next Actions

1. **Immediate:** Add `dbt_pat` and `dbt_host_url` variables to modules
2. **Immediate:** Add HTTP data source for GitHub installations
3. **Week 1:** Update repository resource to use target GitHub ID
4. **Week 1:** Update E2E test script with PAT support
5. **Week 2:** Add ADO/GitLab integration support
6. **Week 2:** Documentation updates

---

## Related Issues

- Repository `github_installation_id` is account-specific, not transferable
- Provider requires PAT for integration discovery (service token insufficient)
- Connection IDs should be working via key-based references

---

## References

- [dbt Cloud Repository Resource](https://registry.terraform.io/providers/dbt-labs/dbtcloud/latest/docs/resources/repository)
- [dbt Cloud Azure DevOps Data Source](https://registry.terraform.io/providers/dbt-labs/dbtcloud/latest/docs/data-sources/azure_dev_ops_project)
- [dbt Cloud API - GitHub Installations](https://docs.getdbt.com/dbt-cloud/api-v2)

