# Connection Provider Configuration - Research Findings

**Date:** 2025-11-21  
**API Version:** dbt Cloud v3

## Key Finding

**The dbt Cloud API does NOT export connection provider-specific configuration or credentials.**

## Evidence

### API Endpoint Used
```
GET /api/v3/accounts/{account_id}/connections/
```

### Sample Response
```json
{
  "id": 199741,
  "account_id": 86165,
  "name": "Databricks dev (UC-enabled)",
  "type": null,
  "adapter_version": "databricks_v0",
  "config": null,  // ⚠️ Always null
  "is_ssh_tunnel_enabled": false,
  "oauth_configuration_id": null,
  "private_link_endpoint_id": null,
  "created_at": "2024-04-01T15:25:55.548513+00:00",
  "updated_at": "2025-10-28T19:41:46.231246+00:00"
}
```

## Analysis

1. **Security by Design**: Connection credentials (passwords, tokens, keys) are intentionally not exported
2. **Config Field is Null**: The `config` field that might contain provider-specific settings is always `null`
3. **Limited Metadata**: Only connection name, type, and references (OAuth, PrivateLink) are available

## Implications for Terraform Export

### What CAN Be Exported
✅ Connection name  
✅ Connection type (via `adapter_version`)  
✅ OAuth configuration reference (if used)  
✅ PrivateLink endpoint reference (if used)  
✅ SSH tunnel enabled flag  

### What CANNOT Be Exported
❌ Provider-specific configuration blocks (`snowflake`, `databricks`, `bigquery`, etc.)  
❌ Host/account/database/warehouse settings  
❌ Credentials (passwords, tokens, keys)  
❌ Any sensitive connection parameters  

## Recommended Approach

### Option 1: Placeholder Strategy (Recommended)
Export connections as **stubs** with LOOKUP placeholders for provider-specific config:

```yaml
connections:
  - key: snowflake_prod
    name: Snowflake Production
    # Provider config must be manually added or looked up via Terraform data source
    snowflake:
      account: LOOKUP:snowflake_account
      database: LOOKUP:snowflake_database
      warehouse: LOOKUP:snowflake_warehouse
    # References we CAN export
    private_link_endpoint_key: my_privatelink  # if applicable
    oauth_configuration_id: LOOKUP:oauth_config_id  # if applicable
```

### Option 2: Reference-Only Strategy
Don't attempt to create connections via Terraform - only reference existing ones:

```yaml
# Use Terraform data sources to reference existing connections
data "dbtcloud_connection" "snowflake_prod" {
  connection_id = 189328  # from import
}

# Then use in environments
environment:
  connection_id: data.dbtcloud_connection.snowflake_prod.id
```

### Option 3: Manual Configuration Required
Export connection metadata only, document that connections must be:
1. Created manually in target account first, OR
2. Created via Terraform with manual configuration, OR
3. Imported into Terraform state from existing connections

## Implementation Decision

**For Phase 2, we will:**
1. Export connection metadata (name, type, references)
2. Add a `provider_config_required: true` flag to indicate manual config is needed
3. Document that connection provider blocks must be manually added
4. Add LOOKUP placeholders for OAuth and PrivateLink references

**Future Enhancement:**
- Allow users to provide a separate YAML file with connection configs (like Kubernetes Secrets)
- Support Terraform data source references instead of resource creation
- Document patterns for using external secret managers (Vault, AWS Secrets Manager, etc.)

## Conclusion

**Connection provider-specific configuration cannot be automated via API export due to security constraints.**  
This is expected and appropriate behavior. Users must manually configure connection details in the target account.

---

## Next Steps

1. ✅ Research complete - Confirmed API limitation
2. Skip connection provider config implementation
3. Focus on fixable resources: service tokens, groups, notifications
4. Document connection limitations in user-facing docs

