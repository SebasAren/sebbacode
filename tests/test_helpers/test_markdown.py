from sebba_code.helpers.markdown import append_to_section, replace_section, summarise_file


class TestAppendToSection:
    def test_append_to_existing_section(self):
        content = "## Todos\n- [ ] First\n\n## Other\nStuff"
        result = append_to_section(content, "## Todos", "- [ ] Second")
        assert "- [ ] First" in result
        assert "- [ ] Second" in result
        assert result.index("- [ ] Second") < result.index("## Other")

    def test_append_to_nonexistent_section(self):
        content = "## Existing\nContent"
        result = append_to_section(content, "## New Section", "- item")
        assert "## New Section" in result
        assert "- item" in result


class TestReplaceSection:
    def test_replace_existing_section(self):
        content = "## Target Files\n- old.ts\n\n## Other\nStuff"
        result = replace_section(content, "## Target Files", "- new.ts")
        assert "- new.ts" in result
        assert "- old.ts" not in result
        assert "## Other" in result

    def test_replace_nonexistent_section(self):
        content = "## Existing\nContent"
        result = replace_section(content, "## New Section", "New body")
        assert "## New Section" in result
        assert "New body" in result


class TestSummariseFile:
    def test_extracts_declarations(self):
        content = (
            "import { foo } from 'bar'\n"
            "\n"
            "export function doStuff() {\n"
            "  return 42\n"
            "}\n"
            "\n"
            "const CONFIG = {}\n"
        )
        result = summarise_file("test.ts", content)
        assert "test.ts" in result
        assert "export function doStuff" in result
        assert "const CONFIG" in result
