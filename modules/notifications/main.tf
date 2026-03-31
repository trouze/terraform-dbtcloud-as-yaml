terraform {
  required_version = ">= 1.7"
  required_providers {
    dbtcloud = {
      source  = "dbt-labs/dbtcloud"
      version = "~> 1.9"
    }
  }
}

locals {
  notifications_map = {
    for n in var.notifications_data :
    n.key => n
  }

  _type_map = {
    "slack"     = 2
    "email"     = 4
    "pagerduty" = 3
    "webhook"   = 1
  }
}

resource "dbtcloud_notification" "notifications" {
  for_each = local.notifications_map

  user_id           = try(each.value.target.user_id, each.value.user_id, null)
  # Support both new schema (type string) and importer flat format (notification_type int)
  notification_type = try(local._type_map[each.value.type], each.value.notification_type)

  slack_channel_id   = try(each.value.target.channel_id, each.value.slack_channel_id, null)
  slack_channel_name = try(each.value.target.channel_name, each.value.target.channel, each.value.slack_channel_name, null)
  external_email     = try(each.value.target.email, each.value.external_email, null)

  on_cancel  = try(each.value.on_cancel, [])
  on_failure = try(each.value.on_failure, [])
  on_success = try(each.value.on_success, [])
  on_warning = try(each.value.on_warning, [])
}
