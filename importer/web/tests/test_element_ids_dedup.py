"""Tests for project key deduplication in element_ids.apply_element_ids."""

from __future__ import annotations

from typing import Any

from importer.element_ids import apply_element_ids


def _make_payload(projects: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "account_id": 1,
        "account_name": "Test Account",
        "projects": projects,
        "globals": {},
    }


def test_duplicate_project_keys_get_deduplicated() -> None:
    """Three projects with the same key should produce analytics, analytics_2, analytics_3."""
    payload = _make_payload(
        [
            {
                "name": "Analytics",
                "key": "analytics",
                "id": 36,
                "environments": [
                    {
                        "name": "Development",
                        "key": "development",
                        "credential": {"credential_type": "snowflake"},
                    }
                ],
                "jobs": [],
                "environment_variables": [],
                "extended_attributes": [],
            },
            {
                "name": "Analytics",
                "key": "analytics",
                "id": 33,
                "environments": [
                    {
                        "name": "Development",
                        "key": "development",
                        "credential": {"credential_type": "snowflake"},
                    }
                ],
                "jobs": [],
                "environment_variables": [],
                "extended_attributes": [],
            },
            {
                "name": "Analytics",
                "key": "analytics",
                "id": 1,
                "environments": [
                    {
                        "name": "Production",
                        "key": "production",
                        "credential": {"credential_type": "databricks", "id": 20},
                    }
                ],
                "jobs": [],
                "environment_variables": [],
                "extended_attributes": [],
            },
        ]
    )

    records = apply_element_ids(payload)

    prj_records = [r for r in records if r["element_type_code"] == "PRJ"]
    assert len(prj_records) == 3
    prj_keys = [r["project_key"] for r in prj_records]
    assert prj_keys == ["analytics", "analytics_2", "analytics_3"]


def test_crd_element_mapping_ids_unique_across_duplicate_projects() -> None:
    """CRDs in projects sharing the same key must get distinct element_mapping_ids."""
    payload = _make_payload(
        [
            {
                "name": "Analytics",
                "key": "analytics",
                "id": 36,
                "environments": [
                    {
                        "name": "Production",
                        "key": "production",
                        "credential": {"credential_type": "snowflake", "id": 100},
                    }
                ],
                "jobs": [],
                "environment_variables": [],
                "extended_attributes": [],
            },
            {
                "name": "Analytics",
                "key": "analytics",
                "id": 33,
                "environments": [
                    {
                        "name": "Production",
                        "key": "production",
                        "credential": {"credential_type": "snowflake", "id": 200},
                    }
                ],
                "jobs": [],
                "environment_variables": [],
                "extended_attributes": [],
            },
        ]
    )

    records = apply_element_ids(payload)

    crd_records = [r for r in records if r["element_type_code"] == "CRD"]
    assert len(crd_records) == 2

    crd_eids = [r["element_mapping_id"] for r in crd_records]
    assert len(set(crd_eids)) == 2, f"CRD element_mapping_ids must be unique: {crd_eids}"

    assert crd_records[0]["project_key"] == "analytics"
    assert crd_records[1]["project_key"] == "analytics_2"


def test_null_id_credentials_excluded_from_records() -> None:
    """CRDs with null credential IDs (dev env) should be excluded entirely."""
    payload = _make_payload(
        [
            {
                "name": "Analytics",
                "key": "analytics",
                "id": 1,
                "environments": [
                    {
                        "name": "Development",
                        "key": "development",
                        "credential": {"credential_type": "snowflake"},
                    },
                    {
                        "name": "Production",
                        "key": "production",
                        "credential": {"credential_type": "databricks", "id": 20},
                    },
                ],
                "jobs": [],
                "environment_variables": [],
                "extended_attributes": [],
            },
        ]
    )

    records = apply_element_ids(payload)

    crd_records = [r for r in records if r["element_type_code"] == "CRD"]
    assert len(crd_records) == 1, (
        f"Only CRDs with valid IDs should be registered, got {len(crd_records)}"
    )

    prod_crd = crd_records[0]
    assert prod_crd["dbt_id"] == 20
    assert prod_crd["environment_key"] == "production"
    assert prod_crd["credential_type"] == "databricks"


def test_env_keys_scoped_by_deduped_project_key() -> None:
    """ENV records in duplicate projects carry the deduped project_key."""
    payload = _make_payload(
        [
            {
                "name": "Analytics",
                "key": "analytics",
                "id": 36,
                "environments": [
                    {"name": "Development", "key": "development"},
                ],
                "jobs": [],
                "environment_variables": [],
                "extended_attributes": [],
            },
            {
                "name": "Analytics",
                "key": "analytics",
                "id": 33,
                "environments": [
                    {"name": "Development", "key": "development"},
                ],
                "jobs": [],
                "environment_variables": [],
                "extended_attributes": [],
            },
        ]
    )

    records = apply_element_ids(payload)

    env_records = [r for r in records if r["element_type_code"] == "ENV"]
    assert len(env_records) == 2
    assert env_records[0]["project_key"] == "analytics"
    assert env_records[1]["project_key"] == "analytics_2"
