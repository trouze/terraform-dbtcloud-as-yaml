"""Tests for environment credential ID pass-through."""

from importer.fetcher import _build_credential_from_api_data, _extract_environment_credential_id
from importer.models import Credential
from importer.normalizer.core import _build_credential_dict


def test_extract_environment_credential_id_prefers_credentials_id() -> None:
    env_item = {
        "credentials_id": 101,
        "credential_id": 202,
    }

    assert _extract_environment_credential_id(env_item) == 101


def test_extract_environment_credential_id_falls_back_to_credential_id() -> None:
    env_item = {
        "credential_id": 303,
    }

    assert _extract_environment_credential_id(env_item) == 303


def test_build_credential_from_api_data_uses_nonstandard_credential_id_field() -> None:
    env_item = {
        "id": 77,
        "name": "Development",
        "credential_id": 404,
    }
    credential_details = {
        "credential_type": "snowflake",
        "default_schema": "analytics",
        "username": "dbt_user",
    }

    credential = _build_credential_from_api_data(env_item, credential_details, "snowflake")

    assert credential.id == 404
    assert credential.credential_type == "snowflake"
    assert credential.schema == "analytics"


def test_build_credential_dict_includes_id_when_enabled() -> None:
    credential = Credential(
        id=505,
        credential_type="snowflake",
        schema="analytics",
    )

    without_id = _build_credential_dict(credential, include_source_id=False)
    with_id = _build_credential_dict(credential, include_source_id=True)

    assert "id" not in without_id
    assert with_id["id"] == 505
