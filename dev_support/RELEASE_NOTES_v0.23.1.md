# Release Notes - v0.23.1

**Date:** 2026-02-18  
**Type:** Patch Release  
**Previous Version:** 0.23.0

## Summary

Fixes a runtime compatibility issue in the Adopt output viewer that could trigger a UI reconnect loop when opening `View Output` on NiceGUI versions that do not accept the `sanitize` argument on `ui.html`.

## Key Fixes

### Adopt Output Dialog Compatibility
- **Problem**: Opening `View Output` on `/adopt` could raise `TypeError: __init__() got an unexpected keyword argument 'sanitize'`, which interrupted dialog rendering and destabilized the UI session.
- **Fix**: Updated `create_plan_viewer_dialog` to call `ui.html` with `sanitize=False` when supported and automatically fall back to a no-`sanitize` call on incompatible versions.
- **Result**: Adoption logs and plan output dialogs now open reliably across local environments without server-side exceptions.

## Files Changed

| File | Change |
|------|--------|
| `importer/web/utils/yaml_viewer.py` | Added NiceGUI-version-compatible `ui.html` rendering fallback |
| `importer/VERSION` | 0.23.0 -> 0.23.1 |
| `CHANGELOG.md` | Added 0.23.1 section |
| `dev_support/importer_implementation_status.md` | Updated version metadata and change log |
| `dev_support/phase5_e2e_testing_guide.md` | Updated importer version and date |

## Testing Verification

1. Restart web UI via `./restart_web.sh`.
2. Navigate to `/adopt`.
3. Run `Plan Adoption`.
4. Click `View Output` repeatedly during/after plan execution.
5. Confirm the output dialog opens and no `sanitize` TypeError appears in server logs.
