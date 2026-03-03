# Release Notes - v0.24.0

**Date:** 2026-03-02  
**Type:** Minor Release  
**Previous Version:** 0.23.4

## Summary

This release adds a dedicated Removal Management utility workflow for explicit Terraform state detachment operations and hardens related intent/mapping behavior. It also includes normalization and operational quality fixes to reduce set-collision risk and improve local web-server lifecycle handling.

## Key Updates

### Removal Management Utility
- Added a dedicated `/removal-management` utility step in the workflow and navigation.
- Added command preview and explicit confirmation flow for selected `terraform state rm` operations.
- Added object-type filtering with persistent multi-select behavior.
- Added per-type counts in object filter options for safer bulk selection.

### Match/Intent and Normalization Hardening
- Match grid now reapplies persisted `removal_keys` when entries are stored either with or without the `target__` prefix.
- Group permission normalization now deduplicates equivalent permission entries to avoid Terraform set collisions.

### Developer Experience
- `restart_web.sh` now supports `--daemon`, graceful shutdown, readiness checks, and log output to `.cursor/web-server.log`.

## Files Updated

- `importer/web/pages/removal_management.py`
- `importer/web/tests/test_removal_management.py`
- `importer/web/app.py`
- `importer/web/state.py`
- `importer/web/components/match_grid.py`
- `importer/normalizer/core.py`
- `test/test_normalizer.py`
- `restart_web.sh`
- `importer/VERSION`
- `CHANGELOG.md`
- `dev_support/importer_implementation_status.md`
- `dev_support/phase5_e2e_testing_guide.md`

## Verification

1. Open `/removal-management`, select one or more object types, and confirm rows filter and selection persists.
2. Confirm object-type dropdown labels include counts (for example `ENV (N)`).
3. Select filtered rows, preview commands, and validate generated `terraform state rm` commands map to selected state addresses.
4. Run normalizer tests and verify duplicate group permission inputs normalize to a deduplicated output set.
5. Run `./restart_web.sh --daemon` and confirm server startup and log path output.
