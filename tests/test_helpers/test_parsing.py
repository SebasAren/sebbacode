import pytest

from sebba_code.helpers.parsing import format_dict, parse_json, parse_json_list


class TestFormatDict:
    def test_simple_dict(self):
        result = format_dict({"key": "value"})
        assert "### key" in result
        assert "value" in result

    def test_nested_dict(self):
        result = format_dict({"key": {"a": 1, "b": 2}})
        assert "### key" in result
        assert "a: 1" in result


class TestParseJson:
    def test_raw_json(self):
        result = parse_json('{"a": 1}')
        assert result == {"a": 1}

    def test_code_fence(self):
        result = parse_json('```json\n{"a": 1}\n```')
        assert result == {"a": 1}

    def test_json_with_surrounding_text(self):
        result = parse_json('Here is the result:\n{"a": 1}\nDone.')
        assert result == {"a": 1}

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError):
            parse_json("not json at all")


class TestParseJsonList:
    def test_raw_list(self):
        result = parse_json_list('["a", "b"]')
        assert result == ["a", "b"]

    def test_code_fence_list(self):
        result = parse_json_list('```json\n["a"]\n```')
        assert result == ["a"]

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_json_list("not a list")
