from sebba_code.tools.progress import add_todo, mark_todo_done


class TestMarkTodoDone:
    def test_marks_todo(self, tmp_agent_dir):
        result = mark_todo_done.invoke({"todo_text": "First task"})
        assert "Done" in result
        content = (tmp_agent_dir / "roadmap.md").read_text()
        assert "- [x]" in content

    def test_not_found(self, tmp_agent_dir):
        result = mark_todo_done.invoke({"todo_text": "Nonexistent task"})
        assert "Not found" in result


class TestAddTodo:
    def test_adds_todo(self, tmp_agent_dir):
        result = add_todo.invoke({"todo_text": "New task"})
        assert "Added" in result
        content = (tmp_agent_dir / "roadmap.md").read_text()
        assert "- [ ] New task" in content
