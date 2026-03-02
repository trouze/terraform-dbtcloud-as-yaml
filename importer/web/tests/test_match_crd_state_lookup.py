"""Unit tests for CRD details state lookup via parent ENV rows."""

from types import SimpleNamespace
from typing import Any

from importer.web.pages.match import _resolve_crd_parent_env_state_resource


def test_resolve_crd_parent_env_state_resource_uses_parent_env_address() -> None:
    env_res = SimpleNamespace(
        address='module.dbt_cloud.module.projects_v2[0].dbtcloud_environment.environments["analytics_development"]',
        dbt_id=70437463668034,
        name="Development",
        tf_name="environments",
        element_code="ENV",
        project_id=70437463664689,
        resource_index="analytics_development",
        attributes={"id": 70437463668034},
    )
    state_result: Any = SimpleNamespace(resources=[env_res])
    source_item = {"environment_name": "Development", "project_name": "Analytics"}
    grid_row = {"project_name": "Analytics"}
    grid_rows = [
        {
            "source_type": "ENV",
            "project_name": "Analytics",
            "source_name": "Development",
            "state_address": env_res.address,
        }
    ]

    resolved = _resolve_crd_parent_env_state_resource(
        source_item=source_item,
        grid_row=grid_row,
        grid_rows=grid_rows,
        state_result=state_result,
    )

    assert resolved is not None
    assert resolved["element_code"] == "ENV"
    assert resolved["address"] == env_res.address
    assert resolved["name"] == "Development"


def test_resolve_crd_parent_env_state_resource_returns_none_without_parent_env_row() -> None:
    env_res = SimpleNamespace(
        address='module.dbt_cloud.module.projects_v2[0].dbtcloud_environment.environments["analytics_development"]',
        dbt_id=70437463668034,
        name="Development",
        tf_name="environments",
        element_code="ENV",
        project_id=70437463664689,
        resource_index="analytics_development",
        attributes={"id": 70437463668034},
    )
    state_result: Any = SimpleNamespace(resources=[env_res])

    resolved = _resolve_crd_parent_env_state_resource(
        source_item={"environment_name": "Development", "project_name": "Analytics"},
        grid_row={"project_name": "Analytics"},
        grid_rows=[],
        state_result=state_result,
    )

    assert resolved is None
