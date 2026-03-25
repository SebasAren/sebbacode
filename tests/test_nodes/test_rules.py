from sebba_code.nodes.rules import match_rules


class TestMatchRules:
    def test_loads_global_rules(self, tmp_agent_dir):
        state = {
            "target_files": ["src/app.ts"],
            "memory": {
                "l0_index": "",
                "l1_files": {},
                "l2_files": {},
                "active_rules": {},
                "session_history": "",
            },
        }
        result = match_rules(state)
        assert "global" in result["memory"]["active_rules"]

    def test_loads_scoped_rules_on_match(self, tmp_agent_dir):
        state = {
            "target_files": ["src/app.test.ts"],
            "memory": {
                "l0_index": "",
                "l1_files": {},
                "l2_files": {},
                "active_rules": {},
                "session_history": "",
            },
        }
        result = match_rules(state)
        assert "testing" in result["memory"]["active_rules"]

    def test_skips_scoped_rules_on_mismatch(self, tmp_agent_dir):
        state = {
            "target_files": ["src/app.ts"],
            "memory": {
                "l0_index": "",
                "l1_files": {},
                "l2_files": {},
                "active_rules": {},
                "session_history": "",
            },
        }
        result = match_rules(state)
        assert "testing" not in result["memory"]["active_rules"]
