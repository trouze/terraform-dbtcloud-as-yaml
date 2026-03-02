"""Tests for Match source selection expansion."""

from importer.web.pages.match import _expand_selected_entity_ids


def test_expand_selected_entity_ids_includes_project_descendants() -> None:
    """Selecting a project should include ENV/CRD descendants in Match."""
    entities = [
        {"element_mapping_id": "acc_1", "element_type_code": "ACC", "name": "Account"},
        {"element_mapping_id": "prj_1", "element_type_code": "PRJ", "name": "Project", "key": "project"},
        {
            "element_mapping_id": "env_1",
            "element_type_code": "ENV",
            "name": "Development",
            "parent_project_id": "prj_1",
        },
        {
            "element_mapping_id": "crd_1",
            "element_type_code": "CRD",
            "name": "Credential (snowflake)",
            "parent_environment_id": "env_1",
        },
    ]

    expanded = _expand_selected_entity_ids(entities, {"prj_1"})

    assert "prj_1" in expanded
    assert "env_1" in expanded
    assert "crd_1" in expanded
