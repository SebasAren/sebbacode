import pytest

from sebba_code.helpers.git_commit import (
    COMMIT_TYPES,
    ConventionalCommit,
    make_commit,
)


class TestConventionalCommitBuilder:
    def test_basic_commit(self):
        commit = ConventionalCommit().with_type("feat").with_description("add new feature")
        assert commit.build() == "feat: add new feature"

    def test_commit_with_scope(self):
        commit = (
            ConventionalCommit()
            .with_type("fix")
            .with_scope("auth")
            .with_description("resolve login bug")
        )
        assert commit.build() == "fix(auth): resolve login bug"

    def test_commit_with_body(self):
        commit = (
            ConventionalCommit()
            .with_type("feat")
            .with_description("add OAuth support")
            .with_body("Added Google and GitHub OAuth providers")
        )
        result = commit.build()
        assert result == "feat: add OAuth support\n\nAdded Google and GitHub OAuth providers"

    def test_commit_with_footer(self):
        commit = (
            ConventionalCommit()
            .with_type("fix")
            .with_description("resolve issue")
            .with_footer("Closes #123")
        )
        result = commit.build()
        assert "fix: resolve issue" in result
        assert "Closes #123" in result

    def test_commit_with_multiple_footers(self):
        commit = (
            ConventionalCommit()
            .with_type("feat")
            .with_description("major update")
            .with_footer("Closes #123")
            .with_footer("Reviewed-by: Jane")
        )
        result = commit.build()
        lines = result.split("\n")
        # Last two lines should be the footers
        assert "Closes #123" in lines[-2:]
        assert "Reviewed-by: Jane" in lines[-2:]

    def test_breaking_change(self):
        commit = (
            ConventionalCommit()
            .with_type("feat")
            .with_description("change API")
            .with_breaking()
        )
        assert commit.build() == "feat!: change API"

    def test_breaking_change_with_scope(self):
        commit = (
            ConventionalCommit()
            .with_type("fix")
            .with_scope("api")
            .with_description("breakage")
            .with_breaking()
        )
        assert commit.build() == "fix(api)!: breakage"

    def test_full_commit(self):
        commit = (
            ConventionalCommit()
            .with_type("feat")
            .with_scope("auth")
            .with_description("add OAuth2 support")
            .with_body("Added Google and GitHub OAuth providers")
            .with_footer("Closes #123")
            .with_footer("Reviewed-by: Jane")
        )
        result = commit.build()
        assert "feat(auth): add OAuth2 support" in result
        assert "Added Google and GitHub OAuth providers" in result
        assert "Closes #123" in result
        assert "Reviewed-by: Jane" in result

    def test_missing_type_raises(self):
        commit = ConventionalCommit().with_description("test")
        with pytest.raises(ValueError, match="type is required"):
            commit.build()

    def test_missing_description_raises(self):
        commit = ConventionalCommit().with_type("feat")
        with pytest.raises(ValueError, match="description is required"):
            commit.build()

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Unknown commit type 'yolo'"):
            ConventionalCommit().with_type("yolo")


class TestMakeCommit:
    def test_basic_commit(self):
        result = make_commit("feat", "add feature")
        assert result == "feat: add feature"

    def test_with_scope(self):
        result = make_commit("fix", "resolve bug", scope="ui")
        assert result == "fix(ui): resolve bug"

    def test_with_body(self):
        result = make_commit("feat", "add thing", body="Detailed explanation")
        assert "feat: add thing" in result
        assert "Detailed explanation" in result

    def test_with_footers(self):
        result = make_commit(
            "fix", "issue", footers=["Closes #456", "See-also: #789"]
        )
        assert "fix: issue" in result
        assert "Closes #456" in result
        assert "See-also: #789" in result

    def test_breaking_change(self):
        result = make_commit("feat", "api change", breaking=True)
        assert result == "feat!: api change"

    def test_empty_type_raises(self):
        with pytest.raises(ValueError, match="Unknown commit type"):
            make_commit("", "description")

    def test_empty_description_raises(self):
        with pytest.raises(ValueError, match="description is required"):
            make_commit("feat", "")

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Unknown commit type 'invalid'"):
            make_commit("invalid", "description")


class TestCommitTypes:
    def test_commit_types_defined(self):
        assert "feat" in COMMIT_TYPES
        assert "fix" in COMMIT_TYPES
        assert "docs" in COMMIT_TYPES
        assert "test" in COMMIT_TYPES
        assert "chore" in COMMIT_TYPES

    def test_all_standard_types_present(self):
        expected = (
            "feat",
            "fix",
            "docs",
            "style",
            "refactor",
            "perf",
            "test",
            "build",
            "ci",
            "chore",
            "revert",
        )
        assert COMMIT_TYPES == expected
