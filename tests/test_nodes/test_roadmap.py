from sebba_code.nodes.roadmap import has_todo, is_first_todo, read_roadmap


class TestReadRoadmap:
    def test_reads_roadmap(self, tmp_agent_dir):
        result = read_roadmap({})
        assert result["roadmap"]
        assert result["current_todo"] is not None
        assert result["current_todo"]["text"] == "First task"
        assert result["current_todo"]["done"] is False

    def test_extracts_target_files(self, tmp_agent_dir):
        result = read_roadmap({})
        assert "src/app.ts" in result["target_files"]
        assert "src/utils.ts" in result["target_files"]

    def test_no_roadmap(self, tmp_agent_dir):
        (tmp_agent_dir / "gcc" / "main.md").unlink()
        result = read_roadmap({})
        assert result["current_todo"] is None
        assert result["target_files"] == []


class TestHasTodo:
    def test_has_todo(self):
        assert has_todo({"current_todo": {"text": "foo", "done": False, "index": 0}}) == "yes"

    def test_no_todo(self):
        assert has_todo({"current_todo": None}) == "no"


class TestIsFirstTodo:
    def test_first_todo(self):
        state = {
            "roadmap": "## Todos\n- [ ] First\n- [ ] Second",
            "current_todo": {"text": "First", "done": False, "index": 0},
        }
        assert is_first_todo(state) == "yes"

    def test_not_first_todo(self):
        state = {
            "roadmap": "## Todos\n- [x] First\n- [ ] Second",
            "current_todo": {"text": "Second", "done": False, "index": 1},
        }
        assert is_first_todo(state) == "no"
