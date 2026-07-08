"""Tests for malformed tool-call JSON recovery."""

from __future__ import annotations

from lcc.agent.recovery import (
    extract_tool_call_from_text,
    fuzzy_match_tool_name,
    recover_tool_call_json,
)

KNOWN_TOOLS = [
    "read_file",
    "write_file",
    "edit_file",
    "bash",
    "glob",
    "grep",
    "list_dir",
]


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


class TestExtractToolCallFromText:
    """Tests for extracting tool calls embedded in assistant content text."""

    def test_fenced_json_tool_call(self) -> None:
        """Fenced JSON with name+arguments -> extracted as tool call."""
        content = (
            '```json\n{"name": "read_file", "arguments": {"path": "notes.txt"}}\n```'
        )
        result = extract_tool_call_from_text(content, KNOWN_TOOLS)
        assert result is not None
        assert result.name == "read_file"
        assert result.arguments == {"path": "notes.txt"}

    def test_bare_json_tool_call(self) -> None:
        """Bare JSON (no fences) with name+arguments."""
        content = '{"name": "read_file", "arguments": {"path": "notes.txt"}}'
        result = extract_tool_call_from_text(content, KNOWN_TOOLS)
        assert result is not None
        assert result.name == "read_file"
        assert result.arguments == {"path": "notes.txt"}

    def test_arguments_as_string(self) -> None:
        """Arguments provided as a JSON string instead of an object."""
        content = '{"name": "bash", "arguments": "{\\"command\\": \\"ls -la\\"}"}'
        result = extract_tool_call_from_text(content, KNOWN_TOOLS)
        assert result is not None
        assert result.name == "bash"
        assert result.arguments == {"command": "ls -la"}

    def test_tool_key_variant(self) -> None:
        """Accept 'tool' as key name instead of 'name'."""
        content = '{"tool": "glob", "arguments": {"pattern": "*.py"}}'
        result = extract_tool_call_from_text(content, KNOWN_TOOLS)
        assert result is not None
        assert result.name == "glob"

    def test_function_key_variant(self) -> None:
        """Accept 'function' as key name instead of 'name'."""
        content = '{"function": "grep", "arguments": {"pattern": "TODO"}}'
        result = extract_tool_call_from_text(content, KNOWN_TOOLS)
        assert result is not None
        assert result.name == "grep"

    def test_prose_only_content_unaffected(self) -> None:
        """Plain prose with no JSON should return None."""
        content = "I'll help you read that file. Let me check."
        result = extract_tool_call_from_text(content, KNOWN_TOOLS)
        assert result is None

    def test_json_with_unknown_tool_name_passed_through(self) -> None:
        """JSON that looks like a tool call but name is not in registry."""
        content = '{"name": "unknown_thing", "arguments": {"x": 1}}'
        result = extract_tool_call_from_text(content, KNOWN_TOOLS)
        assert result is None

    def test_json_answer_not_hijacked(self) -> None:
        """A JSON object in the answer that is NOT a tool call."""
        content = 'Here is the config:\n{"database": "postgres", "port": 5432}'
        result = extract_tool_call_from_text(content, KNOWN_TOOLS)
        assert result is None

    def test_prose_with_trailing_json_tool_call(self) -> None:
        """Content has both prose and a JSON tool call -- extract the call."""
        content = (
            "I need to read the file first.\n"
            '{"name": "read_file", "arguments": {"path": "data.txt"}}'
        )
        result = extract_tool_call_from_text(content, KNOWN_TOOLS)
        assert result is not None
        assert result.name == "read_file"
        assert result.arguments == {"path": "data.txt"}

    def test_empty_content(self) -> None:
        result = extract_tool_call_from_text("", KNOWN_TOOLS)
        assert result is None

    def test_none_content(self) -> None:
        result = extract_tool_call_from_text(None, KNOWN_TOOLS)  # type: ignore[arg-type]
        assert result is None

    def test_fuzzy_name_match_in_extraction(self) -> None:
        """Typo in tool name should be fuzzy-matched."""
        content = '{"name": "reed_file", "arguments": {"path": "x.txt"}}'
        result = extract_tool_call_from_text(content, KNOWN_TOOLS)
        assert result is not None
        assert result.name == "read_file"
