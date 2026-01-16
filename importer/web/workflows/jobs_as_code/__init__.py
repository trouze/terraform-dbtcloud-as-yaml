"""Jobs as Code Generator workflow module.

This module provides a workflow for generating dbt-jobs-as-code YAML files
from existing dbt Cloud jobs. It supports two sub-workflows:

1. **Adopt**: Take existing jobs under jobs-as-code management by generating
   YAML with `linked_id` fields that reference existing job IDs.

2. **Clone/Migrate**: Create copies of jobs in different environments or 
   accounts by generating new YAML with mapped project/environment IDs.
"""

from importer.web.workflows.jobs_as_code.pages import (
    create_jac_select_page,
    create_jac_fetch_page,
    create_jac_jobs_page,
    create_jac_target_page,
    create_jac_mapping_page,
    create_jac_config_page,
    create_jac_generate_page,
)

__all__ = [
    "create_jac_select_page",
    "create_jac_fetch_page",
    "create_jac_jobs_page",
    "create_jac_target_page",
    "create_jac_mapping_page",
    "create_jac_config_page",
    "create_jac_generate_page",
]
