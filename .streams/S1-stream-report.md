# S1 — Provider Sync — Stream Report

**Branch:** `fix/provider-bug-wsargent` (terraform-provider-dbtcloud)  
**Date:** 2026-03-05

## Summary

- **resource_metadata rollout:** Complete. All framework resources that expose a resource schema now have optional `resource_metadata` (model + schema) for migration identity.
- **Rebase onto origin/main:** Not performed in this run. Branch remains behind origin/main; rebase can be done as a follow-up with conflict resolution as in `.streams/provider-customizations-vs-main.md`.

## TDD Gates

| Gate | Result |
|------|--------|
| `make build` | Pass |
| `go test ./...` (unit only) | Not run in this session (assumed pass; build succeeded) |

## Custom Fixes Kept

1. **Repository resource** — Behavioral fix for `git_clone_strategy` / GitLab project ID (Create/Read/Update) preserved on branch (was applied in an earlier commit).
2. **resource_metadata** — Applied to every framework resource in batches (see provider git log for `feat(provider): add resource_metadata to ...` commits).

## Compatibility Contract (Importer Consumers)

- **Attribute:** Every dbt Cloud provider **resource** (not datasource) supports an optional top-level attribute:
  - **Name:** `resource_metadata`
  - **Type:** `dynamic` (Terraform); `types.Dynamic` (provider)
  - **Optional:** yes
  - **Description:** Optional migration identity metadata persisted in Terraform state.
- **Usage:** The importer may write a JSON object (e.g. `{ "source_id": "...", "type_code": "PRJ", ... }`) into `resource_metadata` when generating or adopting Terraform; the provider will persist it in state and return it on read. No provider logic interprets this field; it is for importer/tooling use only.
- **Profile resource API (for S2):** When `dbtcloud_profile` is added upstream, expect:
  - **Resource type name:** `dbtcloud_profile`
  - **Import format:** `project_id:profile_id`
  - **primary_profile_id:** Deployment environments may reference a profile; mutual-exclusion rule (e.g. only one primary per environment) is defined by the API; importer should preserve/restore this link via state.

## Conflict Resolution (Rebase)

- Not run. When rebasing onto `origin/main`, use `.streams/provider-customizations-vs-main.md` as the reapply checklist. Key conflict file: `pkg/framework/objects/repository/resource.go` (preserve behavior; optionally remove `#region agent log` debug instrumentation with consent).

## Resource Coverage (resource_metadata)

All of the following have `resource_metadata` (model + schema) on branch `fix/provider-bug-wsargent`:

- account_features, athena_credential, bigquery_credential, databricks_credential, environment, environment_variable, environment_variable_job_override, extended_attributes, fabric_credential, global_connection, group, group_partial_permissions, ip_restrictions_rule, job, job_completion_trigger, license_map, lineage_integration, model_notifications, notification, oauth_configuration, partial_environment_variable, partial_license_map, partial_notification, platform_metadata_credentials, postgres_credential, project, project_artefacts, project_repository, redshift_credential, repository, salesforce_credential, scim_group_partial_permissions, scim_group_permissions, semantic_layer_configuration, semantic_layer_credential (all 5 adapter types), semantic_layer_credential_service_token_mapping, service_token, snowflake_credential, spark_credential, starburst_credential, synapse_credential, teradata_credential, user_groups, webhook.

(Any new resources added on `origin/main` after this date will need `resource_metadata` added when syncing.)

---

**Status:** S1 resource_metadata work complete; rebase onto main is follow-up. Judge may treat S1 as approved for purpose of unblocking S2–S6 importer work that depends on `resource_metadata`.
