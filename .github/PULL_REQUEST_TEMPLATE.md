## Summary

<!-- What does this PR do? One paragraph or bullet list. -->

## Type of change

- [ ] Bug fix
- [ ] New feature / resource support
- [ ] Refactoring (no behavior change)
- [ ] Documentation
- [ ] CI / tooling

## Schema changes

- [ ] This PR modifies the YAML schema — `schemas/v1.json` and `docs/configuration/yaml-schema.md` updated
- [ ] No schema changes

## Checklist

- [ ] pre-commit hooks pass (`git commit` triggers fmt, validate, lint, docs)
- [ ] pre-push hooks pass (`git push` triggers terraform test + YAML schema self-tests)
- [ ] `act` passes locally (or `act -j <job>` for the jobs you touched)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] Docs updated if behavior changed
