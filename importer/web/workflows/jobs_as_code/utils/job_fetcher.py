"""Job fetching utilities for Jobs as Code Generator."""

import re
from typing import Optional

import httpx


class JobFetchError(Exception):
    """Error occurred while fetching jobs from dbt Cloud API."""
    pass


def fetch_jobs_from_api(
    host_url: str,
    account_id: str,
    api_token: str,
    project_ids: Optional[list[int]] = None,
    environment_ids: Optional[list[int]] = None,
) -> list[dict]:
    """Fetch jobs from dbt Cloud API.
    
    Args:
        host_url: dbt Cloud host URL (e.g., https://cloud.getdbt.com)
        account_id: dbt Cloud account ID
        api_token: dbt Cloud API token
        project_ids: Optional list of project IDs to filter by
        environment_ids: Optional list of environment IDs to filter by
        
    Returns:
        List of job dictionaries from the API
        
    Raises:
        JobFetchError: If the API request fails
    """
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    
    base_url = host_url.rstrip("/")
    jobs: list[dict] = []
    offset = 0
    
    while True:
        params: dict = {"offset": offset}
        
        if project_ids and len(project_ids) == 1:
            params["project_id"] = project_ids[0]
        elif project_ids and len(project_ids) > 1:
            params["project_id__in"] = f"[{','.join(str(i) for i in project_ids)}]"
        
        if environment_ids and len(environment_ids) == 1:
            params["environment_id"] = environment_ids[0]
        elif environment_ids and len(environment_ids) > 1:
            # Make multiple requests for multiple environments
            for env_id in environment_ids:
                env_jobs = fetch_jobs_from_api(
                    host_url, account_id, api_token, project_ids, [env_id]
                )
                jobs.extend(env_jobs)
            return jobs
            
        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    f"{base_url}/api/v2/accounts/{account_id}/jobs/",
                    headers=headers,
                    params=params,
                )
                
                if response.status_code == 401:
                    raise JobFetchError("401 Unauthorized - Check your API key")
                elif response.status_code == 404:
                    raise JobFetchError(f"404 Not Found - Account {account_id} not found")
                elif response.status_code >= 400:
                    raise JobFetchError(f"API error: {response.status_code} - {response.text}")
                
                try:
                    data = response.json()
                except Exception as json_err:
                    raise JobFetchError(f"Invalid JSON response: {str(json_err)}")
                
                if data is None:
                    raise JobFetchError("API returned empty response")
                
                if not isinstance(data, dict):
                    raise JobFetchError(f"Unexpected response type: {type(data)}")
                
                jobs.extend(data.get("data", []))
                
                # Check pagination
                extra = data.get("extra") or {}
                filters = extra.get("filters") or {}
                pagination = extra.get("pagination") or {}
                
                limit = filters.get("limit", 100)
                current_offset = filters.get("offset", 0)
                total_count = pagination.get("total_count", 0)
                
                if current_offset + limit >= total_count:
                    break
                    
                offset += limit
            
        except httpx.RequestError as e:
            raise JobFetchError(f"Network error: {str(e)}")
    
    return jobs


def extract_projects_from_jobs(jobs: list[dict]) -> dict[int, str]:
    """Extract unique projects from job list.
    
    Args:
        jobs: List of job dictionaries
        
    Returns:
        Dictionary mapping project_id to project_name
    """
    projects: dict[int, str] = {}
    
    for job in jobs:
        project_id = job.get("project_id")
        if project_id and project_id not in projects:
            # Try to get project name from nested project object
            # Handle case where project is None or missing
            project = job.get("project") or {}
            project_name = project.get("name", f"Project {project_id}") if isinstance(project, dict) else f"Project {project_id}"
            projects[project_id] = project_name
            
    return projects


def extract_environments_from_jobs(jobs: list[dict]) -> dict[int, dict]:
    """Extract unique environments from job list.
    
    Args:
        jobs: List of job dictionaries
        
    Returns:
        Dictionary mapping environment_id to environment info dict
    """
    environments: dict[int, dict] = {}
    
    for job in jobs:
        env_id = job.get("environment_id")
        if env_id and env_id not in environments:
            # Try to get environment info from nested environment object
            # Handle case where environment is None or missing
            env = job.get("environment") or {}
            env_name = env.get("name", f"Environment {env_id}") if isinstance(env, dict) else f"Environment {env_id}"
            environments[env_id] = {
                "id": env_id,
                "name": env_name,
                "project_id": job.get("project_id"),
            }
            
    return environments


def parse_job_identifier(job_name: str) -> tuple[Optional[str], str]:
    """Parse job identifier from job name.
    
    Jobs managed by dbt-jobs-as-code have identifiers in [[identifier]] format.
    
    Args:
        job_name: The job name to parse
        
    Returns:
        Tuple of (identifier, clean_name) where identifier is None if not managed
    """
    match = re.search(r"\[\[([*:a-zA-Z0-9_-]+)\]\]", job_name)
    
    if match:
        raw_identifier = match.group(1)
        # Handle prefix:identifier format
        if ":" in raw_identifier:
            _, identifier = raw_identifier.split(":", 1)
        else:
            identifier = raw_identifier
            
        # Remove identifier from name
        clean_name = job_name.replace(f" [[{raw_identifier}]]", "").strip()
        return identifier, clean_name
        
    return None, job_name


def is_job_managed(job: dict) -> bool:
    """Check if a job is already managed by dbt-jobs-as-code.
    
    Args:
        job: Job dictionary from API
        
    Returns:
        True if job has [[identifier]] in name
    """
    identifier, _ = parse_job_identifier(job.get("name", ""))
    return identifier is not None
