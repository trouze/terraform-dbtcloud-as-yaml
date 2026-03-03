# Secret Remediation Runbook

Date: 2026-03-02  
Repository: `trouze/terraform-dbtcloud-yaml`  
Branch rewritten: `importer`

## What was done automatically

1. Removed committed dummy private key material from active code paths.
2. Committed the fix:
   - Commit: `3e609e5`
   - Message: `fix(secrets): remove committed dummy private key material`
3. Rewrote git history in a mirror clone to remove known leaked artifact files.
4. Force-pushed rewritten branch:
   - `importer` updated from `ac49277` to `83a1ace`.
5. Created safety backup branch locally before rewrite:
   - `backup/pre-history-rewrite-20260302-140404`

## Paths removed from git history

The following high-risk files/directories were removed from history:

- `test/e2e_test/terraform_debug.log`
- `test/e2e_test/.env.bak`
- `dev_support/samples.backup.20251219_205304`
- `dev_support/samples/account_86165_run_035__json__20251121_000735.json`
- `dev_support/samples/account_86165_run_035__report__20251121_000735.md`
- `dev_support/samples/account_86165_run_036__json__20251121_000942.json`
- `dev_support/samples/account_86165_run_036__report__20251121_000942.md`
- `dev_support/bt/samples/account_11_run_001__report__20260218_015120.md`

## Problem inventory and manual follow-up

### 1) Generic Private Key (dummy PEM)

- **Where detected:** historical commits `ac49277`, `5c84b99`
- **Status:** fixed in code + rewritten history
- **Manual action:** close/resolve associated GitGuardian incidents after re-index/refresh

### 2) dbt Cloud tokens in debug artifacts / env backups

- **Where detected:** historical commits like `e7d819d`, `ba5a49f`
- **Status:** high-risk files removed from history
- **Manual action required:**
  - Rotate/revoke any potentially real dbt Cloud API tokens and service tokens that appeared in logs/backups.
  - Verify token scopes after rotation.
  - Update local secret stores/CI variables with new token values.

### 3) Zapier webhook URLs in sample exports

- **Where detected:** historical commits like `bf5776d`, `df727a9`
- **Status:** known sample files removed from history
- **Manual action required:**
  - Rotate/regenerate affected Zapier webhook endpoints.
  - Confirm downstream integrations still receive expected events.

### 4) Splunk HEC token in sample report

- **Where detected:** historical commit `351c807`
- **Status:** affected file removed from history
- **Manual action required:**
  - Rotate the exposed Splunk token.
  - Update any producer config that used that token.

### 5) Generic Terraform variable and generic password findings in test fixtures

- **Where detected:** historical commits like `1e1c5ea`, `e2b9cde`, `231c1f5`
- **Status:** mostly detector false positives/test placeholders
- **Manual action required:**
  - In GitGuardian, mark specific incidents as false positive / acceptable test fixture where appropriate.
  - Keep placeholder values non-secret-looking in future fixtures.

## Manual checklist (owner actions)

1. **Token/secret rotation**
   - Rotate dbt Cloud tokens (API + service token values that may have been real)
   - Rotate Zapier webhook endpoint(s)
   - Rotate Splunk HEC token
2. **GitGuardian triage**
   - Re-run scan or wait for GitGuardian refresh against rewritten branch history
   - Close resolved incidents
   - Mark false positives for safe fixture-only patterns
3. **Team coordination after rewrite**
   - Notify collaborators that `importer` history was rewritten
   - Ask teammates to rebase/reset local `importer` branches
4. **Local repo hygiene**
   - Fetch latest `origin/importer`
   - Rebase or reset local `importer` branch as needed

## Recommended collaborator recovery commands

For collaborators who have local `importer` clones:

```bash
git fetch origin
git checkout importer
git reset --hard origin/importer
```

If they have local work, they should stash/branch before reset.

