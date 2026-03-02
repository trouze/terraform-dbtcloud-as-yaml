"""Contract tests enforcing resource_metadata wiring in module templates."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULES_DIR = REPO_ROOT / "modules" / "projects_v2"


def _resource_block(module_file: Path, resource_decl: str) -> str:
    lines = module_file.read_text(encoding="utf-8").splitlines()
    start = next(
        (i for i, line in enumerate(lines) if resource_decl in line),
        None,
    )
    assert start is not None, f"Missing resource declaration: {resource_decl}"

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].strip().startswith('resource "'):
            end = i
            break
    return "\n".join(lines[start:end])


def test_projects_and_extended_attributes_include_resource_metadata() -> None:
    projects_tf = MODULES_DIR / "projects.tf"
    extended_attrs_tf = MODULES_DIR / "extended_attributes.tf"

    assert "resource_metadata" in _resource_block(
        projects_tf, 'resource "dbtcloud_project" "projects"'
    )
    assert "resource_metadata" in _resource_block(
        projects_tf, 'resource "dbtcloud_project" "protected_projects"'
    )
    assert "resource_metadata" in _resource_block(
        extended_attrs_tf, 'resource "dbtcloud_extended_attributes" "extended_attrs"'
    )
    assert "resource_metadata" in _resource_block(
        extended_attrs_tf,
        'resource "dbtcloud_extended_attributes" "protected_extended_attrs"',
    )


def test_other_migrated_resources_include_resource_metadata() -> None:
    environments_tf = MODULES_DIR / "environments.tf"
    jobs_tf = MODULES_DIR / "jobs.tf"
    env_vars_tf = MODULES_DIR / "environment_vars.tf"
    globals_tf = MODULES_DIR / "globals.tf"
    projects_tf = MODULES_DIR / "projects.tf"

    required_blocks = [
        (environments_tf, 'resource "dbtcloud_environment" "environments"'),
        (environments_tf, 'resource "dbtcloud_environment" "protected_environments"'),
        (jobs_tf, 'resource "dbtcloud_job" "jobs"'),
        (jobs_tf, 'resource "dbtcloud_job" "protected_jobs"'),
        (env_vars_tf, 'resource "dbtcloud_environment_variable" "environment_variables"'),
        (
            env_vars_tf,
            'resource "dbtcloud_environment_variable" "protected_environment_variables"',
        ),
        (globals_tf, 'resource "dbtcloud_global_connection" "connections"'),
        (globals_tf, 'resource "dbtcloud_global_connection" "protected_connections"'),
        (globals_tf, 'resource "dbtcloud_service_token" "service_tokens"'),
        (globals_tf, 'resource "dbtcloud_service_token" "protected_service_tokens"'),
        (globals_tf, 'resource "dbtcloud_group" "groups"'),
        (globals_tf, 'resource "dbtcloud_group" "protected_groups"'),
        (projects_tf, 'resource "dbtcloud_repository" "repositories"'),
        (projects_tf, 'resource "dbtcloud_repository" "protected_repositories"'),
        (projects_tf, 'resource "dbtcloud_project_repository" "project_repositories"'),
        (
            projects_tf,
            'resource "dbtcloud_project_repository" "protected_project_repositories"',
        ),
    ]

    missing = [
        decl for module_file, decl in required_blocks
        if "resource_metadata" not in _resource_block(module_file, decl)
    ]
    assert not missing, f"resource_metadata missing from blocks: {missing}"


def test_resource_metadata_includes_required_identity_fields() -> None:
    modules = [
        MODULES_DIR / "projects.tf",
        MODULES_DIR / "environments.tf",
        MODULES_DIR / "jobs.tf",
        MODULES_DIR / "environment_vars.tf",
        MODULES_DIR / "extended_attributes.tf",
        MODULES_DIR / "globals.tf",
    ]
    required_fields = [
        "source_identity",
        "source_key",
        "source_name",
        "source_id",
    ]

    missing_by_file: dict[str, list[str]] = {}
    for module_file in modules:
        content = module_file.read_text(encoding="utf-8")
        missing_fields = [field for field in required_fields if field not in content]
        if missing_fields:
            missing_by_file[module_file.name] = missing_fields

    assert not missing_by_file, (
        f"Missing required resource_metadata fields: {missing_by_file}"
    )
