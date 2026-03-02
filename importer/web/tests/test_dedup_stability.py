"""Tests for deterministic project key deduplication ordering.

The dedup logic must produce STABLE key assignments regardless of the order
projects arrive from the API. The project with the lowest ID always gets the
base key; higher IDs get _2, _3, etc.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from importer.element_ids import apply_element_ids


def _make_payload(projects: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "account_id": 1,
        "account_name": "Test Account",
        "projects": projects,
        "globals": {},
    }


def _make_project(project_id: int, key: str = "analytics", name: str = "Analytics") -> dict:
    return {
        "name": name,
        "key": key,
        "id": project_id,
        "environments": [],
        "jobs": [],
        "environment_variables": [],
        "extended_attributes": [],
    }


class TestDedupStability:
    """Dedup suffix assignment must be deterministic regardless of input order."""

    def test_lowest_id_gets_base_key_forward_order(self):
        """When projects arrive [id=1, id=33, id=36], id=1 gets base key."""
        payload = _make_payload([
            _make_project(1),
            _make_project(33),
            _make_project(36),
        ])
        records = apply_element_ids(payload)
        prj_records = [r for r in records if r["element_type_code"] == "PRJ"]

        assert prj_records[0]["dbt_id"] == 1
        assert prj_records[0]["project_key"] == "analytics"
        assert prj_records[1]["dbt_id"] == 33
        assert prj_records[1]["project_key"] == "analytics_2"
        assert prj_records[2]["dbt_id"] == 36
        assert prj_records[2]["project_key"] == "analytics_3"

    def test_lowest_id_gets_base_key_reverse_order(self):
        """When projects arrive [id=36, id=33, id=1], id=1 still gets base key."""
        payload = _make_payload([
            _make_project(36),
            _make_project(33),
            _make_project(1),
        ])
        records = apply_element_ids(payload)
        prj_records = [r for r in records if r["element_type_code"] == "PRJ"]

        assert prj_records[0]["dbt_id"] == 1
        assert prj_records[0]["project_key"] == "analytics"
        assert prj_records[1]["dbt_id"] == 33
        assert prj_records[1]["project_key"] == "analytics_2"
        assert prj_records[2]["dbt_id"] == 36
        assert prj_records[2]["project_key"] == "analytics_3"

    def test_lowest_id_gets_base_key_shuffled_order(self):
        """When projects arrive [id=33, id=1, id=36], id=1 still gets base key."""
        payload = _make_payload([
            _make_project(33),
            _make_project(1),
            _make_project(36),
        ])
        records = apply_element_ids(payload)
        prj_records = [r for r in records if r["element_type_code"] == "PRJ"]

        assert prj_records[0]["dbt_id"] == 1
        assert prj_records[0]["project_key"] == "analytics"
        assert prj_records[1]["dbt_id"] == 33
        assert prj_records[1]["project_key"] == "analytics_2"
        assert prj_records[2]["dbt_id"] == 36
        assert prj_records[2]["project_key"] == "analytics_3"

    def test_two_projects_swap_order_same_keys(self):
        """Two projects with same key produce identical assignments regardless of order."""
        for order in ([33, 36], [36, 33]):
            payload = _make_payload([_make_project(pid) for pid in order])
            records = apply_element_ids(payload)
            prj_records = [r for r in records if r["element_type_code"] == "PRJ"]

            id_to_key = {r["dbt_id"]: r["project_key"] for r in prj_records}
            assert id_to_key[33] == "analytics", f"Input order {order}: id=33 should get base key"
            assert id_to_key[36] == "analytics_2", f"Input order {order}: id=36 should get _2"

    def test_mixed_keys_only_colliding_keys_get_suffix(self):
        """Projects with unique keys are unaffected; only colliding keys get suffixed."""
        payload = _make_payload([
            _make_project(50, key="analytics"),
            _make_project(10, key="marketing"),
            _make_project(20, key="analytics"),
        ])
        records = apply_element_ids(payload)
        prj_records = [r for r in records if r["element_type_code"] == "PRJ"]

        id_to_key = {r["dbt_id"]: r["project_key"] for r in prj_records}
        assert id_to_key[10] == "marketing"
        assert id_to_key[20] == "analytics"
        assert id_to_key[50] == "analytics_2"

    def test_children_inherit_stable_project_key(self):
        """ENV and CRD records inherit the deduped project_key from their parent."""
        for order in ([33, 36], [36, 33]):
            projects = []
            for pid in order:
                p = _make_project(pid)
                p["environments"] = [
                    {
                        "name": "Prod",
                        "key": "prod",
                        "credential": {"credential_type": "snowflake", "id": pid * 10},
                    }
                ]
                projects.append(p)

            payload = _make_payload(projects)
            records = apply_element_ids(payload)

            env_records = [r for r in records if r["element_type_code"] == "ENV"]
            crd_records = [r for r in records if r["element_type_code"] == "CRD"]

            env_by_project = {r["project_key"]: r for r in env_records}
            crd_by_project = {r["project_key"]: r for r in crd_records}

            assert "analytics" in env_by_project, f"Order {order}: base key ENV missing"
            assert "analytics_2" in env_by_project, f"Order {order}: _2 key ENV missing"
            assert "analytics" in crd_by_project, f"Order {order}: base key CRD missing"
            assert "analytics_2" in crd_by_project, f"Order {order}: _2 key CRD missing"

    def test_no_id_projects_sorted_by_name_then_key(self):
        """Projects without IDs fall back to name/key sort for stability."""
        payload = _make_payload([
            {"name": "Zulu", "key": "analytics", "environments": [], "jobs": [],
             "environment_variables": [], "extended_attributes": []},
            {"name": "Alpha", "key": "analytics", "environments": [], "jobs": [],
             "environment_variables": [], "extended_attributes": []},
        ])
        records = apply_element_ids(payload)
        prj_records = [r for r in records if r["element_type_code"] == "PRJ"]

        assert prj_records[0]["name"] == "Alpha"
        assert prj_records[0]["project_key"] == "analytics"
        assert prj_records[1]["name"] == "Zulu"
        assert prj_records[1]["project_key"] == "analytics_2"
