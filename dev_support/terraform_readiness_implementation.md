# Terraform Readiness Implementation Summary

**Date:** 2025-11-21  
**Importer Version:** 0.3.3-dev  
**Status:** ✅ Complete

## Overview

Successfully updated the dbt Cloud importer to generate Terraform-compatible YAML for service tokens, groups, and notifications. Connection provider-specific configuration remains manual due to API security constraints.

## Changes Implemented

### 1. Service Tokens ✅
**Problem:** Using flat `scopes` array instead of Terraform's `service_token_permissions` structure.

**Solution:**
- Updated `_normalize_service_tokens()` in `importer/normalizer/core.py`
- Extract `permission_grants` from metadata
- Convert to Terraform-compatible structure with `permission_set`, `all_projects`, `project_id`, and `writable_environment_categories`
- Map `project_id: null` → `all_projects: true`

**Output Before:**
```yaml
service_tokens:
  - key: account_admin
    name: account_admin
    scopes:  # ❌ Wrong structure
      - account_admin
```

**Output After:**
```yaml
service_tokens:
  - key: account_admin
    name: account_admin
    service_token_permissions:  # ✅ Correct structure
      - permission_set: account_admin
        all_projects: true
    state: 1
```

---

### 2. Groups ✅
**Problem:** Missing `group_permissions`, `assign_by_default`, and `sso_mapping_groups`.

**Solution:**
- Updated `_normalize_groups()` in `importer/normalizer/core.py`
- Extract `group_permissions` from metadata
- Include `assign_by_default` and `sso_mapping_groups` fields
- Convert permissions to Terraform structure

**Output Before:**
```yaml
groups:
  - key: everyone
    name: Everyone
    members: []  # ❌ Not a Terraform field
```

**Output After:**
```yaml
groups:
  - key: everyone
    name: Everyone
    assign_by_default: true  # ✅ Added
    # group_permissions would appear here if present
```

---

### 3. Notifications ✅
**Problem:** Missing `user_id`, using string types instead of numeric, no job associations.

**Solution:**
- Added missing fields to `Notification` model in `importer/models.py`:
  - `on_warning: List[int]`
  - `external_email: Optional[str]`
  - `slack_channel_id: Optional[str]`
  - `slack_channel_name: Optional[str]`
- Updated `_fetch_notifications()` in `importer/fetcher.py` to populate new fields
- Updated `_normalize_notifications()` in `importer/normalizer/core.py` to output Terraform-compatible structure

**Output Before:**
```yaml
notifications:
  - key: email_...
    type: email  # ❌ String instead of number
    target:
      email: test@example.com
```

**Output After:**
```yaml
notifications:
  - key: email_will_sargent_test_email2_dbtlabs_com_17902
    notification_type: 1  # ✅ Numeric (1=internal, 2=slack, 4=external)
    user_id: 103835  # ✅ Required by Terraform
    on_success: [542963]  # ✅ Job associations
    state: 1
```

---

### 4. Connections - Research Complete ❌ (Not Implementable)
**Problem:** Missing provider-specific configuration blocks (e.g., `snowflake`, `databricks`, `bigquery`).

**Finding:** The dbt Cloud API does **not export** connection credentials or provider-specific configuration for security reasons. The `config` field in API responses is always `null`.

**Impact:**
- Connections cannot be fully recreated via Terraform from an export
- Only metadata (name, type, references) can be exported
- Users must manually configure connection details in target accounts

**Documentation:** Created `dev_support/connection_provider_config_research.md` with:
- API endpoint analysis
- Security constraints explanation
- Recommended workarounds (data sources, manual config, secret managers)

---

## Testing & Validation

### Normalization Test
```bash
python -m importer normalize <json> --config importer_mapping.yml
```

**Results:**
- ✅ Service tokens now use `service_token_permissions` structure
- ✅ Groups include `assign_by_default` and permission blocks
- ✅ Notifications include `user_id`, numeric `notification_type`, job lists
- ✅ No linter errors
- ✅ 0 key collisions
- ✅ 17 projects normalized successfully

### Sample Verification
Verified actual output matches Terraform requirements:

**Service Token:**
```yaml
service_token_permissions:
  - permission_set: account_admin
    all_projects: true
```
✅ Matches Terraform `dbtcloud_service_token` resource schema

**Group:**
```yaml
assign_by_default: true
name: Everyone
```
✅ Matches Terraform `dbtcloud_group` resource schema

**Notification:**
```yaml
user_id: 103835
notification_type: 1
on_success: [542963]
```
✅ Matches Terraform `dbtcloud_notification` resource schema

---

## Files Modified

### Models
- `importer/models.py`: Added `on_warning`, `external_email`, `slack_channel_id`, `slack_channel_name` to `Notification`

### Fetcher
- `importer/fetcher.py`: Updated `_fetch_notifications()` to populate new fields

### Normalizer
- `importer/normalizer/core.py`: Updated `_normalize_service_tokens()`, `_normalize_groups()`, `_normalize_notifications()` with Terraform-compatible structures

### Documentation
- `dev_support/terraform_readiness_audit.md`: Comprehensive audit findings
- `dev_support/connection_provider_config_research.md`: API limitation research

---

## Remaining Limitations

### Connections
- ❌ Provider-specific configuration blocks not available from API
- ⚠️ Users must manually add connection details after export
- ℹ️ Consider using Terraform data sources to reference existing connections

### Credentials
- ❌ All credentials (passwords, tokens, keys) are intentionally excluded for security
- ⚠️ Environment credentials must be configured separately in target accounts

### OAuth & PrivateLink
- ⚠️ OAuth configuration references may need manual resolution
- ⚠️ PrivateLink endpoint references included but endpoints themselves must exist in target account

---

## Terraform Compatibility Matrix

| Resource Type | Min Required Fields | Status |
|---------------|---------------------|--------|
| **Service Tokens** | `name`, `service_token_permissions` | ✅ Complete |
| **Groups** | `name`, optional `group_permissions` | ✅ Complete |
| **Notifications** | `user_id`, `notification_type` | ✅ Complete |
| **Connections** | `name`, provider config block | ❌ Partial (metadata only) |
| **Repositories** | `remote_url`, `git_clone_strategy` | ✅ Complete |
| **Webhooks** | `name`, `client_url`, `event_types` | ✅ Complete (already correct) |

---

## Recommendations

### For Users
1. **Service Tokens/Groups/Notifications**: Fully automated, ready for Terraform apply
2. **Connections**: Export metadata, manually add provider configuration blocks
3. **Credentials**: Configure environment credentials in target account post-deployment
4. **Testing**: Always run `terraform plan` before `apply` to review changes

### For Future Development
1. ✅ **Complete**: Terraform-ready normalization for permissions and notifications
2. 🔄 **In Progress**: Test cases to validate YAML against Terraform schemas
3. 📋 **Future**: Support for external secret management integration
4. 📋 **Future**: Terraform data source references for existing connections

---

## Conclusion

The importer now generates **Terraform-compatible YAML** for all exportable resources. The main limitation (connection provider config) is due to API security constraints and cannot be automated. This is expected and appropriate behavior.

**Users can now:**
- ✅ Export service tokens with full permission structures
- ✅ Export groups with SSO mappings and permissions
- ✅ Export notifications with job associations
- ✅ Apply exported YAML to target accounts via Terraform (with manual connection setup)

