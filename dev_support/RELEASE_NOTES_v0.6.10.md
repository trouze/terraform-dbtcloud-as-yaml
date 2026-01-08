# Release Notes v0.6.10

Date: 2026-01-08

## Summary

Patch release focused on **Terraform job creation stability** during E2E runs.

## Fixed

- **Jobs: compare_changes_flags unknown after apply**
  - Fixed an issue where creating `dbtcloud_job` resources could fail with:
    - `Provider returned invalid result object after apply`
    - due to `compare_changes_flags` remaining unknown after the create step.
  - Provider now ensures `compare_changes_flags` is **always known** post-create (set from API when present, otherwise `null`).

## Notes

- This release does not infer environment `deployment_type` from environment names. Any `deployment_type` behavior should come from source snapshot/mapping.


