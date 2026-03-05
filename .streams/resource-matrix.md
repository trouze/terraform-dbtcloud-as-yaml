# Resource Classification Matrix

Canonical per-resource classification for the Profile + Missing Resource Rollout.
See plan: `.cursor/plans/profile-resource-rollout_6c610098.plan.md`

## New resources (rollout scope)

| Resource | Code | Scope | Parent | Depth | Stream | Status |
|----------|------|-------|--------|-------|--------|--------|
| `dbtcloud_profile` | PRF | project | PRJ | 2 | S2 | implement-now |
| `dbtcloud_job_completion_trigger` | JCTG | env/prj | ENV,PRJ | 3 | S3 | implement-now (maps gap) |
| `dbtcloud_environment_variable_job_override` | JEVO | job | JOB | 4 | S3 | implement-now (maps gap) |
| `dbtcloud_account_features` | ACFT | account | ACC | 1 | S4 | implement-now |
| `dbtcloud_ip_restrictions_rule` | IPRST | account | ACC | 1 | S4 | implement-now |
| `dbtcloud_lineage_integration` | LNGI | account | ACC | 1 | S4 | implement-now |
| `dbtcloud_oauth_configuration` | OAUTH | account | ACC | 1 | S4 | guarded (sensitive) |
| `dbtcloud_project_artefacts` | PARFT | project | PRJ | 2 | S5 | implement-now |
| `dbtcloud_user_groups` | USRGRP | account | ACC | 1 | S5 | guarded (confirm scope) |
| `dbtcloud_semantic_layer_configuration` | SLCFG | project | PRJ | 2 | S6 | guarded (API research) |
| `dbtcloud_semantic_layer_credential_service_token_mapping` | SLSTM | account | ACC | 1 | S6 | guarded (API research) |

## Already supported (no action)

- PRJ, ENV, JOB, CON, REP, PREP, EXTATTR, VAR, TOK, GRP, CRD — full support
- NOT, WEB, PLE — partial (deferred; documented blockers)

## Touchpoint files (per PRD 41.02)

- `importer/models.py`, `importer/fetcher.py`, `importer/element_ids.py`
- `schemas/v2.json`, `importer/normalizer/core.py`, `importer/yaml_converter.py`
- `importer/web/utils/terraform_state_reader.py`, `importer/web/utils/protection_manager.py`
- `importer/web/components/hierarchy_index.py`, `importer/web/utils/adoption_dependencies.py`, `importer/web/utils/erd_graph_builder.py`
- `importer/web/pages/mapping.py`, `importer/web/pages/scope.py`, `importer/web/pages/deploy.py`
- `importer/web/pages/fetch_source.py`, `importer/web/pages/explore_source.py`, `importer/web/pages/explore_target.py`
- `importer/web/pages/destroy.py`, `importer/web/pages/removal_management.py`
- `modules/projects_v2/*.tf`
