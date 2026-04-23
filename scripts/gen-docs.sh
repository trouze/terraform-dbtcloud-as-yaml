#!/usr/bin/env bash
set -euo pipefail
terraform-docs -c .terraform-docs.yml .
for dir in modules/*/; do
  module=$(basename "$dir")
  terraform-docs markdown table \
    --output-file "../../docs/reference/module-${module}.md" \
    --output-mode replace \
    "$dir"
done
