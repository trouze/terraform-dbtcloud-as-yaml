"""Smoke tests to catch syntax/import regressions early."""


def test_web_module_imports_smoke() -> None:
    """Import critical web modules used by app startup."""
    import importer.web.app  # noqa: F401
    import importer.web.pages.match  # noqa: F401
    import importer.web.pages.deploy  # noqa: F401
    import importer.web.components.match_grid  # noqa: F401
    import importer.web.utils.adoption_yaml_updater  # noqa: F401

