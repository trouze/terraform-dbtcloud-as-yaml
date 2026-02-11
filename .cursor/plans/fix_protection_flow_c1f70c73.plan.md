---
name: Fix Protection Flow
overview: Fix the deploy generate YAML overwrite bug, the protection management page 500 error (_state_data attribute + background task UI context), and add merge_yaml_configs with tests.
todos:
  - id: merge-fn
    content: Create merge_yaml_configs() function in adoption_yaml_updater.py that merges source YAML into existing base YAML by key
    status: completed
  - id: deploy-fix
    content: Update deploy.py to use merge instead of overwrite when existing deployment YAML exists
    status: completed
  - id: fix-500
    content: "Fix utilities.py: _state_data AttributeError (use hasattr or reconcile_state_resources) and background task UI context error in generate_all_pending"
    status: completed
  - id: unit-tests-merge
    content: "Add unit tests for merge_yaml_configs: preserves existing projects, adds new ones, updates matched, preserves globals, handles empty/None inputs"
    status: completed
  - id: integration-tests-deploy
    content: "Add integration tests: deploy generate uses merge when existing YAML present, deploy generate on fresh migration copies source, deploy generate with protection intent applies after merge"
    status: completed
  - id: unit-tests-utilities
    content: "Add unit tests for utilities.py fixes: _state_data access doesn't crash when unset, generate_all_pending handles missing YAML gracefully, sync_from_tf_state with no state data returns early"
    status: completed
  - id: run-pytests
    content: Run pytest suite to verify merge_yaml_configs and existing tests pass
    status: completed
  - id: restart-and-browse
    content: Run restart_web.sh, then use browsermcp to verify Protection Management page loads without 500, Deploy Generate preserves all projects, and navigation links work
    status: completed
  - id: debug-iterate
    content: If browsermcp reveals issues, fix them and re-test until all three pages (Deploy, Protection Management, Destroy) work correctly
    status: completed
isProject: false
---

# Fix Protection Flow: Deploy Generate, Protection Management Page, and Tests

## Problem Summary

Three interconnected issues are breaking the protection workflow:

1. **Deploy generate overwrites existing YAML** - `deploy.py` starts from `state.map.last_yaml_file` (source-selected subset, e.g. 1 project) and copies it to `deployments/migration/dbt-cloud-config.yml`, obliterating the existing YAML with all 11 managed projects. Terraform then plans to destroy the 10 missing projects.
2. **Protection Management page 500 error** - Two bugs in [importer/web/pages/utilities.py](importer/web/pages/utilities.py):
  - `state.deploy._state_data` is accessed at line 454 but `_state_data` is not a field on `DeployState` - causes `AttributeError`
  - `generate_all_pending()` calls `ui.notify()` from a background task without a UI slot context (line 541) - causes `RuntimeError`
3. **No merge logic exists** - When deploy generate runs, there's no way to merge newly selected source projects into existing deployment YAML while preserving already-managed resources.

## Fix 1: Add `merge_yaml_configs()` to `adoption_yaml_updater.py`

Add a new function at the end of [importer/web/utils/adoption_yaml_updater.py](importer/web/utils/adoption_yaml_updater.py):

```python
def merge_yaml_configs(base_yaml: dict, source_yaml: dict) -> dict:
    """Merge source-selected resources into existing base YAML.
    
    - Projects in source that aren't in base: ADD
    - Projects in source that ARE in base: UPDATE
    - Projects in base that aren't in source: PRESERVE (critical!)
    - Same for globals sections (repositories, connections, etc.)
    """
```

- Merge by `key` field for projects
- Merge by `key` field for globals.repositories, globals.connections, etc.
- Preserve top-level fields (`version`, `account`, etc.) from base
- Return the merged dict

## Fix 2: Update `deploy.py` to merge instead of overwrite

In [importer/web/pages/deploy.py](importer/web/pages/deploy.py) around line 1444:

- Before copying source YAML, check if `output_path / "dbt-cloud-config.yml"` already exists
- If it exists: load both YAMLs, call `merge_yaml_configs(existing, source)`, write merged result
- If it doesn't exist: copy source YAML as-is (current behavior for fresh migrations)
- Same logic needed at line 1606 (protection section fallback copy)

## Fix 3: Fix `_state_data` AttributeError in `utilities.py`

In [importer/web/pages/utilities.py](importer/web/pages/utilities.py):

- Line 299: `state.deploy._state_data = ...` - dynamically setting an attribute not on the dataclass
- Line 454: `state.deploy._state_data` - accessing it later fails if not set

**Fix**: Use `getattr(state.deploy, '_state_data', None)` at line 454, or better yet, use `hasattr()` check. Even better: avoid the dynamic attribute entirely by using `reconcile_state_resources` which already exists on `DeployState`.

## Fix 4: Fix background task UI context in `utilities.py`

In [importer/web/pages/utilities.py](importer/web/pages/utilities.py) `generate_all_pending()` (line 512):

- The function is `async` and called via `asyncio.create_task()` but calls `ui.notify()` which needs a NiceGUI slot context
- **Fix**: Remove `asyncio.create_task()` wrapper at line 592 and call directly, OR wrap `ui.notify()` calls in try/except, OR use NiceGUI's `app.call_later()` pattern

## Fix 5: Comprehensive Unit and Integration Tests

### 5a. Unit tests for `merge_yaml_configs` (in `test_adoption_yaml_updater.py`)

New class `TestMergeYamlConfigs`:

- `test_preserves_existing_projects` - base has 3 projects, source has 1 new, result has 4
- `test_adds_new_projects_from_source` - new project key not in base gets added
- `test_updates_matched_projects` - source project with same key updates base values
- `test_preserves_globals_repositories` - globals.repositories from base preserved
- `test_merges_globals_repositories` - new source repo added, existing preserved
- `test_preserves_globals_connections` - globals.connections from base preserved
- `test_fresh_migration_uses_source_as_is` - empty/None base returns source unchanged
- `test_empty_source_returns_base` - empty/None source returns base unchanged
- `test_preserves_top_level_fields` - version, account, etc. from base preserved
- `test_both_empty_returns_empty` - both empty inputs returns empty dict
- `test_merge_with_protection_flags` - protected: true/false flags preserved correctly

### 5b. Integration tests for deploy generate merge (new file `test_deploy_generate_merge.py`)

Simulates the deploy generate flow without UI:

- `test_deploy_merge_preserves_existing_projects` - existing YAML with 11 projects + source with 1 = 12 projects in output
- `test_deploy_fresh_migration_copies_source` - no existing YAML, source copied as-is
- `test_deploy_merge_then_protection_applied` - merge runs first, then protection intents applied to merged YAML
- `test_deploy_merge_idempotent` - running merge twice produces same result
- `test_deploy_merge_with_adoption_overrides` - merge + adoption overrides work together correctly

### 5c. Unit tests for utilities.py fixes (in `test_protection_edge_cases.py` or new file)

- `test_state_data_access_without_load` - accessing sync_from_tf_state when no state loaded returns gracefully, no AttributeError
- `test_generate_all_pending_with_missing_yaml` - generate_all_pending returns early when YAML file doesn't exist
- `test_generate_all_pending_with_no_pending_intents` - returns early when no pending items

## Live Validation: restart_web.sh + browsermcp

After all code changes and pytest:

1. **Run `./restart_web.sh**` to restart the NiceGUI web server with the fixes
2. **browsermcp: Protection Management page** - Navigate to `http://127.0.0.1:8080/protection-management`, verify it loads without 500 error, check intent table renders, test "Sync from TF State" and "Generate All Pending" buttons
3. **browsermcp: Deploy page** - Navigate to Deploy, click "Generate Files", verify the terminal output shows merge logic (not overwrite), confirm generated YAML contains all managed projects (not just source-selected subset)
4. **browsermcp: Destroy page** - Navigate to Destroy, verify it loads and respects protection intent
5. **browsermcp: Sidebar navigation** - Confirm "Protection Management" link in sidebar navigates to `/protection-management`
6. **If any page fails** - Check terminal output for errors, fix, re-run `./restart_web.sh`, re-test with browsermcp until fully working

## Key Files

- [importer/web/utils/adoption_yaml_updater.py](importer/web/utils/adoption_yaml_updater.py) - Add `merge_yaml_configs()`
- [importer/web/pages/deploy.py](importer/web/pages/deploy.py) - Replace `shutil.copy2` with merge logic (~line 1444)
- [importer/web/pages/utilities.py](importer/web/pages/utilities.py) - Fix `_state_data` and background task UI context
- [importer/web/tests/test_adoption_yaml_updater.py](importer/web/tests/test_adoption_yaml_updater.py) - Add merge tests

