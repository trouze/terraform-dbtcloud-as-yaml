"""CRD matching tests for duplicate credential names across environments."""

from types import SimpleNamespace
from typing import Any

from importer.web.components.match_grid import build_grid_data


def test_crd_prefers_environment_scoped_target_over_name_lookup() -> None:
    source_items: list[dict[str, Any]] = [
        {
            "element_type_code": "CRD",
            "element_mapping_id": "src_crd_prod",
            "name": "Credential (databricks)",
            "project_name": "Platform Innovation",
            "project_key": "platform_innovation",
            "environment_name": "Production",
            "environment_key": "production",
            "dbt_id": 188,
            "credential_id": 188,
        }
    ]

    target_items: list[dict[str, Any]] = [
        # Development credential appears first and would be incorrectly selected by name-only lookup.
        {
            "element_type_code": "CRD",
            "element_mapping_id": "tgt_crd_dev",
            "name": "Credential (databricks)",
            "project_name": "Platform Innovation",
            "project_key": "platform_innovation",
            "environment_name": "Development",
            "environment_key": "development",
            "dbt_id": None,
            "credential_id": None,
        },
        {
            "element_type_code": "CRD",
            "element_mapping_id": "tgt_crd_prod",
            "name": "Credential (databricks)",
            "project_name": "Platform Innovation",
            "project_key": "platform_innovation",
            "environment_name": "Production",
            "environment_key": "production",
            "dbt_id": 188,
            "credential_id": 188,
        },
    ]

    rows = build_grid_data(
        source_items=source_items,
        target_items=target_items,
        confirmed_mappings=[],
        rejected_keys=set(),
    )

    crd_rows = [r for r in rows if r.get("source_type") == "CRD"]
    assert len(crd_rows) == 1
    row = crd_rows[0]
    assert row["target_id"] == "188"
    assert row["target_name"] == "Credential (databricks)"
    assert row["confidence"] == "env_match"


def test_crd_does_not_inherit_in_sync_without_target_id() -> None:
    state_result = SimpleNamespace(
        resources=[
            SimpleNamespace(
                address='module.dbt_cloud.module.projects_v2[0].dbtcloud_environment.environments["analytics_production"]',
                dbt_id=188,
                name="Production",
                tf_name="environments",
                element_code="ENV",
                project_id=1,
                resource_index="analytics_production",
                attributes={"id": 188},
            )
        ]
    )

    source_items: list[dict[str, Any]] = [
        {
            "element_type_code": "ENV",
            "key": "src_env_prod",
            "element_mapping_id": "src_env_prod",
            "name": "Production",
            "project_name": "Analytics",
            "project_key": "analytics",
            "dbt_id": 188,
        },
        {
            "element_type_code": "CRD",
            "key": "src_crd_prod",
            "element_mapping_id": "src_crd_prod",
            "name": "Credential (databricks)",
            "project_name": "Analytics",
            "project_key": "analytics",
            "environment_name": "Production",
            "environment_key": "production",
            "dbt_id": 20,
            "credential_id": 20,
        },
    ]

    target_items: list[dict[str, Any]] = [
        {
            "element_type_code": "ENV",
            "element_mapping_id": "tgt_env_prod",
            "name": "Production",
            "project_name": "Analytics",
            "project_key": "analytics",
            "dbt_id": 188,
        },
        {
            "element_type_code": "CRD",
            "element_mapping_id": "tgt_crd_prod",
            "name": "Credential (databricks)",
            "project_name": "Analytics",
            "project_key": "analytics",
            "environment_name": "Production",
            "environment_key": "production",
            "dbt_id": None,
            "credential_id": None,
        },
    ]

    rows = build_grid_data(
        source_items=source_items,
        target_items=target_items,
        confirmed_mappings=[],
        rejected_keys=set(),
        state_result=state_result,
        state_loaded=True,
    )

    crd_row = next(row for row in rows if row["source_type"] == "CRD")
    assert crd_row["target_id"] == ""
    assert crd_row["drift_status"] == "no_state"


def test_crd_env_match_prefers_non_null_id_among_same_env_candidates() -> None:
    source_items: list[dict[str, Any]] = [
        {
            "element_type_code": "CRD",
            "element_mapping_id": "src_crd_prod",
            "name": "Credential (databricks)",
            "project_name": "Analytics",
            "project_key": "analytics",
            "environment_name": "Production",
            "environment_key": "production",
            "dbt_id": 20,
            "credential_id": 20,
        }
    ]

    target_items: list[dict[str, Any]] = [
        # Same env, but stale/unknown row appears first with null ID.
        {
            "element_type_code": "CRD",
            "element_mapping_id": "tgt_crd_unknown",
            "name": "Credential (unknown)",
            "project_name": "Analytics",
            "project_key": "analytics",
            "environment_name": "Production",
            "environment_key": "production",
            "dbt_id": None,
            "credential_id": None,
        },
        {
            "element_type_code": "CRD",
            "element_mapping_id": "tgt_crd_databricks",
            "name": "Credential (databricks)",
            "project_name": "Analytics",
            "project_key": "analytics",
            "environment_name": "Production",
            "environment_key": "production",
            "dbt_id": 188,
            "credential_id": 188,
        },
    ]

    rows = build_grid_data(
        source_items=source_items,
        target_items=target_items,
        confirmed_mappings=[],
        rejected_keys=set(),
    )

    crd_rows = [r for r in rows if r.get("source_type") == "CRD"]
    assert len(crd_rows) == 1
    row = crd_rows[0]
    assert row["target_id"] == "188"
    assert row["target_name"] == "Credential (databricks)"
    assert row["confidence"] == "env_match"


def test_crd_env_match_uses_project_key_before_project_name() -> None:
    source_items: list[dict[str, Any]] = [
        {
            "element_type_code": "CRD",
            "element_mapping_id": "src_crd_dev",
            "name": "Credential (snowflake)",
            "project_name": "Analytics",
            "project_key": "analytics",
            "environment_name": "Development",
            "environment_key": "development",
            "dbt_id": 500,
            "credential_id": 500,
        }
    ]

    target_items: list[dict[str, Any]] = [
        # Same display names but DIFFERENT project key must not be selected.
        {
            "element_type_code": "CRD",
            "element_mapping_id": "tgt_wrong_project",
            "name": "Credential (snowflake)",
            "project_name": "Analytics",
            "project_key": "analytics_2",
            "environment_name": "Development",
            "environment_key": "development",
            "dbt_id": 501,
            "credential_id": 501,
        },
        {
            "element_type_code": "CRD",
            "element_mapping_id": "tgt_correct_project",
            "name": "Credential (snowflake)",
            "project_name": "Analytics",
            "project_key": "analytics",
            "environment_name": "Development",
            "environment_key": "development",
            "dbt_id": 999,
            "credential_id": 999,
        },
    ]

    rows = build_grid_data(
        source_items=source_items,
        target_items=target_items,
        confirmed_mappings=[],
        rejected_keys=set(),
    )

    source_rows = [r for r in rows if r.get("confidence") != "target_only"]
    assert len(source_rows) == 1
    row = source_rows[0]
    assert row["target_id"] == "999"
    assert row["target_name"] == "Credential (snowflake)"
    assert row["confidence"] == "env_match"


def test_crd_falls_back_to_env_target_when_target_crds_missing() -> None:
    source_items: list[dict[str, Any]] = [
        {
            "element_type_code": "CRD",
            "element_mapping_id": "src_crd_bronze",
            "name": "Credential (databricks)",
            "project_name": "BPE - DBT Azure",
            "project_key": "bpe_dbt_azure",
            "environment_name": "Bronze",
            "environment_key": "bronze",
            "dbt_id": 127,
            "credential_id": 127,
        }
    ]
    target_items: list[dict[str, Any]] = [
        {
            "element_type_code": "ENV",
            "element_mapping_id": "tgt_env_bronze",
            "name": "Bronze",
            "project_name": "BPE - DBT Azure",
            "project_key": "bpe_dbt_azure",
            "environment_name": "Bronze",
            "environment_key": "bronze",
            "dbt_id": 70437463668051,
        }
    ]
    state_result = SimpleNamespace(
        resources=[
            SimpleNamespace(
                address='module.dbt_cloud.module.projects_v2[0].dbtcloud_environment.environments["bpe_dbt_azure_bronze"]',
                dbt_id=70437463668051,
                name="Bronze",
                tf_name="environments",
                element_code="ENV",
                project_id=70437463664682,
                resource_index="bpe_dbt_azure_bronze",
                attributes={"id": 70437463668051},
            )
        ]
    )

    rows = build_grid_data(
        source_items=source_items,
        target_items=target_items,
        confirmed_mappings=[],
        rejected_keys=set(),
        state_result=state_result,
        state_loaded=True,
    )

    crd_rows = [r for r in rows if r.get("source_type") == "CRD"]
    assert len(crd_rows) == 1
    row = crd_rows[0]
    assert row["target_id"] == "70437463668051"
    assert row["target_name"] == "Bronze"
    assert row["confidence"] == "env_parent_match"
    assert row["drift_status"] == "in_sync"
    assert row["state_address"] == 'module.dbt_cloud.module.projects_v2[0].dbtcloud_environment.environments["bpe_dbt_azure_bronze"]'
    assert row["action"] == "match"


def test_crd_null_id_excluded_from_grid() -> None:
    """CRDs with null dbt_id (dev credentials) should not appear in the match grid."""
    source_items: list[dict[str, Any]] = [
        {
            "element_type_code": "CRD",
            "element_mapping_id": "src_crd_dev",
            "name": "Credential (snowflake)",
            "project_name": "Analytics",
            "project_key": "analytics",
            "environment_name": "Development",
            "environment_key": "development",
            "dbt_id": None,
            "credential_id": None,
        },
        {
            "element_type_code": "CRD",
            "element_mapping_id": "src_crd_prod",
            "name": "Credential (databricks)",
            "project_name": "Analytics",
            "project_key": "analytics",
            "environment_name": "Production",
            "environment_key": "production",
            "dbt_id": 20,
            "credential_id": 20,
        },
    ]

    target_items: list[dict[str, Any]] = [
        {
            "element_type_code": "CRD",
            "element_mapping_id": "tgt_crd_prod",
            "name": "Credential (databricks)",
            "project_name": "Analytics",
            "project_key": "analytics",
            "environment_name": "Production",
            "environment_key": "production",
            "dbt_id": 120,
            "credential_id": 120,
        },
    ]

    rows = build_grid_data(
        source_items=source_items,
        target_items=target_items,
        confirmed_mappings=[],
        rejected_keys=set(),
    )

    crd_rows = [r for r in rows if r["source_type"] == "CRD"]
    assert len(crd_rows) == 1, f"Expected 1 CRD row (prod only), got {len(crd_rows)}"
    assert crd_rows[0]["source_id"] == 20
    assert crd_rows[0]["source_name"] == "Credential (databricks)"


