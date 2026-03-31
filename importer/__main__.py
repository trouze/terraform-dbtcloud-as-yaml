import argparse
from pathlib import Path
from importer.bootstrap import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch dbt Cloud account state and write dbt-config.yml"
    )
    parser.add_argument(
        "--output", type=Path, default=None, metavar="PATH",
        help="Output path for dbt-config.yml (default: ./dbt-config.yml)",
    )
    parser.add_argument(
        "--project-id", type=int, action="append", dest="project_ids", metavar="ID",
        help="Scope import to a project ID (repeatable: --project-id 123 --project-id 456)",
    )
    parser.add_argument(
        "--slim", action="store_true", default=False,
        help="Skip account-level globals (groups, service tokens, notifications, etc.). "
             "Connections and repositories are always fetched.",
    )
    parser.add_argument(
        "--import-blocks", action="store_true", default=False, dest="import_blocks",
        help="Generate imports.tf with Terraform import {} blocks (requires Terraform >= 1.5). "
             "Safe to delete after first 'terraform apply'.",
    )
    args = parser.parse_args()
    run(output_path=args.output, project_ids=args.project_ids, slim=args.slim, import_blocks=args.import_blocks)
