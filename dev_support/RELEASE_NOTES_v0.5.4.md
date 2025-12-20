# Release Notes: v0.5.4

**Release Date:** 2025-12-20  
**Version:** 0.5.4 (Patch Release)  
**Type:** Bug Fix

---

## Summary

This patch release fixes a Terraform validation error that prevented successful plan execution. The issue was related to using sensitive values in `for_each` filters, which Terraform disallows for security reasons.

---

## 🐛 Bug Fixes

### Terraform "Invalid for_each argument" Error

**Problem:** Terraform plan was failing with the following error:
```
Error: Invalid for_each argument
  on ../../modules/projects_v2/environments.tf line 60, in resource "dbtcloud_databricks_credential" "credentials":
  60:   for_each = {
  61:     for item in local.all_environments :
  62:     "${item.project_key}_${item.env_key}" => item
  63:     if try(item.env_data.credential, null) != null &&
  64:        try(item.env_data.credential.token_name, null) != null &&
  65:        contains(local.available_token_names, item.env_data.credential.token_name) &&
  66:        try(item.env_data.credential.schema, null) != null
  67:   }
     ├────────────────
     │ local.all_environments is tuple with 29 elements
     │ local.available_token_names has a sensitive value

Sensitive values, or values derived from sensitive values, cannot be used
as for_each arguments. If used, the sensitive value could be exposed as a
resource instance key.
```

**Root Cause:** Even though we were using `keys(var.token_map)` to extract only the token names (which are not sensitive), Terraform still considered the result sensitive because it was derived from a sensitive map (`var.token_map`). Terraform disallows sensitive values in `for_each` conditions to prevent them from being exposed as resource instance keys.

**Solution:** 
- Wrapped `keys(var.token_map)` with Terraform's `nonsensitive()` function
- This explicitly marks the keys as non-sensitive, allowing their use in `for_each` filters
- The `nonsensitive()` function (available in Terraform 0.14+) is designed for exactly this use case

**Impact:** Terraform plan now completes successfully. The plan shows 97 resources to add with no errors.

**Files Changed:**
- `modules/projects_v2/environments.tf`: Updated line 24 to use `nonsensitive(keys(var.token_map))`

---

## 🔧 Technical Details

### Terraform Sensitive Value Handling

Terraform has strict rules about sensitive values to prevent accidental exposure:
- Sensitive values cannot be used in `for_each` keys or conditions
- Values derived from sensitive values are also considered sensitive
- The `nonsensitive()` function allows you to explicitly mark a value as non-sensitive when you know it's safe

### Why This Works

In our case:
- `var.token_map` is marked as `sensitive = true` (the token values are secrets)
- The **keys** of the map (token names like "databricks_prod_token") are not secrets
- `keys(var.token_map)` extracts only the keys, but Terraform still considers it sensitive
- `nonsensitive(keys(var.token_map))` explicitly tells Terraform the keys are safe to use

### Code Change

**Before:**
```hcl
locals {
  available_token_names = toset(keys(var.token_map))
}
```

**After:**
```hcl
locals {
  available_token_names = toset(nonsensitive(keys(var.token_map)))
}
```

---

## 📚 Documentation Updates

- Updated `CHANGELOG.md` with detailed fix description
- Updated `dev_support/importer_implementation_status.md` with version and change log entry
- Updated `dev_support/phase5_e2e_testing_guide.md` with new version number

---

## 🚀 Upgrade Instructions

### For Users

No action required. This fix only affects internal Terraform module logic.

### For Developers

If you encounter similar "Invalid for_each argument" errors with sensitive values:

1. **Identify the sensitive source**: Find where the sensitive value originates
2. **Determine if the derived value is actually sensitive**: In our case, map keys are not sensitive, only values
3. **Use `nonsensitive()`**: Wrap the derived value with `nonsensitive()` if it's safe to expose
4. **Verify**: Ensure the non-sensitive value doesn't expose secrets

**Example:**
```hcl
# ❌ This fails - keys() of sensitive map is still sensitive
locals {
  token_names = keys(var.sensitive_token_map)
}

resource "example" "test" {
  for_each = local.token_names  # Error: sensitive value in for_each
}

# ✅ This works - explicitly mark keys as non-sensitive
locals {
  token_names = nonsensitive(keys(var.sensitive_token_map))
}

resource "example" "test" {
  for_each = local.token_names  # OK: keys are not sensitive
}
```

---

## ✅ Testing

- ✅ Terraform plan completes successfully (97 resources planned)
- ✅ No "Invalid for_each argument" errors
- ✅ Credential filtering works correctly based on token availability
- ✅ Sensitive token values remain protected

---

## 📝 Next Steps

- Continue E2E testing with corrected Terraform module
- Address deprecation warnings for `adapter_type` attribute (informational only)
- Monitor for any edge cases with credential filtering

---

**Related Issues:** N/A  
**Breaking Changes:** None  
**Migration Required:** No

