from sebba_code.tools.progress import add_todo, gcc_commit, mark_todo_done


class TestGccCommit:
    def test_creates_commit_file(self, tmp_agent_dir):
        result = gcc_commit.invoke({"summary": "Test commit", "what_i_did": "- Did stuff"})
        assert "001" in result
        commit_file = tmp_agent_dir / "gcc" / "commits" / "001.md"
        assert commit_file.exists()
        content = commit_file.read_text()
        assert "Test commit" in content
        assert "Did stuff" in content


class TestMarkTodoDone:
    def test_marks_todo(self, tmp_agent_dir):
        result = mark_todo_done.invoke({"todo_text": "First task"})
        assert "Done" in result
        content = (tmp_agent_dir / "gcc" / "main.md").read_text()
        assert "- [x]" in content

    def test_not_found(self, tmp_agent_dir):
        result = mark_todo_done.invoke({"todo_text": "Nonexistent task"})
        assert "Not found" in result


class TestAddTodo:
    def test_adds_todo(self, tmp_agent_dir):
        result = add_todo.invoke({"todo_text": "New task"})
        assert "Added" in result
        content = (tmp_agent_dir / "gcc" / "main.md").read_text()
        assert "- [ ] New task" in content
