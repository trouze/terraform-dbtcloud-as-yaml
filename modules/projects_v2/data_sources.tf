#############################################
# Data Sources for LOOKUP Placeholder Resolution
# 
# Resolves LOOKUP: placeholders by querying existing resources in the target account.
# Users must create these resources manually before running Terraform.
#############################################

# Resolve LOOKUP connections by name
# Use global_connections data source and filter by name
data "dbtcloud_global_connections" "all" {}

locals {
  # Map LOOKUP connections to their IDs by filtering global_connections
  lookup_connection_ids = {
    for lookup_key in local.lookup_connections :
    lookup_key => try([
      for conn in data.dbtcloud_global_connections.all.connections :
      conn.id if conn.name == replace(lookup_key, "LOOKUP:", "")
    ][0], null)
  }
}

# Resolve LOOKUP repositories by name (if needed)
# Note: Repositories are project-scoped, so this may need project_id
# For now, we'll handle repository lookups differently in projects.tf

