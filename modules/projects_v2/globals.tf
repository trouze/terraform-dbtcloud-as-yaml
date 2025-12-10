#############################################
# Global Resources
# 
# Creates account-level resources that can be referenced by projects:
# - Connections (global connections)
# - Service Tokens
# - Groups
# - Notifications (created but job associations handled later)
#
# Note: Repositories are project-scoped and created per-project.
# Note: PrivateLink endpoints are read-only (must exist in account).
#############################################

# Global Connections
# Note: Provider-specific configuration blocks (snowflake, databricks, etc.) 
# must be manually added as they're not available from API exports
resource "dbtcloud_global_connection" "connections" {
  for_each = {
    for conn in var.globals.connections :
    conn.key => conn
  }

  name = each.value.name

  # PrivateLink endpoint reference (if specified)
  private_link_endpoint_id = try(
    lookup(local.privatelink_endpoints_map, each.value.private_link_endpoint_key, null) != null ?
    data.dbtcloud_privatelink_endpoints.all.endpoints[
      index(
        [for ep in data.dbtcloud_privatelink_endpoints.all.endpoints : ep.id],
        lookup(local.privatelink_endpoints_map, each.value.private_link_endpoint_key).endpoint_id
      )
    ].id : null,
    null
  )

  # Provider-specific blocks must be manually configured
  # The importer exports connection metadata but not provider config for security
  # Users must add these blocks manually based on their connection details
  # Example:
  # snowflake = {
  #   account   = "..."
  #   database  = "..."
  #   warehouse = "..."
  # }
}

# Service Tokens
resource "dbtcloud_service_token" "service_tokens" {
  for_each = {
    for token in var.globals.service_tokens :
    token.key => token
  }

  name  = each.value.name
  state = try(each.value.state, 1)

  dynamic "service_token_permissions" {
    for_each = try(each.value.service_token_permissions, [])
    content {
      permission_set = service_token_permissions.value.permission_set
      all_projects   = try(service_token_permissions.value.all_projects, false)
      project_id     = try(service_token_permissions.value.project_id, null)
      writable_environment_categories = try(
        service_token_permissions.value.writable_environment_categories,
        []
      )
    }
  }
}

# Groups
resource "dbtcloud_group" "groups" {
  for_each = {
    for group in var.globals.groups :
    group.key => group
  }

  name              = each.value.name
  assign_by_default = try(each.value.assign_by_default, false)
  sso_mapping_groups = try(each.value.sso_mapping_groups, [])

  dynamic "group_permissions" {
    for_each = try(each.value.group_permissions, [])
    content {
      permission_set = group_permissions.value.permission_set
      all_projects   = try(group_permissions.value.all_projects, false)
      project_id     = try(group_permissions.value.project_id, null)
      writable_environment_categories = try(
        group_permissions.value.writable_environment_categories,
        []
      )
    }
  }
}

# Notifications
# Note: Job associations (on_success, on_failure, etc.) are handled later
# after jobs are created, via separate resources or updates
resource "dbtcloud_notification" "notifications" {
  for_each = {
    for notif in var.globals.notifications :
    notif.key => notif
  }

  user_id          = each.value.user_id
  notification_type = try(each.value.notification_type, 1)
  state            = try(each.value.state, 1)

  # Job associations - these will be empty initially and updated after jobs are created
  # For now, we'll handle this via a separate update mechanism or locals
  on_success = try(each.value.on_success, [])
  on_failure = try(each.value.on_failure, [])
  on_warning = try(each.value.on_warning, [])
  on_cancel  = try(each.value.on_cancel, [])

  external_email     = try(each.value.external_email, null)
  slack_channel_id   = try(each.value.slack_channel_id, null)
  slack_channel_name = try(each.value.slack_channel_name, null)
}

# Data source for PrivateLink endpoints (read-only)
data "dbtcloud_privatelink_endpoints" "all" {}

