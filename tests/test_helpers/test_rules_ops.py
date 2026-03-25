from sebba_code.helpers.rules_ops import parse_path_frontmatter, strip_frontmatter


class TestParsePathFrontmatter:
    def test_with_paths(self):
        content = '---\npaths:\n  - "**/*.test.ts"\n---\n# Rules'
        result = parse_path_frontmatter(content)
        assert result == ["**/*.test.ts"]

    def test_without_frontmatter(self):
        content = "# Rules\nNo frontmatter here"
        result = parse_path_frontmatter(content)
        assert result is None

    def test_without_paths_key(self):
        content = "---\ntitle: test\n---\n# Rules"
        result = parse_path_frontmatter(content)
        assert result is None


class TestStripFrontmatter:
    def test_strips_frontmatter(self):
        content = "---\npaths:\n  - foo\n---\n# Rules\nContent"
        result = strip_frontmatter(content)
        assert result == "# Rules\nContent"

    def test_no_frontmatter(self):
        content = "# Rules\nContent"
        result = strip_frontmatter(content)
        assert result == "# Rules\nContent"
