"""
Bootstrap entry point: fetch live dbt Cloud account state → dbt-config.yml

Usage (via install.sh or directly):
    DBT_SOURCE_HOST_URL=... DBT_SOURCE_ACCOUNT_ID=... DBT_SOURCE_API_TOKEN=... \
        python -m importer
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

# Account-level globals that are safe to skip when scoping to specific projects.
# "connections" and "repositories" are always fetched — they are cross-referenced
# during project normalization.
ACCOUNT_LEVEL_GLOBALS = {
    "service_tokens",
    "groups",
    "notifications",
    "webhooks",
    "privatelink_endpoints",
    "account_features",
    "ip_restrictions",
    "oauth_configurations",
    "user_groups",
}


def run(
    output_path: Path | None = None,
    project_ids: Optional[List[int]] = None,
    slim: bool = False,
) -> None:
    from importer.config import Settings
    from importer.client import DbtCloudClient
    from importer.fetcher import fetch_account_snapshot
    from importer.normalizer import MappingConfig, NormalizationContext
    from importer.normalizer.core import normalize_snapshot
    import yaml

    output_path = output_path or Path.cwd() / "dbt-config.yml"
    mapping_path = Path(__file__).parent.parent / "importer_mapping.yml"

    try:
        settings = Settings.from_env()
        client = DbtCloudClient(settings)
        print("  Fetching account state...")
        snapshot = fetch_account_snapshot(
            client,
            project_ids=set(project_ids) if project_ids else None,
            skip_globals=ACCOUNT_LEVEL_GLOBALS if slim else None,
        )
        client.close()

        config = MappingConfig.load(mapping_path)
        if project_ids:
            config.scope["mode"] = "specific_projects"
            config.scope["project_ids"] = list(project_ids)
        context = NormalizationContext(config)
        normalized = normalize_snapshot(snapshot, config, context)

        yaml_output = yaml.dump(
            normalized,
            default_flow_style=False,
            sort_keys=config.should_sort_keys(),
            indent=config.get_yaml_indent(),
            width=config.get_yaml_line_length(),
            allow_unicode=True,
        )
        output_path.write_text(yaml_output, encoding="utf-8")

        print(f"  \u2713  {output_path} written")

        if context.placeholders:
            print(f"  \u26a0  {len(context.placeholders)} LOOKUP placeholders need manual resolution")
        if context.exclusions:
            print(f"  \u2139  {len(context.exclusions)} resources excluded \u2014 review dbt-config.yml")

    except Exception as e:
        print(f"  \u2717  Import failed: {e}", file=sys.stderr)
        sys.exit(1)
