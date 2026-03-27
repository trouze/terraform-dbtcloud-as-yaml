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
  oauth_map = {
    for o in var.oauth_data :
    try(o.key, o.name) => o
  }
}

resource "dbtcloud_oauth_configuration" "oauth_configurations" {
  for_each = local.oauth_map

  name          = each.value.name
  type          = each.value.type
  authorize_url = each.value.authorize_url
  token_url     = each.value.token_url
  redirect_uri  = each.value.redirect_uri
  client_id     = each.value.client_id
  client_secret = try(
    lookup(var.oauth_client_secrets, each.key, null),
    each.value.client_secret
  )
}
