# Examples

## Quick Start

1. **Copy the example**
   ```bash
   cp -r examples/basic my-dbt-project
   cd my-dbt-project
   ```

2. **Set up credentials**
   ```bash
   cp .env.example .env
   # Edit .env with your dbt Cloud credentials
   ```

3. **Deploy**
   ```bash
   source .env
   terraform init
   terraform plan
   terraform apply
   ```

## Managing Multiple Projects

Store multiple YAML configs and switch between them:

```bash
# Directory structure
configs/
  ├── finance.yml
  ├── marketing.yml
  └── operations.yml

# Deploy specific project
source .env
terraform plan -var="yaml_file_path=./configs/finance.yml"
terraform apply -var="yaml_file_path=./configs/finance.yml"

# Or in GitHub Actions (parallel execution)
terraform plan -var="yaml_file_path=./configs/${{ matrix.project }}.yml"
```

## Available Examples

- **basic/** - Minimal working example with environment variable setup

## YAML Configuration Spec

The YAML file defines all dbt Cloud resources. Below is the complete specification:

```yaml
project:
  name: <string> # Required. Name of the dbt project.
  repository:
    remote_url: <string> # Required. URL of the remote Git repository.
    gitlab_project_id: <number> # Optional. GitLab project ID if using GitLab integration.
  environments:
    - name: <string> # Required. Name of the environment.
      credential:
        token_name: <string> # Optional. Name of the token to use.
        schema: <string> # Optional. Schema to be used.
        catalog: <string> # Optional. Catalog to be used.
      connection_id: <number> # Required. Connection ID for the environment.
      type: <string> # Required. Type of environment. Allowed values: 'development', 'deployment'.
      dbt_version: <string> # Optional. dbt version to use. Defaults to "latest".
      enable_model_query_history: <boolean> # Optional. Enable model query history. Defaults to false.
      custom_branch: <string> # Optional. Custom branch for dbt. Defaults to null.
      deployment_type: <string> # Optional. Deployment type (e.g., 'production'). Defaults to null.
      jobs:
        - name: <string> # Required. Name of the job.
          execute_steps: 
            - <string> # Required. Steps to execute in the job.
          triggers:
            github_webhook: <boolean> # Required. Trigger job on GitHub webhook.
            git_provider_webhook: <boolean> # Required. Trigger job on Git provider webhook.
            schedule: <boolean> # Required. Trigger job on a schedule.
            on_merge: <boolean> # Required. Trigger job on merge.
          dbt_version: <string> # Optional. dbt version for the job. Defaults to "latest".
          deferring_environment: <string> # Optional. Enable deferral of job to environment. Defaults to no deferral.
          description: <string> # Optional. Description of the job. Defaults to null.
          errors_on_lint_failure: <boolean> # Optional. Fail job on lint errors. Defaults to true.
          generate_docs: <boolean> # Optional. Generate docs. Defaults to false.
          is_active: <boolean> # Optional. Whether the job is active. Defaults to true.
          num_threads: <number> # Optional. Number of threads for the job. Defaults to 4.
          run_compare_changes: <boolean> # Optional. Compare changes before running. Defaults to false.
          run_generate_sources: <boolean> # Optional. Generate sources before running. Defaults to false.
          run_lint: <boolean> # Optional. Run lint before running. Defaults to false.
          schedule_cron: <string> # Optional. Cron schedule for the job. Defaults to null.
          schedule_days: <array> of <ints> # Optional. Days for schedule. Defaults to null. e.g. [0, 1, 2]
          schedule_hours: <array> of <ints> # Optional. Hours for schedule. Defaults to null. e.g. [0, 1, 2]
          schedule_interval: <string> # Optional. Interval for schedule. Defaults to null.
          schedule_type: <string> # Optional. Type of schedule. Defaults to null.
          self_deferring: <boolean> # Optional. Whether the job is self-deferring. Defaults to false.
          target_name: <string> # Optional. Target name for the job. Defaults to null.
          timeout_seconds: <number> # Optional. Job timeout in seconds. Defaults to 0.
          triggers_on_draft_pr: <boolean> # Optional. Trigger job on draft PRs. Defaults to false.
          env_var_overrides:
            <ENV_VAR>: <string> # Optional. Specify a job env var override
  environment_variables:
    - name: DBT_<string> # Required. Name of the environment variable. Starts with DBT_
      environment_values:
        - env: project
          value: <string> # Optional. Environment value
        - env: Production
          value: <string> # Optional. Environment value
        - env: UAT
          value: <string> # Optional. Environment value
        - env: Development
          value: <string> # Optional. Environment value
    - name: DBT_SECRET_<string> # Required. Name of the secret environment variable. Starts with DBT_SECRET_
      environment_values:
        - env: project
          value: secret_<string> # Optional. Environment value
        - env: Production
          value: secret_<string> # Optional. Environment value
        - env: UAT
          value: secret_<string> # Optional. Environment value
        - env: Development
          value: secret_<string> # Optional. Environment value
```