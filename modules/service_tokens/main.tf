terraform {
  required_version = ">= 1.7"
  required_providers {
    dbtcloud = {
      source  = "dbt-labs/dbtcloud"
      version = "~> 1.8"
    }
  }
}

locals {
  tokens_map = {
    for t in var.service_tokens_data :
    try(t.key, t.name) => t
  }

  # COMPAT(v1-schema): prefer service_token_permissions[] when non-empty, else legacy permissions[]
  service_tokens_permissions_by_key = {
    for k, t in local.tokens_map :
    k => (
      length(try(t.service_token_permissions, [])) > 0 ? try(t.service_token_permissions, []) :
      try(t.permissions, [])
    )
  }

  protected_tokens_map = {
    for k, t in local.tokens_map :
    k => t
    if try(t.protected, false) == true
  }

  unprotected_tokens_map = {
    for k, t in local.tokens_map :
    k => t
    if try(t.protected, false) != true
  }

  # v2 set resource_metadata on dbtcloud_service_token; stock provider has no such argument.
  service_tokens_provenance = {
    for key, t in local.tokens_map :
    key => {
      source_key      = key
      source_name     = t.name
      source_identity = "TOK:${key}"
      source_id       = try(t.id, null)
      protected       = try(t.protected, false)
    }
  }
}

resource "dbtcloud_service_token" "service_tokens" {
  for_each = local.unprotected_tokens_map

  name  = each.value.name
  state = try(each.value.state, 1)

  dynamic "service_token_permissions" {
    for_each = var.skip_global_project_permissions ? [] : tolist(try(local.service_tokens_permissions_by_key[each.key], []))
    content {
      permission_set = service_token_permissions.value.permission_set
      all_projects = try(
        service_token_permissions.value.all_projects,
        try(service_token_permissions.value.project_key, null) == null &&
        try(service_token_permissions.value.project_id, null) == null,
      )
      project_id = (
        try(service_token_permissions.value.project_key, null) != null
        ? try(var.project_ids[service_token_permissions.value.project_key], null)
        : try(service_token_permissions.value.project_id, null)
      )
      writable_environment_categories = try(service_token_permissions.value.writable_environment_categories, [])
    }
  }

  dynamic "service_token_permissions" {
    for_each = var.skip_global_project_permissions ? tolist(try(local.service_tokens_permissions_by_key[each.key], [])) : []
    content {
      permission_set                  = service_token_permissions.value.permission_set
      all_projects                    = true
      project_id                      = null
      writable_environment_categories = try(service_token_permissions.value.writable_environment_categories, [])
    }
  }
}

resource "dbtcloud_service_token" "protected_service_tokens" {
  for_each = local.protected_tokens_map

  name  = each.value.name
  state = try(each.value.state, 1)

  dynamic "service_token_permissions" {
    for_each = var.skip_global_project_permissions ? [] : tolist(try(local.service_tokens_permissions_by_key[each.key], []))
    content {
      permission_set = service_token_permissions.value.permission_set
      all_projects = try(
        service_token_permissions.value.all_projects,
        try(service_token_permissions.value.project_key, null) == null &&
        try(service_token_permissions.value.project_id, null) == null,
      )
      project_id = (
        try(service_token_permissions.value.project_key, null) != null
        ? try(var.project_ids[service_token_permissions.value.project_key], null)
        : try(service_token_permissions.value.project_id, null)
      )
      writable_environment_categories = try(service_token_permissions.value.writable_environment_categories, [])
    }
  }

  dynamic "service_token_permissions" {
    for_each = var.skip_global_project_permissions ? tolist(try(local.service_tokens_permissions_by_key[each.key], [])) : []
    content {
      permission_set                  = service_token_permissions.value.permission_set
      all_projects                    = true
      project_id                      = null
      writable_environment_categories = try(service_token_permissions.value.writable_environment_categories, [])
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}
