"""Tests for deploy-time source ID backfill helpers."""

import json
from pathlib import Path

import yaml

from importer.web.pages.deploy import (
    _backfill_environment_ids_from_source_report,
    _backfill_job_ids_from_source_report,
)


def test_backfill_environment_ids_uses_project_suffix_fallback(tmp_path: Path) -> None:
    yaml_file = tmp_path / "dbt-cloud-config.yml"
    report_file = tmp_path / "report_items.json"

    yaml_file.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "projects": [
                    {
                        "key": "analytics_3",
                        "name": "Analytics",
                        "id": 1,
                        "repository": None,
                        "environments": [
                            {"key": "development", "name": "Development", "type": "development"},
                            {"key": "prod", "name": "Prod", "type": "deployment"},
                        ],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    report_file.write_text(
        json.dumps(
            [
                {
                    "element_type_code": "ENV",
                    "project_key": "analytics",
                    "key": "development",
                    "dbt_id": 1,
                },
                {
                    "element_type_code": "ENV",
                    "project_key": "analytics",
                    "key": "prod",
                    "dbt_id": 6,
                },
            ]
        ),
        encoding="utf-8",
    )

    metrics = _backfill_environment_ids_from_source_report(str(yaml_file), str(report_file))

    assert metrics["updated"] is True
    assert metrics["filled_count"] == 2
    assert metrics["fallback_filled_count"] == 2
    updated = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    envs = updated["projects"][0]["environments"]
    assert envs[0]["id"] == 1
    assert envs[1]["id"] == 6


def test_backfill_environment_ids_noop_when_none_missing(tmp_path: Path) -> None:
    yaml_file = tmp_path / "dbt-cloud-config.yml"
    report_file = tmp_path / "report_items.json"

    yaml_file.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "projects": [
                    {
                        "key": "analytics",
                        "name": "Analytics",
                        "environments": [
                            {"key": "prod", "name": "Prod", "type": "deployment", "id": 6}
                        ],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    report_file.write_text("[]", encoding="utf-8")

    metrics = _backfill_environment_ids_from_source_report(str(yaml_file), str(report_file))

    assert metrics["updated"] is False
    assert metrics["missing_before"] == 0
    assert metrics["filled_count"] == 0


def test_backfill_job_ids_uses_project_suffix_fallback(tmp_path: Path) -> None:
    yaml_file = tmp_path / "dbt-cloud-config.yml"
    report_file = tmp_path / "report_items.json"

    yaml_file.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "projects": [
                    {
                        "key": "analytics_3",
                        "name": "Analytics",
                        "jobs": [
                            {"key": "deployjb1", "name": "Deployjb1"},
                            {"key": "deployjb2", "name": "Deployjb2"},
                        ],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    report_file.write_text(
        json.dumps(
            [
                {
                    "element_type_code": "JOB",
                    "project_key": "analytics",
                    "key": "deployjb1",
                    "dbt_id": 2,
                },
                {
                    "element_type_code": "JOB",
                    "project_key": "analytics",
                    "key": "deployjb2",
                    "dbt_id": 3,
                },
            ]
        ),
        encoding="utf-8",
    )

    metrics = _backfill_job_ids_from_source_report(str(yaml_file), str(report_file))

    assert metrics["updated"] is True
    assert metrics["filled_count"] == 2
    assert metrics["fallback_filled_count"] == 2
    updated = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    jobs = updated["projects"][0]["jobs"]
    assert jobs[0]["id"] == 2
    assert jobs[1]["id"] == 3
