"""Page components for Jobs as Code Generator workflow."""

from importer.web.workflows.jobs_as_code.pages.select import create_jac_select_page
from importer.web.workflows.jobs_as_code.pages.fetch import create_jac_fetch_page
from importer.web.workflows.jobs_as_code.pages.jobs import create_jac_jobs_page
from importer.web.workflows.jobs_as_code.pages.target import create_jac_target_page
from importer.web.workflows.jobs_as_code.pages.mapping import create_jac_mapping_page
from importer.web.workflows.jobs_as_code.pages.config import create_jac_config_page
from importer.web.workflows.jobs_as_code.pages.generate import create_jac_generate_page

__all__ = [
    "create_jac_select_page",
    "create_jac_fetch_page",
    "create_jac_jobs_page",
    "create_jac_target_page",
    "create_jac_mapping_page",
    "create_jac_config_page",
    "create_jac_generate_page",
]
