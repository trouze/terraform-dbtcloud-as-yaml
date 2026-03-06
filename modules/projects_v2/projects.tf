#############################################
# Projects
# 
# Creates dbt Cloud projects and their repositories.
# Each project references a repository (by key or inline object).
# Supports protected resources with lifecycle.prevent_destroy.
#############################################

locals {
  repository_ssh_fallback_url = "git@github.com:dbt-labs/jaffle-shop.git"

  # Resolve repository references
  # The normalizer outputs repository references as string keys (e.g., "jaffle_shop")
  # We look them up in repositories_map to get the full repository object
  resolve_repository = {
    for project in var.projects :
    project.key => (
      # Handle null repository
      project.repository == null ? null :
      # Handle LOOKUP placeholder (unresolved reference)
      can(regex("^LOOKUP:", tostring(project.repository))) ? null :
      # Try to look up string key in repositories_map
      # try() returns null if the key doesn't exist or if project.repository isn't a valid key
      try(local.repositories_map[project.repository], null)
    )
  }

  # Filter projects that have valid repositories (not null, not LOOKUP)
  projects_with_repositories = {
    for project in var.projects :
    project.key => project
    if local.resolve_repository[project.key] != null
  }

  # Check if any GitLab repositories exist (require PAT)
  has_gitlab_repositories = length([
    for key, project in local.projects_with_repositories :
    key if try(local.resolve_repository[key].git_clone_strategy, "") == "deploy_token"
  ]) > 0

  # Determine effective git clone strategy for each repository
  # Preserve explicit non-deploy_key strategies from source YAML when possible.
  # If github_app is specified but no PAT/installation ID is available, fallback to deploy_key.
  # When github_installation_id is provided, API automatically uses github_app, so we must match that.
  # Use nonsensitive() to prevent strategy string from inheriting PAT's sensitivity
  #
  # deploy_token (GitLab native) repos are downgraded to deploy_key unless
  # var.enable_gitlab_deploy_token is true.  The dbt Cloud v3 API can return 500
  # when the PAT owner's GitLab OAuth token lacks access to the project (unhandled
  # GitlabGetError — backend fix pending in dbt-cloud PR #16687).
  # When the user has confirmed their GitLab linkage and project access, they can
  # set enable_gitlab_deploy_token = true to preserve the native strategy.
  # See: bugs/bug3-gitlab-deploy-token-pat.md
  effective_git_clone_strategy = {
    for key, repo in local.resolve_repository :
    key => nonsensitive(
      # If Azure integration strategy is selected but required Azure IDs are missing, force deploy_key.
      # This avoids API failures when integrations are not configured in the target account yet.
      try(repo.git_clone_strategy, "") == "azure_active_directory_app" && (
        trimspace(tostring(try(repo.azure_active_directory_project_id, ""))) == "" ||
        trimspace(tostring(try(repo.azure_active_directory_repository_id, ""))) == ""
      ) ? "deploy_key" :
      # GitLab deploy_token: use native strategy when enabled, otherwise fall back to deploy_key
      try(repo.git_clone_strategy, "") == "deploy_token" ? (
        var.enable_gitlab_deploy_token ? "deploy_token" : "deploy_key"
      ) :
      # If github_installation_id is provided, API will use github_app regardless of what we send
      # So we must set it to github_app to match API behavior and avoid replacement
      local.effective_github_installation_id[key] != null ? "github_app" :
      # If explicitly set, use it (unless github_app without PAT)
      try(repo.git_clone_strategy, null) != null ? (
        try(repo.git_clone_strategy, "") == "github_app" && local.github_installation_id == null ?
        "deploy_key" : # Fallback to deploy_key if github_app but no PAT
        try(repo.git_clone_strategy, null)
      ) : null # Let Terraform/provider auto-detect
    )
  }

  # Detect repos that were downgraded from deploy_token to deploy_key.
  # Their remote_url is a GitLab project path (e.g., "group/project") that must
  # be converted to SSH format for the deploy_key strategy.
  # When enable_gitlab_deploy_token is true, no downgrade occurs and the original
  # remote_url + gitlab_project_id are preserved.
  gitlab_deploy_token_downgraded = {
    for key, repo in local.resolve_repository :
    key => try(repo.git_clone_strategy, "") == "deploy_token" && local.effective_git_clone_strategy[key] == "deploy_key"
  }

  # Extract GitLab hostname from pull_request_url_template for SSH URL construction.
  # Template format: "https://gitlab.example.com/group/proj/-/merge_requests/new?..."
  # Falls back to "gitlab.com" for SaaS GitLab.
  gitlab_ssh_host = {
    for key, repo in local.resolve_repository :
    key => try(regex("https?://([^/]+)/", try(repo.pull_request_url_template, ""))[0], "gitlab.com")
  }

  # Determine effective remote URL per repo.
  # - deploy_key repos require SSH-style URLs; fall back to a known-good one.
  # - github_app repos use their original URL (may be git://, https://, or SSH).
  # - azure_active_directory_app repos use their original URL.
  # - GitLab repos downgraded from deploy_token → deploy_key get their path
  #   converted to git@gitlab.com:<path>.git
  effective_repository_remote_url = {
    for key, repo in local.resolve_repository :
    key => (
      local.gitlab_deploy_token_downgraded[key] ? (
        "git@${local.gitlab_ssh_host[key]}:${trimspace(try(repo.remote_url, ""))}.git"
      ) :
      local.effective_git_clone_strategy[key] == "github_app" ||
      local.effective_git_clone_strategy[key] == "azure_active_directory_app"
      ? trimspace(try(repo.remote_url, local.repository_ssh_fallback_url))
      : (
        can(regex("^(git@|ssh:)", trimspace(try(repo.remote_url, "")))) ?
        trimspace(try(repo.remote_url, "")) :
        local.repository_ssh_fallback_url
      )
    )
    if repo != null
  }

  # Extract GitHub owner from remote_url for per-repo installation matching.
  # Supports formats: git@github.com:OWNER/repo, git://github.com/OWNER/repo,
  # https://github.com/OWNER/repo, ssh://git@github.com/OWNER/repo
  repo_github_owner = {
    for key, repo in local.resolve_repository :
    key => lower(try(
      regex("github\\.com[:/]([^/]+)/", try(repo.remote_url, ""))[0],
      ""
    ))
  }

  # Determine effective GitHub installation ID by matching repo owner to installation.
  # An account may have multiple GitHub App installations (e.g., one per org/user).
  # We match the repo's GitHub owner to the installation's account.login.
  effective_github_installation_id = {
    for key, repo in local.resolve_repository :
    key => (
      try(repo.git_clone_strategy, "") == "github_app" ? (
        # 1. Match repo owner to a specific installation
        lookup(local.github_installation_by_owner, local.repo_github_owner[key], null) != null ?
        lookup(local.github_installation_by_owner, local.repo_github_owner[key], null) :
        # 2. Fallback to first discovered installation
        local.github_installation_id != null ? local.github_installation_id :
        # 3. Last resort: per-repo github_installation_id (adoption workflows)
        try(repo.github_installation_id, null)
      ) :
      null
    )
  }

  #############################################
  # Protection: Split projects into protected/unprotected
  # 
  # Two independent protection scopes:
  # - protected: Controls project resource protection (independent)
  # - repository_protected: Controls repository + project_repository protection
  #   Falls back to `protected` if not explicitly set, for backward compatibility
  #############################################

  # All projects as a map
  all_projects_map = {
    for project in var.projects :
    project.key => project
  }

  # Protected projects (protected: true)
  protected_projects_map = {
    for key, project in local.all_projects_map :
    key => project
    if try(project.protected, false) == true
  }

  # Unprotected projects (protected: false or not set)
  unprotected_projects_map = {
    for key, project in local.all_projects_map :
    key => project
    if try(project.protected, false) != true
  }

  # Determine effective repository protection status
  # Uses repository_protected if explicitly set, otherwise falls back to project.protected
  # This enables independent protection: protect project but not repo, or vice versa
  effective_repository_protected = {
    for key, project in local.all_projects_map :
    key => (
      # If repository_protected is explicitly set (true or false), use it
      try(project.repository_protected, null) != null ? project.repository_protected :
      # Otherwise fall back to project.protected for backward compatibility
      try(project.protected, false)
    )
  }

  # Protected repositories (based on effective_repository_protected)
  protected_repositories_map = {
    for key, project in local.all_projects_map :
    key => project
    if local.effective_repository_protected[key] == true && local.resolve_repository[key] != null
  }

  # Unprotected repositories (based on effective_repository_protected)
  unprotected_repositories_map = {
    for key, project in local.all_projects_map :
    key => project
    if local.effective_repository_protected[key] != true && local.resolve_repository[key] != null
  }

}

#############################################
# Unprotected Projects - standard lifecycle
#############################################

resource "dbtcloud_project" "projects" {
  for_each = local.unprotected_projects_map

  name = each.value.name

  resource_metadata = {
    source_project_id = try(each.value.id, null)
    source_id         = try(each.value.id, null)
    source_identity   = "PRJ:${each.key}"
    source_key        = each.key
    source_name       = each.value.name
  }
}

#############################################
# Protected Projects - prevent_destroy lifecycle
#############################################

resource "dbtcloud_project" "protected_projects" {
  for_each = local.protected_projects_map

  name = each.value.name

  resource_metadata = {
    source_project_id = try(each.value.id, null)
    source_id         = try(each.value.id, null)
    source_identity   = "PRJ:${each.key}"
    source_key        = each.key
    source_name       = each.value.name
  }

  lifecycle {
    prevent_destroy = true
  }
}

#############################################
# Unprotected Repositories - standard lifecycle
# Uses effective_repository_protected (independent of project protection)
#############################################

# Note: GitLab repositories (deploy_token strategy) require a PAT - use TF_VAR_dbt_token with PAT
resource "dbtcloud_repository" "repositories" {
  for_each = local.unprotected_repositories_map

  # Reference the correct project resource based on PROJECT protection status
  # (repo protection is independent - repo can be unprotected while project is protected)
  project_id = (
    contains(keys(local.protected_projects_map), each.key) ?
    dbtcloud_project.protected_projects[each.key].id :
    dbtcloud_project.projects[each.key].id
  )
  remote_url = local.effective_repository_remote_url[each.key]

  # Git clone strategy (with fallback to deploy_key if github_app without PAT)
  git_clone_strategy = local.effective_git_clone_strategy[each.key]

  is_active = try(local.resolve_repository[each.key].is_active, true)

  # GitHub native integration
  github_installation_id = local.effective_github_installation_id[each.key]

  resource_metadata = {
    source_project_id  = try(each.value.id, null)
    source_id          = try(local.resolve_repository[each.key].id, null)
    source_identity    = "REP:${each.key}"
    source_key         = each.key
    source_project_key = each.key
    source_name        = try(local.resolve_repository[each.key].name, each.key)
  }

  # GitLab native integration (nulled when downgraded from deploy_token to deploy_key)
  gitlab_project_id = local.gitlab_deploy_token_downgraded[each.key] ? null : try(
    local.resolve_repository[each.key].gitlab_project_id,
    null
  )

  # Azure DevOps native integration
  azure_active_directory_project_id = try(
    local.resolve_repository[each.key].azure_active_directory_project_id,
    null
  )
  azure_active_directory_repository_id = try(
    local.resolve_repository[each.key].azure_active_directory_repository_id,
    null
  )
  azure_bypass_webhook_registration_failure = try(
    local.resolve_repository[each.key].azure_bypass_webhook_registration_failure,
    false
  )

  # PrivateLink endpoint reference
  private_link_endpoint_id = try(
    local.resolve_repository[each.key].private_link_endpoint_key != null ?
    lookup(
      {
        for ple in data.dbtcloud_privatelink_endpoints.all.endpoints :
        ple.id => ple.id
      },
      lookup(local.privatelink_endpoints_map, local.resolve_repository[each.key].private_link_endpoint_key, {}).endpoint_id,
      null
    ) : null,
    null
  )

  pull_request_url_template = try(
    local.resolve_repository[each.key].pull_request_url_template,
    null
  )
}

#############################################
# Protected Repositories - prevent_destroy lifecycle
# Uses effective_repository_protected (independent of project protection)
#############################################

resource "dbtcloud_repository" "protected_repositories" {
  for_each = local.protected_repositories_map

  # Reference the correct project resource based on PROJECT protection status
  # (repo protection is independent - repo can be protected while project is unprotected)
  project_id = (
    contains(keys(local.protected_projects_map), each.key) ?
    dbtcloud_project.protected_projects[each.key].id :
    dbtcloud_project.projects[each.key].id
  )
  remote_url = local.effective_repository_remote_url[each.key]

  # Git clone strategy (with fallback to deploy_key if github_app without PAT)
  git_clone_strategy = local.effective_git_clone_strategy[each.key]

  is_active = try(local.resolve_repository[each.key].is_active, true)

  # GitHub native integration
  github_installation_id = local.effective_github_installation_id[each.key]

  resource_metadata = {
    source_project_id  = try(each.value.id, null)
    source_id          = try(local.resolve_repository[each.key].id, null)
    source_identity    = "REP:${each.key}"
    source_key         = each.key
    source_project_key = each.key
    source_name        = try(local.resolve_repository[each.key].name, each.key)
  }

  # GitLab native integration (nulled when downgraded from deploy_token to deploy_key)
  gitlab_project_id = local.gitlab_deploy_token_downgraded[each.key] ? null : try(
    local.resolve_repository[each.key].gitlab_project_id,
    null
  )

  # Azure DevOps native integration
  azure_active_directory_project_id = try(
    local.resolve_repository[each.key].azure_active_directory_project_id,
    null
  )
  azure_active_directory_repository_id = try(
    local.resolve_repository[each.key].azure_active_directory_repository_id,
    null
  )
  azure_bypass_webhook_registration_failure = try(
    local.resolve_repository[each.key].azure_bypass_webhook_registration_failure,
    false
  )

  # PrivateLink endpoint reference
  private_link_endpoint_id = try(
    local.resolve_repository[each.key].private_link_endpoint_key != null ?
    lookup(
      {
        for ple in data.dbtcloud_privatelink_endpoints.all.endpoints :
        ple.id => ple.id
      },
      lookup(local.privatelink_endpoints_map, local.resolve_repository[each.key].private_link_endpoint_key, {}).endpoint_id,
      null
    ) : null,
    null
  )

  pull_request_url_template = try(
    local.resolve_repository[each.key].pull_request_url_template,
    null
  )

  lifecycle {
    prevent_destroy = true
  }
}

#############################################
# Project-Repository Links
# Protection follows repository_protected (same as repository resources)
#############################################

# Link unprotected repositories to projects
resource "dbtcloud_project_repository" "project_repositories" {
  for_each = local.unprotected_repositories_map

  # Reference the correct project resource based on PROJECT protection status
  project_id = (
    contains(keys(local.protected_projects_map), each.key) ?
    dbtcloud_project.protected_projects[each.key].id :
    dbtcloud_project.projects[each.key].id
  )
  repository_id = dbtcloud_repository.repositories[each.key].repository_id

  resource_metadata = {
    source_project_id  = try(each.value.id, null)
    source_id          = try(local.resolve_repository[each.key].id, null)
    source_identity    = "PREP:${each.key}"
    source_key         = each.key
    source_project_key = each.key
    source_name        = each.key
  }
}

# Link protected repositories to projects
resource "dbtcloud_project_repository" "protected_project_repositories" {
  for_each = local.protected_repositories_map

  # Reference the correct project resource based on PROJECT protection status
  project_id = (
    contains(keys(local.protected_projects_map), each.key) ?
    dbtcloud_project.protected_projects[each.key].id :
    dbtcloud_project.projects[each.key].id
  )
  repository_id = dbtcloud_repository.protected_repositories[each.key].repository_id

  resource_metadata = {
    source_project_id  = try(each.value.id, null)
    source_id          = try(local.resolve_repository[each.key].id, null)
    source_identity    = "PREP:${each.key}"
    source_key         = each.key
    source_project_key = each.key
    source_name        = each.key
  }

  lifecycle {
    prevent_destroy = true
  }
}