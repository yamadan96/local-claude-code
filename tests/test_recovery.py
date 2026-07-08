"""Tests for malformed tool-call JSON recovery."""

from __future__ import annotations

from lcc.agent.recovery import (
    fuzzy_match_tool_name,
    recover_tool_call_json,
)


class TestRecoverToolCallJson:
    def test_valid_json_passthrough(self) -> None:
        result = recover_tool_call_json('{"path": "test.txt"}')
        assert result == {"path": "test.txt"}

    def test_strip_markdown_fences(self) -> None:
        raw = '```json\n{"path": "test.txt"}\n```'
        result = recover_tool_call_json(raw)
        assert result == {"path": "test.txt"}

    def test_strip_markdown_fences_no_language(self) -> None:
        raw = '```\n{"command": "ls"}\n```'
        result = recover_tool_call_json(raw)
        assert result == {"command": "ls"}

    def test_extract_json_from_text(self) -> None:
        raw = 'Here is the result: {"path": "file.py", "content": "hello"} end'
        result = recover_tool_call_json(raw)
        assert result == {"path": "file.py", "content": "hello"}

    def test_trailing_comma_fix(self) -> None:
        raw = '{"path": "test.txt", "content": "data",}'
        result = recover_tool_call_json(raw)
        assert result == {"path": "test.txt", "content": "data"}

    def test_single_quotes_fix(self) -> None:
        raw = "{'path': 'test.txt'}"
        result = recover_tool_call_json(raw)
        assert result == {"path": "test.txt"}

    def test_nested_json_object(self) -> None:
        raw = '{"path": "f.txt", "options": {"recursive": true}}'
        result = recover_tool_call_json(raw)
        assert result is not None
        assert result["path"] == "f.txt"
        assert result["options"]["recursive"] is True

    def test_completely_invalid_returns_none(self) -> None:
        result = recover_tool_call_json("this is not json at all")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = recover_tool_call_json("")
        assert result is None

    def test_none_input_returns_none(self) -> None:
        result = recover_tool_call_json(None)  # type: ignore[arg-type]
        assert result is None

    def test_json_with_surrounding_text(self) -> None:
        raw = 'I will read the file:\n{"path": "README.md"}\nDone.'
        result = recover_tool_call_json(raw)
        assert result == {"path": "README.md"}

    def test_arguments_as_string_with_raw_key(self) -> None:
        """When arguments is a string (not dict), provider stores it as _raw."""
        raw = '{"_raw": "{\\"path\\": \\"test.txt\\"}"}'
        result = recover_tool_call_json(raw)
        assert result == {"path": "test.txt"}


class TestFuzzyMatchToolName:
    def test_exact_match(self) -> None:
        tools = ["read_file", "write_file", "bash"]
        assert fuzzy_match_tool_name("read_file", tools) == "read_file"

    def test_case_insensitive_match(self) -> None:
        tools = ["read_file", "write_file"]
        assert fuzzy_match_tool_name("Read_File", tools) == "read_file"

    def test_close_typo(self) -> None:
        tools = ["read_file", "write_file", "edit_file", "bash"]
        # "reed_file" is 1 edit away from "read_file"
        assert fuzzy_match_tool_name("reed_file", tools) == "read_file"

    def test_no_match_when_too_far(self) -> None:
        tools = ["read_file", "write_file"]
        assert fuzzy_match_tool_name("completely_different", tools) is None

    def test_empty_candidate(self) -> None:
        tools = ["read_file"]
        assert fuzzy_match_tool_name("", tools) is None

    def test_empty_known_names(self) -> None:
        assert fuzzy_match_tool_name("read_file", []) is None

    def test_bash_typo(self) -> None:
        tools = ["bash", "read_file", "glob"]
        assert fuzzy_match_tool_name("bsh", tools) == "bash"

    def test_underscore_vs_no_underscore(self) -> None:
        tools = ["read_file", "write_file"]
        # "readfile" is 1 edit from "read_file"
        assert fuzzy_match_tool_name("readfile", tools) == "read_file"
