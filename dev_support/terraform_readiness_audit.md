# Terraform Readiness Audit - Data Model Analysis

**Date:** 2025-11-21  
**Importer Version:** 0.3.3-dev

## Executive Summary

The importer data models (Pydantic) and API data capture are **sufficient** for Terraform resource creation. The issue is that the **normalizer is not extracting the right fields** from the captured data.

## Key Findings

### ✅ Data IS Being Captured

All necessary data for Terraform is present in the JSON snapshot's `metadata` fields. The importer successfully fetches:

- Service token `permission_grants` with `permission_set`, `project_id`, and `writable_environment_categories`
- Group `group_permissions`, `assign_by_default`, and `sso_mapping_groups`
- Notification `user_id`, `type` (numeric), `on_success/failure/cancel/warning` job lists, `external_email`, `slack_channel_id/name`

###  ❌ Normalization is Incomplete

The normalizer currently:
- Flattens `permission_grants` to a simple `scopes` array (losing structure)
- Ignores `group_permissions` entirely
- Doesn't map notification types correctly
- Doesn't extract connection provider-specific config from `details.config`

## Detailed Analysis by Resource

### 1. Service Tokens

**API Data (in `metadata`):**
```json
"permission_grants": [
  {
    "permission_set": "account_admin",
    "project_id": null,
    "writable_environment_categories": []
  }
]
```

**Current Model Fields:**
- ✅ `permission_sets: List[str]` - extracted
- ✅ `project_ids: List[int]` - extracted
- ❌ **Missing:** per-permission structure with `all_projects` flag

**Terraform Needs:**
```yaml
service_token_permissions:
  - permission_set: account_admin
    all_projects: true  # derived from project_id==null
    writable_environment_categories: []
```

**Fix Required:**
- Update normalizer to create `service_token_permissions` blocks from `metadata.permission_grants`
- Map `project_id: null` → `all_projects: true`
- Map `project_id: <num>` → `all_projects: false, project_id: <num>`

---

### 2. Groups

**API Data (in `metadata`):**
```json
"group_permissions": [],
"assign_by_default": true,
"sso_mapping_groups": []
```

**Current Model Fields:**
- ✅ `assign_by_default: Optional[bool]` - captured
- ✅ `sso_mapping_groups: List[str]` - captured
- ✅ `permission_sets: List[str]` - captured
- ❌ **Missing:** structured `group_permissions` from `metadata.group_permissions`

**Terraform Needs:**
```yaml
groups:
  - name: Everyone
    assign_by_default: true
    sso_mapping_groups: []
    group_permissions:
      - permission_set: developer
        all_projects: false
        project_id: 12345
        writable_environment_categories: [development, staging]
```

**Fix Required:**
- Update normalizer to extract `group_permissions` from `metadata.group_permissions`
- Include `assign_by_default` and `sso_mapping_groups` in output

---

### 3. Notifications

**API Data (in `metadata`):**
```json
"user_id": 103835,
"type": 4,  // 4=external email, 2=slack, 1=internal
"on_success": [542963],
"on_failure": [],
"on_cancel": [],
"on_warning": [],
"external_email": "will.sargent+test-email2@dbtlabs.com",
"slack_channel_id": null,
"slack_channel_name": null,
"state": 1
```

**Current Model Fields:**
- ✅ `notification_type: Optional[int]` - captured
- ✅ `user_id: Optional[int]` - captured
- ✅ `on_success/failure/cancel: List[int]` - captured
- ❌ **Missing:** `on_warning` field in model
- ❌ **Missing:** `external_email`, `slack_channel_id`, `slack_channel_name` fields

**Terraform Needs:**
```yaml
notifications:
  - user_id: 103835
    notification_type: 4  # numeric, not string
    external_email: will.sargent+test-email2@dbtlabs.com
    on_success: [542963]
    on_failure: []
    on_cancel: []
    on_warning: []
    state: 1
```

**Fix Required:**
- Add `on_warning`, `external_email`, `slack_channel_id`, `slack_channel_name` to `Notification` model
- Update fetch logic to extract these from API metadata
- Update normalizer to output all fields (not just type/target)

---

### 4. Connections

**API Data (in `details`):**
```json
"details": {
  "adapter_version": "databricks_v0",
  "config": null,  // ⚠️ Provider-specific config would be here
  "is_ssh_tunnel_enabled": false,
  "oauth_configuration_id": null,
  "private_link_endpoint_id": null
}
```

**Issue:** The `config` field is `null` in our sample. This suggests:
1. Connection config might not be retrievable via the API we're using
2. OR we're not fetching the right endpoint to get full connection details

**Terraform Needs:**
```yaml
connections:
  - name: Snowflake Production
    snowflake:  # provider-specific block
      account: my-account
      database: MY_DATABASE
      warehouse: MY_WAREHOUSE
    oauth_configuration_id: 12345  # optional
    private_link_endpoint_id: "ple_abc123"  # optional
```

**Fix Required:**
- Research dbt Cloud API to find endpoint that returns full connection config
- Update fetch logic to retrieve provider-specific configuration
- Update normalizer to map `adapter_version` → provider block name
- Parse `config` JSON into provider-specific fields

---

## Implementation Priority

### Phase 1: Quick Wins (Fields Already in Metadata)
1. **Notifications** - All data is present, just need to update normalizer
2. **Service Tokens** - Restructure from `metadata.permission_grants`
3. **Groups** - Extract from `metadata.group_permissions`

### Phase 2: Model Updates
4. Add missing fields to `Notification` model
5. Update fetch logic to populate new fields

### Phase 3: Research & Complex
6. **Connections** - Research API for provider-specific config endpoint
7. Parse and structure connection configuration by provider type

---

## Recommended Next Steps

1. ✅ **Audit complete** - All data models reviewed
2. 🔄 **Research connections API** - Find endpoint with full config
3. **Update normalizer** - Fix service tokens, groups, notifications structure
4. **Update models** - Add missing notification fields
5. **Test** - Validate YAML against Terraform schemas

---

## Notes

- The `metadata` field in the JSON snapshot is a **goldmine** - it contains all the raw API responses
- The current normalizer is doing a "flat" extraction instead of a "structured" extraction
- This is a **normalizer problem**, not a **data capture problem**
- Connection provider-specific config may require additional API endpoint or may be redacted for security

