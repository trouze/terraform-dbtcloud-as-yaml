#!/usr/bin/env bash
# install.sh — bootstrap a dbt Cloud Terraform starter from terraform-dbtcloud-yaml
#
# Usage:
#   curl -fsSL https://github.com/trouze/terraform-dbtcloud-yaml/releases/latest/download/install.sh | bash
#   curl -fsSL https://github.com/trouze/terraform-dbtcloud-yaml/releases/latest/download/install.sh | bash -s -- my-project
#
set -euo pipefail

TARGET=${1:-my-dbt-platform}
REPO="trouze/terraform-dbtcloud-yaml"
RELEASE_URL="${RELEASE_URL:-https://github.com/$REPO/releases/latest/download/starter.tar.gz}"

# Resolve the importer directory: prefer a copy alongside this script (local dev),
# fall back to fetching it from the repo via git sparse-checkout.
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-}")" &>/dev/null && pwd || true)"
if [[ -d "$_SCRIPT_DIR/importer" ]]; then
  IMPORTER_DIR="$_SCRIPT_DIR/importer"
  IMPORTER_PYTHONPATH="$_SCRIPT_DIR"
else
  # curl | bash path — fetch importer from the repo into a temp dir
  _IMPORTER_TMP="$(mktemp -d)"
  trap 'rm -rf "$_IMPORTER_TMP"' EXIT
  git clone --no-checkout --depth=1 "https://github.com/$REPO" "$_IMPORTER_TMP/repo" --quiet
  git -C "$_IMPORTER_TMP/repo" sparse-checkout set importer
  git -C "$_IMPORTER_TMP/repo" checkout --quiet
  IMPORTER_DIR="$_IMPORTER_TMP/repo/importer"
  IMPORTER_PYTHONPATH="$_IMPORTER_TMP/repo"
fi

echo "Setting up dbt Platform Terraform starter in ./$TARGET ..."
echo ""

if [[ -e "$TARGET" ]]; then
  echo "Error: '$TARGET' already exists. Pass a different directory name:" >&2
  echo "  bash <(curl -fsSL ...) my-other-name" >&2
  exit 1
fi

mkdir -p "$TARGET"

# Strategy 1: curl + tar (no extra tools required — fastest)
if command -v curl &>/dev/null && command -v tar &>/dev/null; then
  if curl -fsSL "$RELEASE_URL" | tar -xz --strip-components=1 -C "$TARGET" 2>/dev/null; then
    :
  else
    # Fall through to strategy 2 if the release asset doesn't exist yet
    rmdir "$TARGET" 2>/dev/null || true
    _fallback=1
  fi
fi

# Strategy 2: degit (needs npm/npx)
if [[ ${_fallback:-0} -eq 1 ]] || [[ ! -d "$TARGET" ]]; then
  if command -v npx &>/dev/null; then
    echo "(release asset not found, falling back to degit)"
    npx --yes degit "$REPO/examples/basic" "$TARGET"
  else
    # Strategy 3: git sparse-checkout
    echo "(falling back to git sparse-checkout)"
    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT
    git clone --no-checkout --depth=1 "https://github.com/$REPO" "$TMP/repo" --quiet
    git -C "$TMP/repo" sparse-checkout set examples/basic
    git -C "$TMP/repo" checkout --quiet
    cp -r "$TMP/repo/examples/basic/." "$TARGET/"
  fi
fi

echo "Done. Starter created in ./$TARGET"
echo ""

# ── Phase 2: Existing account import ─────────────────────────────────────────
printf "Do you have an existing dbt Cloud account to import? [y/N] "
read -r IMPORT_ACCOUNT

if [[ "$IMPORT_ACCOUNT" =~ ^[Yy]$ ]]; then
    if ! command -v python3 &>/dev/null; then
        echo "  python3 is required for the import. Install it and re-run." >&2
        exit 1
    fi

    # Virtualenv + install importer package
    python3 -m venv "$TARGET/.venv"
    # shellcheck disable=SC1091
    source "$TARGET/.venv/bin/activate"
    pip install -q "$IMPORTER_DIR"

    printf "  dbt Cloud host URL [https://<your-account>.<region>.dbt.com]: "
    read -r DBT_SOURCE_HOST_URL
    DBT_SOURCE_HOST_URL="${DBT_SOURCE_HOST_URL:-https://cloud.getdbt.com}"

    printf "  Account ID: "
    read -r DBT_SOURCE_ACCOUNT_ID

    printf "  API token: "
    read -rs DBT_SOURCE_API_TOKEN
    echo

    printf "  Project ID(s) to import, comma-separated [leave blank for all]: "
    read -r PROJECT_IDS_INPUT

    IMPORTER_FLAGS=()
    if [[ -n "$PROJECT_IDS_INPUT" ]]; then
        IFS=',' read -ra _ids <<< "$PROJECT_IDS_INPUT"
        for _id in "${_ids[@]}"; do
            _id="${_id// /}"  # trim spaces
            [[ -n "$_id" ]] && IMPORTER_FLAGS+=(--project-id "$_id")
        done
    fi

    printf "  Generate imports.tf for Terraform state import? [y/N] "
    read -r GENERATE_IMPORTS
    if [[ "$GENERATE_IMPORTS" =~ ^[Yy]$ ]]; then
        IMPORTER_FLAGS+=(--import-blocks)
    fi

    export DBT_SOURCE_HOST_URL DBT_SOURCE_ACCOUNT_ID DBT_SOURCE_API_TOKEN
    (cd "$TARGET" && dbtcloud-import init "${IMPORTER_FLAGS[@]}")

    # Pre-populate .env so Terraform credentials don't need to be re-entered
    if [[ -f "$TARGET/.env.example" ]]; then
        python3 -c "
import sys, pathlib
target, acct, token, host = sys.argv[1:]
txt = pathlib.Path(f'{target}/.env.example').read_text()
txt = txt.replace('YOUR_ACCOUNT_ID', acct).replace('YOUR_API_TOKEN', token).replace('YOUR_HOST_URL', host)
pathlib.Path(f'{target}/.env').write_text(txt)
" "$TARGET" "$DBT_SOURCE_ACCOUNT_ID" "$DBT_SOURCE_API_TOKEN" "$DBT_SOURCE_HOST_URL"
        echo "  \u2713  $TARGET/.env pre-filled with your dbt Cloud credentials"
    fi
fi

# ── Phase 3: Next steps ───────────────────────────────────────────────────────
echo ""
echo "Next steps:"
echo "  1.  cd $TARGET"
if [[ "${IMPORT_ACCOUNT:-N}" =~ ^[Yy]$ ]]; then
    echo "  2.  Review .env — your dbt Cloud credentials are pre-filled;"
    echo "      add warehouse credentials (TF_VAR_environment_credentials, etc.)"
    if [[ "${GENERATE_IMPORTS:-N}" =~ ^[Yy]$ ]]; then
        echo "  3.  source .env && terraform init && terraform apply  # imports existing state"
        echo "      After a successful apply, delete imports.tf — resources are now in state."
    fi
else
    echo "  2.  cp .env.example .env"
    echo "      # fill in TF_VAR_dbt_account_id, TF_VAR_dbt_token, and warehouse credentials"
fi
echo "  3.  source .env && terraform init && terraform apply"
echo ""
echo "Full walkthrough: https://github.com/$REPO/blob/main/examples/basic/README.md"
