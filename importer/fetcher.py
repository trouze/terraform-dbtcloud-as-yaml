"""Functions to fetch dbt Cloud account data into the internal model."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List

from slugify import slugify

from .client import DbtCloudClient
from .models import (
    AccountSnapshot,
    Connection,
    Credential,
    Environment,
    EnvironmentVariable,
    Globals,
    Job,
    Project,
    Repository,
)

log = logging.getLogger(__name__)


def slug(value: str) -> str:
    return slugify(value, separator="_")


def fetch_account_snapshot(client: DbtCloudClient) -> AccountSnapshot:
    log.info("Fetching dbt Cloud account snapshot ...")
    
    # Fetch account information
    log.info("Fetching account details (v2)")
    try:
        account_data = client.get("/", version="v2")
        account_name = account_data.get("data", {}).get("name", None)
    except Exception as exc:
        log.warning("Failed to fetch account name: %s", exc)
        account_name = None
    
    globals_model = Globals(
        connections=_fetch_connections(client),
        repositories=_fetch_repositories(client),
    )

    projects = _fetch_projects(client, globals_model)

    return AccountSnapshot(
        account_id=client.settings.account_id,
        account_name=account_name,
        globals=globals_model,
        projects=projects,
    )


def _fetch_connections(client: DbtCloudClient) -> Dict[str, Connection]:
    log.info("Fetching connections (v3)")
    connections: Dict[str, Connection] = {}
    for item in client.paginate("/connections/", version="v3"):
        key = item.get("name") or f"connection_{item['id']}"
        connection_key = slug(key)
        connections[connection_key] = Connection(
            key=connection_key,
            id=item.get("id"),
            name=item.get("name"),
            type=item.get("type"),
            details=item,
        )
    return connections


def _fetch_repositories(client: DbtCloudClient) -> Dict[str, Repository]:
    log.info("Fetching repositories (v2)")
    repositories: Dict[str, Repository] = {}
    for item in client.paginate("/repositories/"):
        name = item.get("remote_url", "repo")
        repo_key = slug(item.get("name") or name)
        repositories[repo_key] = Repository(
            key=repo_key,
            id=item.get("id"),
            remote_url=item["remote_url"],
            git_clone_strategy=item.get("git_clone_strategy"),
            metadata=item,
        )
    return repositories


def _fetch_projects(client: DbtCloudClient, globals_model: Globals) -> List[Project]:
    log.info("Fetching projects (v2)")
    projects: List[Project] = []
    for item in client.paginate("/projects/"):
        project_key = slug(item["name"])
        repository_id = item.get("repository_id")
        repository_key = _find_repo_key(globals_model.repositories, repository_id)
        project = Project(
            key=project_key,
            id=item.get("id"),
            name=item["name"],
            repository_key=repository_key,
            metadata=item,
        )
        project_id = project.id or 0
        project.environments = list(_fetch_environments(client, project_id, globals_model.connections))
        project.jobs = list(_fetch_jobs(client, project_id, project.environments))
        project.environment_variables = list(_fetch_environment_variables(client, project_id))
        projects.append(project)
    return projects


def _find_repo_key(repositories: Dict[str, Repository], repo_id: int | None) -> str | None:
    if repo_id is None:
        return None
    for repo in repositories.values():
        if repo.id == repo_id:
            return repo.key
    return None


def _fetch_environments(
    client: DbtCloudClient,
    project_id: int,
    connections: Dict[str, Connection],
) -> Iterable[Environment]:
    log.info("Fetching environments for project %s", project_id)
    for item in client.paginate("/environments/", params={"project_id": project_id}):
        env_key = slug(item["name"])
        connection_id = item.get("connection_id")
        connection_key = _find_connection_key(connections, connection_id)
        credential_data = item.get("credentials") or item.get("credential") or {}
        credential = Credential(
            token_name=credential_data.get("token_name", ""),
            schema=credential_data.get("schema", ""),
            catalog=credential_data.get("catalog"),
        )
        yield Environment(
            key=env_key,
            id=item.get("id"),
            name=item["name"],
            type=item.get("type", "development"),
            connection_key=connection_key,
            credential=credential,
            dbt_version=item.get("dbt_version"),
            custom_branch=item.get("custom_branch"),
            enable_model_query_history=item.get("enable_model_query_history"),
            metadata=item,
        )


def _fetch_jobs(client: DbtCloudClient, project_id: int, environments: list) -> Iterable[Job]:
    log.info("Fetching jobs for project %s", project_id)
    # Build a mapping of environment_id -> environment_key
    env_id_to_key = {env.id: env.key for env in environments if env.id}
    
    params = {"project_id": project_id, "order_by": "id"}
    for item in client.paginate("/jobs/", params=params):
        job_key = slug(item["name"])
        # Try to get environment from the embedded object first, then from environment_id
        environment = item.get("environment") or {}
        environment_id = environment.get("id") or item.get("environment_id")
        
        # Map environment_id to key, or fallback to slug of environment name
        if environment_id and environment_id in env_id_to_key:
            environment_key = env_id_to_key[environment_id]
        elif environment.get("name"):
            environment_key = slug(environment["name"])
        else:
            environment_key = f"env_{environment_id or 'unknown'}"
        
        yield Job(
            key=job_key,
            id=item.get("id"),
            name=item["name"],
            environment_key=environment_key,
            execute_steps=item.get("execute_steps", []),
            triggers=item.get("triggers", {}),
            settings=item,
        )


def _fetch_environment_variables(client: DbtCloudClient, project_id: int) -> Iterable[EnvironmentVariable]:
    """Fetch project-scoped environment variables (v3)."""
    log.info("Fetching environment variables for project %s (v3)", project_id)
    path = f"/projects/{project_id}/environment-variables/environment/"
    try:
        # This endpoint doesn't paginate - it returns all variables at once
        response = client.get(path, version="v3")
        
        # The response structure is: {'status': {...}, 'data': {'environments': [...], 'variables': {...}}}
        data = response.get("data", {})
        variables = data.get("variables", {})
        
        # variables is a dict like: {'VAR_NAME': {'project': {...}, 'EnvName': {...}, ...}}
        for var_name, env_values in variables.items():
            # env_values is a dict with environment names as keys (plus 'project' for the default)
            # Extract the project default value
            project_default = None
            if "project" in env_values and isinstance(env_values["project"], dict):
                project_default = env_values["project"].get("value")
            
            # Extract environment-specific values (excluding project default)
            environment_values = {
                env_name: details["value"]
                for env_name, details in env_values.items()
                if env_name != "project" and isinstance(details, dict) and "value" in details
            }
            yield EnvironmentVariable(
                name=var_name,
                project_default=project_default,
                environment_values=environment_values
            )
    except Exception as exc:  # pragma: no cover - network dependent
        log.warning("Failed to fetch environment variables for project %s: %s", project_id, exc)


def _find_connection_key(connections: Dict[str, Connection], connection_id: int | None) -> str:
    if connection_id is None:
        return "connection_unknown"
    for connection in connections.values():
        if connection.id == connection_id:
            return connection.key
    return f"connection_{connection_id}"


