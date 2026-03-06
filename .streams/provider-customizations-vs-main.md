# Provider customizations vs main (reapply checklist for Path 1)

This document lists **all changes we have in the terraform-provider-dbtcloud branch that differ from `origin/main`**. These are treated as **our decisions / priority** for where the provider should go. Main is released, so we work from main and reapply these changes both technically (reset to main, then reapply) and politically (promote to upstream over time).

---

## 1. resource_metadata on all resources (critical)

**Decision:** Every provider resource must support an optional `resource_metadata` attribute (e.g. `types.Dynamic`) so the importer can store migration identity in Terraform state and it round-trips.

**Reapply (after reset to main):**

- For **every** resource in `pkg/framework/objects/*` that has a resource schema (i.e. appears in Terraform config/state):
  1. **Model:** Add `ResourceMetadata types.Dynamic \`tfsdk:"resource_metadata"\`` to the resource model struct.
  2. **Schema:** Add `"resource_metadata": resource_schema.DynamicAttribute{ Optional: true, Description: "Optional migration identity metadata persisted in Terraform state." }` to the resource schema.
  3. **CRUD:** Where state is built from API (Read, and sometimes Create/Update), preserve `resource_metadata` from plan or existing state so it is not lost (e.g. `state.ResourceMetadata = plan.ResourceMetadata` or copy from `req.State` in Read).

**Resources to cover (from current diff vs main; main may have added more – audit from main’s list):**

- account_features  
- athena_credential  
- bigquery_credential  
- databricks_credential  
- environment  
- environment_variable  
- environment_variable_job_override  
- extended_attributes  
- fabric_credential  
- global_connection  
- group  
- group_partial_permissions (schema only in diff)  
- ip_restrictions_rule  
- job  
- job_completion_trigger  
- license_map  
- lineage_integration  
- model_notifications  
- notification  
- oauth_configuration  
- partial_environment_variable, partial_license_map, partial_notification (schema only)  
- postgres_credential  
- project  
- project_artefacts  
- project_repository  
- redshift_credential  
- repository  
- scim_group_partial_permissions  
- scim_group_permissions  
- semantic_layer_configuration  
- semantic_layer_credential  
- semantic_layer_credential_service_token_mapping  
- service_token  
- snowflake_credential  
- spark_credential  
- starburst_credential  
- synapse_credential  
- teradata_credential  
- user_groups  
- webhook  

**Note:** After resetting to main, list all resources that have a resource schema (e.g. from provider registration or `*Resource()` in framework) and ensure every one has `resource_metadata` (model + schema + preservation in CRUD). New resources on main must get it too.

---

## 2. Repository resource fix (behavioral)

**Decision:** Correct behavior for `git_clone_strategy` and GitLab project ID so Terraform state and API stay consistent.

**Reapply (behavior only; do not reapply debug logging):**

**File:** `pkg/framework/objects/repository/resource.go`

1. **Create**
   - Use a separate variable for “GitLab project ID to send to Create API”: when `git_clone_strategy == "deploy_token"` use `plan.GitlabProjectID`, otherwise pass `0` (so we don’t send `gitlab_project_id` when strategy is e.g. `deploy_key`). (Current branch uses `createGitlabProjectID` for this.)
   - After Create, set `plan.GitCloneStrategy` from API only when `github_installation_id != 0`; otherwise leave `plan.GitCloneStrategy` as the plan value so we don’t overwrite with API’s normalized value.

2. **Read**
   - When API returns `git_clone_strategy == "github_app"` but repo has no `github_installation_id`, keep existing state’s `git_clone_strategy` instead of overwriting with `"github_app"` (avoids unnecessary drift).

3. **Update**
   - Same idea as Read: when API returns `github_app` but no `github_installation_id`, set `state.GitCloneStrategy = plan.GitCloneStrategy` instead of API value.

**Do not reapply:** Debug logging that writes to `.cursor/debug-*.log` or any file under the terraform-dbtcloud-yaml path. The stash contains this; drop it when reapplying.

---

## 3. Other changes in current branch vs main (categorize before reapply)

The full `git diff origin/main` in the provider touches many files. Below is a high-level categorization so you can decide what else to reapply beyond (1) and (2).

- **Job (execution, run_compare_changes, docs, tests):** job/model.go, job/resource.go, job/schema.go, job data sources, job docs, `resource_acceptance_cost_optimization_test.go`, `resource_acceptance_job_type_transitions_test.go`.  
  - Decide: from main we kept execution block and run_compare; if main already has equivalent behavior, no reapply; otherwise treat as our decision and reapply.

- **job_completion_trigger:** New resource (model, resource, schema).  
  - Decide: if this exists on main, skip; if it’s ours, reapply.

- **environment_variable_job_override:** New/updated resource.  
  - Decide: same as above.

- **service_token:** model.go, resource.go changes (e.g. `permissionRequest.AccountID = int64(accountID)` and any other fixes).  
  - Decide: reapply if these are correctness fixes we want to keep.

- **environment/resource.go:** Small changes (e.g. 15 lines).  
  - Likely resource_metadata preservation or similar; reapply if it’s part of (1) or a separate fix.

- **project/resource.go:** Small changes.  
  - Same as above.

- **scim_group_* / semantic_layer_*:** resource.go and resource_acceptance_test.go changes.  
  - Likely resource_metadata preservation or test updates; reapply with (1) or as needed.

- **global_connection/resource.go:** 40 lines added.  
  - Includes `writeDebugLogGlobalConn` and possibly ResourceMetadata preservation. Reapply only the behavioral part (e.g. preserving resource_metadata in Read if state is built from API); do not reapply debug logging.

- **Docs / CHANGELOG / provider registration:** PR_DESCRIPTION.md, CHANGELOG.md, docs/guides/4_job_attribute_conflicts.md, docs/data-sources/job.md, docs/data-sources/jobs.md, docs/resources/job.md, pkg/provider/framework_provider.go, pkg/dbt_cloud/*.  
  - Reapply only if they document or support the behaviors we’re keeping (e.g. job behavior, new resources).

---

## 4. Stash contents (repository only)

- **Stash name:** `stash@{0}: On fix/provider-bug-wsargent: local repo resource.go changes`
- **Contains:** repository/resource.go only.
  - **Keep when reapplying:** Read/Update GitCloneStrategy preservation (when API says `github_app` but no `github_installation_id`, preserve state/plan).
  - **Do not reapply:** All `#region agent log` blocks and any writes to `.cursor/debug-*.log`.

The **committed** version of repository/resource.go on our branch already has the Create-side fix (createGitlabProjectID + GitCloneStrategy from plan when no github_installation_id). The **stash** adds Read/Update preservation plus debug logging. So reapply = committed Create behavior + stash Read/Update behavior, minus debug.

---

## 5. Path 1 reapply order

1. **Reset provider branch to main**  
   e.g. `git checkout fix/provider-bug-wsargent && git reset --hard origin/main` (or create a new branch from main).

2. **Reapply resource_metadata (Section 1)**  
   For every resource (from main’s list): add model field, schema attribute, and preserve in Read/Create/Update where state is built from API.

3. **Reapply repository fix (Section 2)**  
   Apply behavioral changes only (Create + Read + Update), no debug logging. Use committed diff for Create and stash for Read/Update, with logging removed.

4. **Decide and reapply Section 3**  
   For job, job_completion_trigger, environment_variable_job_override, service_token, environment, project, scim_group_*, semantic_layer_*, global_connection behavior (no debug), and docs/CHANGELOG/provider: decide what is “our decision” and reapply only that.

5. **Build and test**  
   `make build`, run provider tests, and run importer against the new provider build.

---

## 6. Summary: “Our decisions” for upstream

- **resource_metadata:** Optional attribute on every resource for migration identity; must round-trip in state.
- **Repository:** Correct handling of `git_clone_strategy` and GitLab project ID on Create/Read/Update so state and API stay consistent.
- (Anything you choose from Section 3 as a deliberate product/behavior decision.)

Use this doc as the single checklist so we don’t lose functionality when we update and so we can promote the same set of changes upstream.

---

## 7. Path 1 execution status (after reset to main)

**Done:**
- Reset provider branch to `origin/main`.
- **resource_metadata:** Added model + schema to: account_features, athena_credential, bigquery_credential, environment, repository, global_connection, job, group, service_token, databricks_credential, webhook, user_groups, profile, connection_catalog_config, environment_variable, extended_attributes, ip_restrictions_rule, scim_group_permissions, scim_group_partial_permissions.
- **Repository fix:** Reapplied (Create: createGitlabProjectID + preserve plan GitCloneStrategy when no github_installation_id; Read/Update: preserve state/plan when API returns github_app but no github_installation_id). No debug logging.
- `make build` succeeds.

**Remaining (resource_metadata):**
- Add **schema** for the resources that already have the model (so config/state accept `resource_metadata`): global_connection, job, group, service_token, databricks_credential, webhook, user_groups, profile, connection_catalog_config, environment_variable, extended_attributes, ip_restrictions_rule, scim_group_permissions, scim_group_partial_permissions.
- Add **model + schema** to remaining resources: fabric_credential, license_map, lineage_integration, model_notifications, notification, oauth_configuration, platform_metadata_credentials, postgres_credential, project, project_artefacts, redshift_credential, salesforce_credential, snowflake_credential, spark_credential, starburst_credential, synapse_credential, environment_variable_job_override, group_partial_permissions, semantic_layer_*, etc.
- Optionally add Read/Create/Update preservation of `resource_metadata` where state is built from API.
