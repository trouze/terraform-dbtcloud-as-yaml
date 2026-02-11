"""Unit tests for adoption dependency resolution (criteria 24-26).

Tests:
- UT-AD-08: JOB → [ENV, PRJ] parent chain
- UT-AD-24: All child types resolve correct parent chains
- find_unadopted_parents: returns rows for unadopted parents
- get_project_children: groups children by type for "Select Whole Project"
"""

import pytest

from importer.web.utils.adoption_dependencies import (
    find_unadopted_parents,
    get_parent_chain,
    get_project_children,
)


# =============================================================================
# UT-AD-08: Dependency resolution for JOB → ENV → PRJ chain
# =============================================================================


class TestGetParentChain:
    """Test get_parent_chain() returns correct parent types."""

    def test_job_parent_chain(self):
        """UT-AD-08: JOB → [ENV, PRJ]."""
        chain = get_parent_chain("JOB")
        assert chain == ["ENV", "PRJ"]

    def test_env_parent_chain(self):
        """ENV → [PRJ]."""
        chain = get_parent_chain("ENV")
        assert chain == ["PRJ"]

    def test_prj_parent_chain(self):
        """PRJ has no adoptable parents (ACC is excluded)."""
        chain = get_parent_chain("PRJ")
        assert chain == []

    def test_crd_parent_chain(self):
        """CRD → [ENV, PRJ]."""
        chain = get_parent_chain("CRD")
        assert chain == ["ENV", "PRJ"]

    def test_var_parent_chain(self):
        """VAR → [PRJ]."""
        chain = get_parent_chain("VAR")
        assert chain == ["PRJ"]

    def test_extattr_parent_chain(self):
        """EXTATTR → [PRJ]."""
        chain = get_parent_chain("EXTATTR")
        assert chain == ["PRJ"]

    def test_rep_parent_chain(self):
        """REP has no adoptable parents (ACC is excluded)."""
        chain = get_parent_chain("REP")
        assert chain == []

    def test_con_parent_chain(self):
        """CON → [ENV, PRJ] (connection used by environments)."""
        chain = get_parent_chain("CON")
        assert chain == ["ENV", "PRJ"]

    def test_unknown_type_returns_empty(self):
        """Unknown type returns empty chain."""
        chain = get_parent_chain("UNKNOWN")
        assert chain == []

    def test_acc_returns_empty(self):
        """ACC (account) returns empty chain."""
        chain = get_parent_chain("ACC")
        assert chain == []


# =============================================================================
# UT-AD-24: All child types resolve correct parent chains
# =============================================================================


class TestAllChildTypeParentChains:
    """UT-AD-24: Verify parent chain for all child resource types."""

    @pytest.mark.parametrize(
        "child_type, expected_chain",
        [
            ("JOB", ["ENV", "PRJ"]),
            ("CRD", ["ENV", "PRJ"]),
            ("ENV", ["PRJ"]),
            ("VAR", ["PRJ"]),
            ("EXTATTR", ["PRJ"]),
            ("PRJ", []),
            ("REP", []),
            ("CON", ["ENV", "PRJ"]),
            ("TOK", []),
            ("GRP", []),
            ("NOT", []),
            ("WEB", []),
            ("PLE", []),
        ],
    )
    def test_parent_chain(self, child_type, expected_chain):
        """Each child type resolves to the correct parent chain."""
        assert get_parent_chain(child_type) == expected_chain


# =============================================================================
# find_unadopted_parents: locate parent rows needing adoption
# =============================================================================


def _make_row(source_type, source_name, project_name, action="ignore"):
    """Helper to build a minimal grid row."""
    return {
        "source_type": source_type,
        "source_name": source_name,
        "source_key": f"{source_type}:{source_name}",
        "project_name": project_name,
        "action": action,
        "target_id": "100",
    }


class TestFindUnadoptedParents:
    """Tests for find_unadopted_parents()."""

    def test_job_with_unadopted_env_and_project(self):
        """Adopting a job without env/project returns both as unadopted."""
        prj = _make_row("PRJ", "analytics", "analytics", action="ignore")
        env = _make_row("ENV", "Production", "analytics", action="ignore")
        job = _make_row("JOB", "nightly_build", "analytics", action="adopt")

        unadopted = find_unadopted_parents(job, [prj, env, job])
        unadopted_types = [r["source_type"] for r in unadopted]
        assert "ENV" in unadopted_types
        assert "PRJ" in unadopted_types

    def test_job_with_adopted_env_returns_only_project(self):
        """Adopting a job when env is already adopted returns only project."""
        prj = _make_row("PRJ", "analytics", "analytics", action="ignore")
        env = _make_row("ENV", "Production", "analytics", action="adopt")
        job = _make_row("JOB", "nightly_build", "analytics", action="adopt")

        unadopted = find_unadopted_parents(job, [prj, env, job])
        unadopted_types = [r["source_type"] for r in unadopted]
        assert "PRJ" in unadopted_types
        assert "ENV" not in unadopted_types

    def test_job_with_all_parents_adopted(self):
        """No unadopted parents when all are already adopted."""
        prj = _make_row("PRJ", "analytics", "analytics", action="adopt")
        env = _make_row("ENV", "Production", "analytics", action="adopt")
        job = _make_row("JOB", "nightly_build", "analytics", action="adopt")

        unadopted = find_unadopted_parents(job, [prj, env, job])
        assert len(unadopted) == 0

    def test_job_with_matched_parent_not_flagged(self):
        """Parents with action=match are not flagged as unadopted."""
        prj = _make_row("PRJ", "analytics", "analytics", action="match")
        env = _make_row("ENV", "Production", "analytics", action="match")
        job = _make_row("JOB", "nightly_build", "analytics", action="adopt")

        unadopted = find_unadopted_parents(job, [prj, env, job])
        assert len(unadopted) == 0

    def test_env_with_unadopted_project(self):
        """Adopting an env returns only the project as unadopted."""
        prj = _make_row("PRJ", "analytics", "analytics", action="ignore")
        env = _make_row("ENV", "Production", "analytics", action="adopt")

        unadopted = find_unadopted_parents(env, [prj, env])
        assert len(unadopted) == 1
        assert unadopted[0]["source_type"] == "PRJ"

    def test_project_has_no_unadopted_parents(self):
        """Projects have no adoptable parents."""
        prj = _make_row("PRJ", "analytics", "analytics", action="adopt")

        unadopted = find_unadopted_parents(prj, [prj])
        assert len(unadopted) == 0


# =============================================================================
# get_project_children: group children by type for "Select Whole Project"
# =============================================================================


class TestGetProjectChildren:
    """Tests for get_project_children()."""

    def test_basic_project_children(self):
        """Project with envs, jobs, and vars returns all grouped by type."""
        prj = _make_row("PRJ", "analytics", "analytics")
        env1 = _make_row("ENV", "Production", "analytics")
        env2 = _make_row("ENV", "Staging", "analytics")
        job = _make_row("JOB", "nightly_build", "analytics")
        var = _make_row("VAR", "DBT_TOKEN", "analytics")

        children = get_project_children(prj, [prj, env1, env2, job, var])
        assert len(children["ENV"]) == 2
        assert len(children["JOB"]) == 1
        assert len(children["VAR"]) == 1
        assert "PRJ" not in children

    def test_project_children_excludes_other_project_resources(self):
        """Children from a different project are not included."""
        prj1 = _make_row("PRJ", "analytics", "analytics")
        prj2 = _make_row("PRJ", "marketing", "marketing")
        env1 = _make_row("ENV", "Production", "analytics")
        env2 = _make_row("ENV", "Production", "marketing")

        children = get_project_children(prj1, [prj1, prj2, env1, env2])
        assert len(children.get("ENV", [])) == 1
        assert children["ENV"][0]["source_name"] == "Production"
        assert children["ENV"][0]["project_name"] == "analytics"

    def test_empty_project(self):
        """Project with no children returns empty dict."""
        prj = _make_row("PRJ", "analytics", "analytics")

        children = get_project_children(prj, [prj])
        assert children == {}

    def test_project_children_includes_all_depth_levels(self):
        """Children at all depth levels are included."""
        prj = _make_row("PRJ", "analytics", "analytics")
        env = _make_row("ENV", "Production", "analytics")
        job = _make_row("JOB", "nightly_build", "analytics")
        crd = _make_row("CRD", "snowflake_cred", "analytics")
        var = _make_row("VAR", "DBT_TOKEN", "analytics")
        extattr = _make_row("EXTATTR", "custom_attrs", "analytics")

        children = get_project_children(prj, [prj, env, job, crd, var, extattr])
        assert "ENV" in children
        assert "JOB" in children
        assert "CRD" in children
        assert "VAR" in children
        assert "EXTATTR" in children
