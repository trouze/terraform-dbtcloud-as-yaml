# Phase 1 – Source Account Analysis

This document covers credentials setup, the dbt Cloud API surface we need to inventory an account, prototype commands for pagination/auth, and the draft internal data model the importer will populate before emitting YAML.

---

## 1. Credentials & Local Setup

1. **Populate `.env` (already provided)** with at least:
   ```
   DBT_HOST=https://cloud.getdbt.com
   DBT_ACCOUNT_ID=12345
   DBT_API_TOKEN=XXXXXXXX
   ```
   - `DBT_API_TOKEN` must belong to an **Account Admin** (or higher) because we will read repositories, environments, connections, groups, service tokens, and semantic layer state.
2. **Load the env vars** before experimenting:
   ```bash
   set -a
   source .env
   set +a
   ```
3. **Define helper headers** so curl/httpie commands stay concise:
   ```bash
   export DBT_V2="$DBT_HOST/api/v2/accounts/$DBT_ACCOUNT_ID"
   export DBT_V3="$DBT_HOST/api/v3/accounts/$DBT_ACCOUNT_ID"
   export DBT_TOKEN_HEADER="Authorization: Token $DBT_API_TOKEN"
   export DBT_BEARER_HEADER="Authorization: Bearer $DBT_API_TOKEN"
   ```
   - dbt Cloud currently accepts the same PAT for both v2 (`Token`) and v3 (`Bearer`) endpoints.
4. **Health check**:
   ```bash
   curl -sS "$DBT_V2/projects/?limit=1" -H "$DBT_TOKEN_HEADER" | jq '.data[0].name'
   ```

> The importer CLI will read `.env` automatically (via `python-dotenv`) so the same convention applies to local runs and CI.

---

## 2. Endpoint Inventory

| Asset | API Version | Endpoint(s) | Notes / Required Fields |
|-------|-------------|-------------|-------------------------|
| Projects | v2 | `GET /api/v2/accounts/{account_id}/projects/` | Collect `id`, `name`, `repository_id`, `state`. Query params: `limit`, `offset`. |
| Repositories | v2 | `GET /api/v2/accounts/{account_id}/repositories/` | Needed for remote URL, clone strategy, OAuth install IDs. |
| Environments | v2 | `GET /api/v2/accounts/{account_id}/environments/` | Includes `connection_id`, `credential` info, job IDs. Use `include=credentials` to avoid follow-up calls. |
| Jobs | v2 | `GET /api/v2/accounts/{account_id}/jobs/` | Returns triggers, execute steps, schedule info. Use `include=environment` to map names, `order_by=id`. |
| Job Artifacts (optional) | v2 | `GET /api/v2/accounts/{account_id}/jobs/{job_id}/artifacts/{remainder}` | Only required if we want job definitions like `manifest.json`. Probably out-of-scope. |
| Project-level Env Vars | v3 | `GET /api/v3/accounts/{account_id}/projects/{project_id}/environment-variables/` | Use `environment-variables/environment/`, `job/`, `user/` endpoints to capture each scope; response includes `environment_id` or `job_id`. |
| Connections | v3 | `GET /api/v3/accounts/{account_id}/connections/` | Captures connection metadata (type, catalog support, PrivateLink binding). Required for placeholders + lookups. |
| Credentials (warehouse tokens) | v2 | `GET /api/v2/accounts/{account_id}/credentials/` (implicit via environments) | Not every credential is tied to an environment; call explicitly to catch detached ones. |
| Service Tokens | v3 | `GET /api/v3/accounts/{account_id}/service-tokens/` | Returns `name`, `scopes`, `last_used_at`. Secrets are not retrievable; importer stores metadata + placeholder. |
| Groups | v3 | `GET /api/v3/accounts/{account_id}/groups/` | Contains group members + permission sets. Needed for RBAC documentation. |
| Notifications | v2 (job-scoped) | Embedded in job payload under `settings.notification_settings` | Extract Slack/email/webhook details per job; no standalone endpoint yet. |
| PrivateLink Endpoints | v3 | `GET /api/v3/accounts/{account_id}/private-link-endpoints/` | Provides region + cloud; referenced by repositories/connections. |
| Semantic Layer Configs | v3 | `GET /api/v3/accounts/{account_id}/semantic-layer-credentials/` + `semantic-layer-config` fields on projects | Ensures importer can recreate semantic layer toggles. |
| Service Connections / OAuth | v3 | `GET /api/v3/accounts/{account_id}/oauth-configurations/` (if repos rely on OAuth) | Needed when importer must warn about manual remapping. |
| Tokens / PAT metadata | v3 | `GET /api/v3/accounts/{account_id}/personal-access-tokens/` (optional) | Useful for inventory but excluded from YAML output for security. |

### Pagination Strategy
- v2 endpoints accept `limit` (default 100) and `offset`. Keep `limit=1000` for faster syncs and loop until fewer than limit results are returned.
- v3 endpoints accept `limit`, `offset`, and some support cursor-style `starting_after`. Prefer offset for consistency unless the endpoint demands cursoring.

### Filtering & Includes
- Projects/Jobs: add `?include=environment,custom_environment_variables` to reduce follow-up calls.
- Repositories: add `?git_remote_url__icontains=` when supporting partial imports (Phase 4).
- Groups: `?name__icontains` supports targeted lookups when re-running.

### Auth Scopes (minimum)
- Projects/Environments/Jobs: `Account Admin` or custom service token with `read:projects`, `read:jobs`.
- Connections/Service Tokens/Groups: requires `Owner` or PAT with `account:admin`.
- Semantic Layer endpoints: require `semantic_layer_only` scope.

---

## 3. Prototype Commands

```bash
# List first page of projects (v2)
http GET "$DBT_V2/projects/?limit=100" "Authorization:$DBT_API_TOKEN"

# Stream all environments with pagination
page=0
while :; do
  resp=$(curl -sS "$DBT_V2/environments/?limit=100&offset=$((page*100))" -H "$DBT_TOKEN_HEADER")
  echo "$resp" | jq '.data[].name'
  [[ $(echo "$resp" | jq '.data | length') -lt 100 ]] && break
  page=$((page+1))
done

# Fetch project-scoped env vars (v3)
http GET "$DBT_V3/projects/$PROJECT_ID/environment-variables/environment/?limit=100" "$DBT_BEARER_HEADER"

# Connections with PrivateLink metadata
http GET "$DBT_V3/connections/?limit=100" "$DBT_BEARER_HEADER" | jq '.data[].details.privatelink'

# Service tokens inventory
http GET "$DBT_V3/service-tokens/?limit=100" "$DBT_BEARER_HEADER" | jq '.data[] | {name, scopes}'
```

Key behaviors to test:
- PAT expiration/rotation: ensure 401s are surfaced with actionable messaging.
- Mixed API versions: fail fast when an endpoint returns 404 so we can fall back or skip gracefully.
- Rate limits: note `X-RateLimit-Remaining` headers; add exponential backoff after `429`.

---

## 4. Internal Data Model Draft

The importer will populate an intermediate model before emitting YAML. Proposed structure (Python-ish types):

```python
class AccountSnapshot(BaseModel):
    account: AccountMeta
    globals: Globals
    projects: list[Project]

class Globals(BaseModel):
    connections: dict[str, Connection]
    repositories: dict[str, Repository]
    groups: dict[str, Group]
    service_tokens: dict[str, ServiceToken]
    privatelink_endpoints: dict[str, PrivateLinkEndpoint]
    notifications: dict[str, NotificationTarget]
    semantic_layer_configs: dict[str, SemanticLayerConfig]

class Project(BaseModel):
    key: str
    project_id: int
    name: str
    repository_key: str
    environments: list[Environment]
    environment_variables: list[EnvironmentVariable]
    jobs: list[Job]
    notifications: dict[str, NotificationTarget]
```

Modeling rules:
- **Keys over IDs**: every object gets a deterministic key (slugified name or API slug). Numeric IDs remain for traceability but never required in YAML.
- **Lookup metadata**: store `lookup_hint` for anything that must be remapped in the target account (connections without Terraform control, OAuth configs, etc.).
- **Normalization hooks**: attach `source_metadata` to each object so we can reference the original API payload when debugging while keeping the emitter clean.

---

## 5. Deliverables for Phase 1

1. Scripts/snippets (above) that confirm we can read every endpoint with the PAT in `.env`.
2. Checklist of required scopes per endpoint (documented above; update if API responses complain).
3. JSON sample dumps stored under `dev_support/samples/` (ignore secrets) for use in Phase 2 normalization tests.
4. Issues filed for any missing API (e.g., if notifications require manual scraping).

