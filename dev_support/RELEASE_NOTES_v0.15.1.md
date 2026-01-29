# Release Notes v0.15.1

**Release Date:** 2026-01-29  
**Release Type:** Patch (Bug Fixes)

---

## Summary

This patch release fixes critical bugs in the resource matching logic, particularly for repositories that were adopted with different names. It also adds a new Match Debug tab to help diagnose matching issues.

---

## Bug Fixes

### State-Aware Repository Matching

**Problem:** After adopting a repository into Terraform state, the Match Existing grid would show "Create New" instead of "Match" if the source repository name differed from the target repository name.

**Root Cause:** Project-linked repositories have their own matching code path (added as child rows under projects) that was missing state-aware matching logic. The main loop had state-aware matching, but repositories under projects were only matched by:
1. `remote_url`
2. `github_repo`
3. Exact name match

**Fix:** Added state-aware matching for project-linked repositories. If no match is found by URL/name but the repository exists in Terraform state, the state's `dbt_id` is used to look up the target resource.

### Composite ID Parsing

**Problem:** Terraform state for some resources (like repositories) uses composite IDs in the format `"project_id:resource_id"` (e.g., `"605:556"`). The matching logic wasn't extracting the numeric resource ID correctly.

**Fix:** Enhanced `terraform_state_reader.py` to:
- Detect composite IDs containing `:`
- Extract the numeric resource ID from the last part
- Normalize all `dbt_id` values to integers for consistent lookups

### Type Normalization

**Problem:** Type mismatches between string and integer IDs caused lookup failures even when the values matched (e.g., `"556"` vs `556`).

**Fix:** Added explicit type normalization to integers throughout the matching pipeline:
- When building `state_by_id` lookup dictionaries
- When building `state_repo_by_project` lookup dictionaries
- Before performing `target_by_id.get()` lookups

---

## New Features

### Match Debug Tab

Added a new "Match Debug" tab to the resource detail popup dialog. This tab provides comprehensive debugging information:

1. **Matching Strategy**: Shows current action, confidence level, and match type
2. **Key Comparison**: Displays source key, name, type, and ID alongside target values
3. **Lookup Diagnostics**: Shows drift status, state ID, state address, and resource index
4. **Terraform Import Address Preview**: Shows the expected import address format
5. **LLM Diagnostic Report**: Structured text format optimized for AI analysis with a "Copy for AI" button
6. **Raw Grid Row Data**: JSON dump of all row properties for detailed inspection

---

## Files Changed

| File | Changes |
|------|---------|
| `importer/web/components/match_grid.py` | Added state-aware matching for project-linked repositories, type normalization |
| `importer/web/components/entity_table.py` | Added Match Debug tab with diagnostics and LLM report |
| `importer/web/utils/terraform_state_reader.py` | Fixed composite ID parsing, dbt_id normalization |
| `importer/web/pages/match.py` | Removed debug print statements |

---

## Upgrade Notes

No breaking changes. This is a drop-in replacement for v0.15.0.

---

## Testing Performed

1. Verified adopted repository with different name shows "Match" action
2. Verified drift status shows "In Sync" for matched adopted resources
3. Verified Match Debug tab displays correct diagnostic information
4. Verified composite ID parsing works for repository IDs
5. Verified no regressions in other resource type matching

---

## Known Issues

None.
