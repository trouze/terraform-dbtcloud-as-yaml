# Contributing to terraform-dbtcloud-as-yaml

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

All contributors must follow the [dbt Community Code of Conduct](https://docs.getdbt.com/community/resources/code-of-conduct). See also [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) in this repository.

## How to Contribute

### Reporting security issues

Do not open a public issue. Follow [SECURITY.md](SECURITY.md).

### Reporting Bugs

If you find a bug, please create an issue with:

- Clear description of the bug
- Steps to reproduce
- Expected vs. actual behavior
- Your environment (Terraform version, OS, etc.)
- Any relevant configuration snippets

### Suggesting Features

Feature requests are welcome! Please include:

- Description of the feature
- Use case and why it's needed
- Any examples or mockups

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/your-username/terraform-dbtcloud-as-yaml.git
   cd terraform-dbtcloud-as-yaml
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the existing code style
   - Add comments for complex logic
   - Update documentation as needed

3. **Test your changes**

   Pre-commit hooks run automatically on `git commit` (fmt, validate, lint, docs) and pre-push hooks run on `git push` (terraform test + YAML schema self-tests). To run all hooks manually without committing:

   ```bash
   pre-commit run --all-files
   ```

   To check CI parity before opening a PR:

   ```bash
   act
   act -j <jobname>
   ```

4. **Commit with clear messages**
   ```bash
   git commit -m "Add: clear description of changes"
   ```

5. **Push and open a PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Terraform >= 1.7 (use [tfenv](https://github.com/tfutils/tfenv) or [asdf](https://asdf-vm.com/) — `.terraform-version` is provided)
- [tflint](https://github.com/terraform-linters/tflint)
- Git
- [pre-commit](https://pre-commit.com/#install)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker (required by `act`)
- [act](https://github.com/nektos/act)
- [terraform-docs](https://terraform-docs.io/user-guide/installation/) v0.20.0

### Local Development

```bash
git clone https://github.com/your-username/terraform-dbtcloud-as-yaml.git
cd terraform-dbtcloud-as-yaml

terraform init -backend=false
```

One-time setup after cloning:

```bash
pre-commit install --hook-type pre-commit --hook-type pre-push
```

### Developer workflow

| Action | What runs |
|---|---|
| `git commit` | fmt, validate, lint, docs, schema-drift (pre-commit hooks) |
| `git push` | `terraform test` (root + all 5 modules), YAML schema self-tests (pre-push hooks) |
| `pre-commit run --all-files` | All pre-commit hooks on every file |
| `bash scripts/gen-docs.sh` | Regenerate terraform-docs manually |
| `act` | Full CI parity — all jobs |
| `act -j <jobname>` | Single CI job (`validate`, `module-tests`, `docs`, `schema-drift`, `yaml-validate`, `mkdocs-build`) |
| `cd test && RUN_INTEGRATION_TESTS=1 DBT_CLOUD_ACCOUNT_ID=... DBT_CLOUD_TOKEN=... go test -v -timeout 30m -run Integration ./...` | Integration tests (requires dbt Cloud credentials) |

## Testing

Before submitting a PR, verify that all hooks pass and CI is green locally:

```bash
pre-commit run --all-files
act
```

For integration tests (requires dbt Cloud credentials):

```bash
cd test && RUN_INTEGRATION_TESTS=1 DBT_CLOUD_ACCOUNT_ID=<id> DBT_CLOUD_TOKEN=<token> \
  go test -v -timeout 30m -run Integration ./...
```

You can also trigger the `integration.yml` workflow from the GitHub Actions UI.

## Documentation

- Update `README.md` for user-facing changes
- Update module `variables.tf` with clear descriptions
- Add comments to complex logic
- Include examples for new features

## Release Process

Maintainers will:

1. Update version numbers following [Semantic Versioning](https://semver.org/)
2. Update `CHANGELOG.md`
3. Create a GitHub release with release notes
4. Tag the commit with version number

## Questions?

- Check existing [GitHub issues](https://github.com/dbt-labs/terraform-dbtcloud-as-yaml/issues)
- Review the [README](../README.md) and [documentation](../README.md#documentation)
- Open a new discussion in GitHub Discussions

## License

By contributing, you agree that your contributions will be licensed under the project's [Apache License 2.0](LICENSE).

Thank you for contributing!
