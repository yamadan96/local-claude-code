"""Tests for OpenAI-compatible provider with mocked httpx transport."""

from __future__ import annotations

import json
from typing import Any

import httpx

from lcc.agent.messages import ChatRequest
from lcc.providers.openai_compat import OpenAICompatProvider


def _make_mock_response(
    content: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    status_code: int = 200,
    usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a mock OpenAI-style response body."""
    message: dict[str, Any] = {}
    if content is not None:
        message["content"] = content
    if tool_calls is not None:
        message["tool_calls"] = tool_calls

    body: dict[str, Any] = {
        "choices": [{"message": message, "finish_reason": "stop"}],
    }
    if usage:
        body["usage"] = usage
    return body


def _create_transport(
    response_body: dict[str, Any],
    status_code: int = 200,
) -> httpx.MockTransport:
    """Create a MockTransport that returns a fixed response."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=status_code,
            json=response_body,
        )

    return httpx.MockTransport(handler)


class TestOpenAICompatProvider:
    def test_plain_text_response(self) -> None:
        body = _make_mock_response(content="Hello!")
        transport = _create_transport(body)
        client = httpx.Client(transport=transport)
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test-model",
            http_client=client,
        )
        request = ChatRequest(
            messages=[{"role": "user", "content": "Hi"}],
            model="test-model",
        )
        response = provider.complete(request)
        assert response.content == "Hello!"
        assert response.tool_calls is None

    def test_tool_call_response(self) -> None:
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": '{"path": "test.txt"}',
                },
            }
        ]
        body = _make_mock_response(tool_calls=tool_calls)
        transport = _create_transport(body)
        client = httpx.Client(transport=transport)
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test-model",
            http_client=client,
        )
        request = ChatRequest(
            messages=[{"role": "user", "content": "read file"}],
            model="test-model",
        )
        response = provider.complete(request)
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "read_file"
        assert response.tool_calls[0].arguments == {"path": "test.txt"}

    def test_legacy_function_call_format(self) -> None:
        """Handle legacy function_call (pre-tool_calls API)."""
        body = {
            "choices": [
                {
                    "message": {
                        "function_call": {
                            "name": "bash",
                            "arguments": '{"command": "ls"}',
                        }
                    },
                    "finish_reason": "function_call",
                }
            ]
        }
        transport = _create_transport(body)
        client = httpx.Client(transport=transport)
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test",
            http_client=client,
        )
        request = ChatRequest(messages=[{"role": "user", "content": "list files"}])
        response = provider.complete(request)
        assert response.tool_calls is not None
        assert response.tool_calls[0].name == "bash"

    def test_usage_parsed(self) -> None:
        body = _make_mock_response(
            content="Hi",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )
        transport = _create_transport(body)
        client = httpx.Client(transport=transport)
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test",
            http_client=client,
        )
        request = ChatRequest(messages=[{"role": "user", "content": "Hi"}])
        response = provider.complete(request)
        assert response.usage is not None
        assert response.usage.prompt_tokens == 10
        assert response.usage.total_tokens == 15

    def test_empty_choices(self) -> None:
        body = {"choices": []}
        transport = _create_transport(body)
        client = httpx.Client(transport=transport)
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test",
            http_client=client,
        )
        request = ChatRequest(messages=[{"role": "user", "content": "Hi"}])
        response = provider.complete(request)
        assert response.content == "(empty response from model)"

    def test_malformed_tool_arguments_stored_as_raw(self) -> None:
        """When arguments can't be parsed, they're stored with _raw key."""
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": "not valid json {{{",
                },
            }
        ]
        body = _make_mock_response(tool_calls=tool_calls)
        transport = _create_transport(body)
        client = httpx.Client(transport=transport)
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test",
            http_client=client,
        )
        request = ChatRequest(messages=[{"role": "user", "content": "test"}])
        response = provider.complete(request)
        assert response.tool_calls is not None
        assert "_raw" in response.tool_calls[0].arguments

    def test_non_dict_tool_call_entries_are_skipped(self) -> None:
        """Malformed entries from weak servers are ignored instead of crashing."""
        tool_calls: list[Any] = [
            "garbage",
            {"id": "call_bad", "type": "function", "function": "read_file"},
            {
                "id": "call_ok",
                "type": "function",
                "function": {"name": "glob", "arguments": '{"pattern": "*.py"}'},
            },
        ]
        body = _make_mock_response(tool_calls=tool_calls)
        transport = _create_transport(body)
        client = httpx.Client(transport=transport)
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test",
            http_client=client,
        )
        request = ChatRequest(messages=[{"role": "user", "content": "find py"}])
        response = provider.complete(request)
        assert response.tool_calls is not None
        assert [call.id for call in response.tool_calls] == ["call_ok"]

    def test_only_malformed_tool_calls_returns_none(self) -> None:
        body = _make_mock_response(content="hi", tool_calls=["garbage"])
        transport = _create_transport(body)
        client = httpx.Client(transport=transport)
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test",
            http_client=client,
        )
        request = ChatRequest(messages=[{"role": "user", "content": "hi"}])
        response = provider.complete(request)
        assert response.content == "hi"
        assert response.tool_calls is None

    def test_api_key_sent_in_header(self) -> None:
        """When api_key is set, Authorization header should be sent."""
        received_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received_headers.update(dict(request.headers))
            return httpx.Response(
                200,
                json=_make_mock_response(content="ok"),
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test",
            api_key="sk-test-key",
            http_client=client,
        )
        request = ChatRequest(messages=[{"role": "user", "content": "Hi"}])
        provider.complete(request)
        assert "authorization" in received_headers
        assert received_headers["authorization"] == "Bearer sk-test-key"

    def test_tool_calls_as_single_object(self) -> None:
        """Some servers return tool_calls as a single dict instead of list."""
        body = {
            "choices": [
                {
                    "message": {
                        "tool_calls": {
                            "id": "call_solo",
                            "type": "function",
                            "function": {
                                "name": "glob",
                                "arguments": '{"pattern": "*.py"}',
                            },
                        }
                    }
                }
            ]
        }
        transport = _create_transport(body)
        client = httpx.Client(transport=transport)
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test",
            http_client=client,
        )
        request = ChatRequest(messages=[{"role": "user", "content": "find py"}])
        response = provider.complete(request)
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "glob"

    def test_tools_sent_in_payload(self) -> None:
        """When tools are provided, they should be in the request payload."""
        received_payload: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received_payload.update(json.loads(request.content))
            return httpx.Response(
                200,
                json=_make_mock_response(content="ok"),
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        provider = OpenAICompatProvider(
            base_url="http://fake:11434/v1",
            model="test",
            http_client=client,
        )
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        request = ChatRequest(
            messages=[{"role": "user", "content": "Hi"}],
            tools=tools,
        )
        provider.complete(request)
        assert "tools" in received_payload
        assert received_payload["tool_choice"] == "auto"
