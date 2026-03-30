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
    args = parser.parse_args()
    run(output_path=args.output, project_ids=args.project_ids, slim=args.slim)
