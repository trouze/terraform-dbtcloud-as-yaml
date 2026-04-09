# YAML Validation Action

Validate your `dbt-config.yml` against the dbt Cloud Terraform YAML schema **before** running Terraform or supplying any dbt Cloud credentials. This catches typos, missing required fields, and structural errors early in your pull-request workflow.

## Overview

The `validate` action is a composite GitHub Action shipped inside this repository. It uses [`check-jsonschema`](https://check-jsonschema.readthedocs.io/) to validate your YAML file against [`schemas/v1.json`](https://raw.githubusercontent.com/dbt-labs/terraform-dbtcloud-as-yaml/main/schemas/v1.json).

- **No Terraform required** — no `terraform init`, no provider downloads
- **No dbt Cloud credentials required** — purely structural validation
- **Fast** — typically completes in under 30 seconds
- **Clear error messages** — reports every violation with a JSON path so you know exactly what to fix

---

## Quick Start

```yaml title=".github/workflows/validate.yml"
name: Validate dbt Cloud YAML

on:
  push:
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dbt-labs/terraform-dbtcloud-as-yaml/validate@v1
        with:
          file: dbt-config.yml   # optional — this is the default
```

The job exits with code `1` and prints a structured error report when the file does not conform to the schema, causing your CI run to fail immediately — before any Terraform or credential steps run.

---

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `file` | No | `dbt-config.yml` | Path to the dbt Cloud YAML configuration file to validate, relative to the repository root. |

---

## Example: Validate before Terraform Plan

Add the validation step at the top of your existing Terraform CI workflow so bad YAML is caught before Terraform even initialises:

```yaml title=".github/workflows/ci.yml"
name: CI — Validate and Plan

on:
  pull_request:
    branches: [main]
    paths:
      - "dbt-config.yml"
      - "**.tf"

permissions:
  contents: read
  pull-requests: write

jobs:
  validate:
    name: Validate YAML
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dbt-labs/terraform-dbtcloud-as-yaml/validate@v1
        with:
          file: dbt-config.yml

  plan:
    name: Terraform Plan
    runs-on: ubuntu-latest
    needs: validate   # only runs when YAML is valid
    env:
      TF_VAR_dbt_account_id: ${{ secrets.DBT_ACCOUNT_ID }}
      TF_VAR_dbt_token: ${{ secrets.DBT_TOKEN }}
      TF_VAR_dbt_host_url: "https://cloud.getdbt.com"
      TF_VAR_environment_credentials: ${{ secrets.ENVIRONMENT_CREDENTIALS }}
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - run: terraform plan -no-color
```

---

## Example Error Output

When a YAML file fails validation the action prints a structured report and exits with code `1`:

```
Validating 'dbt-config.yml' against dbt Cloud YAML schema v1...
Schema validation errors were encountered.
  dbt-config.yml::$: 'version' is a required property
  dbt-config.yml::$.account: 'host_url' is a required property
  dbt-config.yml::$.projects[0].environments[0].credential: 'token_name' is a required property
Error: Process completed with exit code 1.
```

Each line identifies the exact JSON path where the violation occurred, making it straightforward to find and fix the issue.

---

## Versioning

Pin the action to a release tag or commit SHA to avoid unexpected breaking changes:

```yaml
# Pin to a release tag (recommended)
- uses: dbt-labs/terraform-dbtcloud-as-yaml/validate@v1

# Pin to a specific commit SHA for maximum reproducibility
- uses: dbt-labs/terraform-dbtcloud-as-yaml/validate@2bb4e9e
```

Avoid `@main` in production workflows — it tracks the development branch and may change at any time.

---

## Next Steps

<div class="grid cards" markdown>

-   :material-pipe:{ .lg .middle } **CI/CD Integration**

    ---

    Full CI and CD pipeline examples for GitHub Actions, GitLab, and Azure DevOps

    [:octicons-arrow-right-24: CI/CD Guide](cicd.md)

-   :material-file-code:{ .lg .middle } **YAML Schema Reference**

    ---

    Full field reference for `dbt-config.yml`

    [:octicons-arrow-right-24: YAML Schema](../configuration/yaml-schema.md)

-   :material-security:{ .lg .middle } **Best Practices**

    ---

    Secure and reliable deployments

    [:octicons-arrow-right-24: Best Practices](best-practices.md)

</div>
