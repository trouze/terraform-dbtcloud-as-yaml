"""Pre-flight probe for GitLab deploy_token repository creation.

For each deploy_token repo in the YAML, creates a test repository via the
dbt Cloud API, records whether it succeeded, then immediately deletes it.
Repos that fail are downgraded to deploy_key in the YAML before Terraform runs.

The test repos are never linked to a project_repository, so they are invisible
to end users even if cleanup fails.
"""

import logging
import re
from pathlib import Path
from typing import Any, Optional

import requests
import yaml

logger = logging.getLogger(__name__)

_TIMEOUT = 30


def _is_pat_token(api_token: str) -> bool:
    return api_token.startswith("dbtu_")


def _get_any_project_id(host_url: str, account_id: str, api_token: str) -> Optional[int]:
    """Fetch the first project ID from the target account to use as a test host."""
    try:
        resp = requests.get(
            f"{host_url}/api/v3/accounts/{account_id}/projects/",
            headers={"Authorization": f"Bearer {api_token}"},
            params={"limit": 1},
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            projects = data.get("data", []) if isinstance(data, dict) else data
            if projects:
                return projects[0].get("id")
    except Exception as e:
        logger.warning(f"Failed to list target projects: {e}")
    return None


def _create_test_repo(
    host_url: str,
    account_id: str,
    project_id: int,
    api_token: str,
    remote_url: str,
    gitlab_project_id: int,
) -> dict:
    """Attempt to create a deploy_token repo. Returns {ok, status, repo_id, error}."""
    try:
        resp = requests.post(
            f"{host_url}/api/v3/accounts/{account_id}/projects/{project_id}/repositories/",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json={
                "remote_url": remote_url,
                "git_clone_strategy": "deploy_token",
                "gitlab_project_id": gitlab_project_id,
            },
            timeout=_TIMEOUT,
        )
        body = {}
        try:
            body = resp.json()
        except Exception:
            pass

        if resp.status_code in (200, 201):
            repo_data = body.get("data", body)
            repo_id = repo_data.get("id") or repo_data.get("repository_id")
            return {"ok": True, "status": resp.status_code, "repo_id": repo_id, "error": None}

        err_detail = body.get("data", body.get("status", {}).get("developer_message", str(body)))
        return {"ok": False, "status": resp.status_code, "repo_id": None, "error": str(err_detail)[:300]}
    except requests.Timeout:
        return {"ok": False, "status": None, "repo_id": None, "error": "Request timed out"}
    except Exception as e:
        return {"ok": False, "status": None, "repo_id": None, "error": str(e)[:300]}


def _delete_repo(
    host_url: str,
    account_id: str,
    project_id: int,
    repo_id: int,
    api_token: str,
) -> bool:
    """Delete a test repository. Returns True on success."""
    try:
        resp = requests.delete(
            f"{host_url}/api/v3/accounts/{account_id}/projects/{project_id}/repositories/{repo_id}/",
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=_TIMEOUT,
        )
        return resp.status_code in (200, 204)
    except Exception as e:
        logger.warning(f"Failed to delete test repo {repo_id}: {e}")
        return False


def _convert_to_ssh_url(remote_url: str, pull_request_url_template: Optional[str] = None) -> str:
    """Convert a GitLab project path or HTTPS URL to git@host:path.git format."""
    if remote_url.startswith("git@") or remote_url.startswith("ssh://"):
        return remote_url

    gitlab_host = "gitlab.com"
    if pull_request_url_template:
        m = re.match(r"https?://([^/]+)/", pull_request_url_template)
        if m:
            gitlab_host = m.group(1)

    path = remote_url.strip()
    path = re.sub(r"^https?://[^/]+/", "", path)
    path = path.rstrip("/")
    if not path.endswith(".git"):
        path = f"{path}.git"
    return f"git@{gitlab_host}:{path}"


def _downgrade_repo(repo: dict) -> None:
    """Mutate a repo dict from deploy_token to deploy_key in place."""
    repo["git_clone_strategy"] = "deploy_key"
    repo["remote_url"] = _convert_to_ssh_url(
        repo.get("remote_url", ""),
        repo.get("pull_request_url_template"),
    )
    repo.pop("gitlab_project_id", None)


def probe_and_patch_deploy_token_repos(
    yaml_path: str,
    host_url: str,
    account_id: str,
    api_token: str,
) -> dict:
    """Create-then-delete each deploy_token repo to verify GitLab access.

    For every deploy_token repo in the YAML:
      1. POST to create it under an existing target project
      2. Record success/failure
      3. DELETE the test repo immediately (always, even on failure)
      4. On failure: downgrade the repo to deploy_key in the YAML

    Returns {total, kept, downgraded, test_project_id, repos: {key: {action, reason}}}.
    """
    yaml_p = Path(yaml_path)
    with open(yaml_p, "r") as f:
        config = yaml.safe_load(f)

    all_repos: list[dict] = []
    for project in config.get("projects", []):
        repo = project.get("repository")
        if isinstance(repo, dict):
            all_repos.append(repo)
    for repo in config.get("globals", {}).get("repositories", []):
        all_repos.append(repo)
    for repo in config.get("repositories", []):
        all_repos.append(repo)

    deploy_token_repos = [r for r in all_repos if r.get("git_clone_strategy") == "deploy_token"]
    if not deploy_token_repos:
        return {"total": 0, "kept": 0, "downgraded": 0, "test_project_id": None, "repos": {}}

    result: dict[str, Any] = {
        "total": len(deploy_token_repos),
        "kept": 0,
        "downgraded": 0,
        "test_project_id": None,
        "repos": {},
    }

    if not _is_pat_token(api_token):
        for repo in deploy_token_repos:
            key = repo.get("key", repo.get("name", "unknown"))
            _downgrade_repo(repo)
            result["downgraded"] += 1
            result["repos"][key] = {
                "action": "downgraded",
                "reason": "Service token cannot use GitLab native integration (PAT required)",
            }
        with open(yaml_p, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return result

    test_project_id = _get_any_project_id(host_url, account_id, api_token)
    result["test_project_id"] = test_project_id

    if test_project_id is None:
        for repo in deploy_token_repos:
            key = repo.get("key", repo.get("name", "unknown"))
            _downgrade_repo(repo)
            result["downgraded"] += 1
            result["repos"][key] = {
                "action": "downgraded",
                "reason": "No projects in target account to use as probe host",
            }
        with open(yaml_p, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return result

    yaml_modified = False

    for repo in deploy_token_repos:
        key = repo.get("key", repo.get("name", "unknown"))
        gitlab_project_id = repo.get("gitlab_project_id")

        if not gitlab_project_id:
            _downgrade_repo(repo)
            yaml_modified = True
            result["downgraded"] += 1
            result["repos"][key] = {"action": "downgraded", "reason": "Missing gitlab_project_id"}
            continue

        probe = _create_test_repo(
            host_url, account_id, test_project_id, api_token,
            repo.get("remote_url", ""), gitlab_project_id,
        )

        try:
            if probe["ok"] and probe["repo_id"]:
                _delete_repo(host_url, account_id, test_project_id, probe["repo_id"], api_token)
                result["kept"] += 1
                result["repos"][key] = {
                    "action": "kept",
                    "reason": f"API returned {probe['status']} — deploy_token verified",
                }
            else:
                if probe["repo_id"]:
                    _delete_repo(host_url, account_id, test_project_id, probe["repo_id"], api_token)
                _downgrade_repo(repo)
                yaml_modified = True
                result["downgraded"] += 1
                result["repos"][key] = {
                    "action": "downgraded",
                    "reason": f"API returned {probe['status']}: {probe['error']}",
                }
        except Exception as e:
            if probe.get("repo_id"):
                _delete_repo(host_url, account_id, test_project_id, probe["repo_id"], api_token)
            _downgrade_repo(repo)
            yaml_modified = True
            result["downgraded"] += 1
            result["repos"][key] = {"action": "downgraded", "reason": f"Probe exception: {e}"}

    if yaml_modified:
        with open(yaml_p, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return result
