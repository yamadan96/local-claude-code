"""OpenAI-compatible endpoint provider (Ollama, LM Studio, vLLM)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from lcc.agent.messages import (
    ChatRequest,
    ChatResponse,
    TokenUsage,
    ToolCall,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503}
INITIAL_BACKOFF_SECONDS = 1.0


class OpenAICompatError(Exception):
    """Error from the OpenAI-compatible provider."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenAICompatProvider:
    """Provider for OpenAI-compatible chat completion endpoints.

    Works with Ollama (/v1), LM Studio, vLLM, and any server
    that implements the OpenAI chat completions API.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout: float = 120.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout
        self._client = http_client or httpx.Client(timeout=timeout)

    def complete(self, request: ChatRequest) -> ChatResponse:
        """Send a chat completion request to the OpenAI-compatible endpoint."""
        payload = self._build_payload(request)
        response_data = self._post_with_retry(payload)
        return self._parse_response(response_data)

    def _build_payload(self, request: ChatRequest) -> dict[str, Any]:
        """Build the JSON payload for the API request."""
        payload: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": request.messages,
        }
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = "auto"
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    def _post_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to the completions endpoint with retry on transient errors."""
        url = f"{self._base_url}/chat/completions"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
                if response.status_code in RETRY_STATUS_CODES:
                    last_error = OpenAICompatError(
                        f"Server returned {response.status_code}: "
                        f"{response.text[:200]}",
                        status_code=response.status_code,
                    )
                    backoff = INITIAL_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        "Retrying after %s (attempt %d/%d, status %d)",
                        backoff,
                        attempt + 1,
                        MAX_RETRIES,
                        response.status_code,
                    )
                    time.sleep(backoff)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as exc:
                last_error = exc
                backoff = INITIAL_BACKOFF_SECONDS * (2**attempt)
                logger.warning(
                    "Request timed out (attempt %d/%d), retrying in %ss",
                    attempt + 1,
                    MAX_RETRIES,
                    backoff,
                )
                time.sleep(backoff)
                continue
            except httpx.HTTPStatusError as exc:
                raise OpenAICompatError(
                    f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                    status_code=exc.response.status_code,
                ) from exc

        raise OpenAICompatError(
            f"All {MAX_RETRIES} retries exhausted. Last error: {last_error}"
        )

    def _parse_response(self, data: dict[str, Any]) -> ChatResponse:
        """Parse the API response into a ChatResponse."""
        choices = data.get("choices", [])
        if not choices:
            return ChatResponse(content="(empty response from model)")

        message = choices[0].get("message", {})
        content = message.get("content")
        tool_calls = self._parse_tool_calls(message)
        usage = self._parse_usage(data.get("usage"))

        return ChatResponse(content=content, tool_calls=tool_calls, usage=usage)

    def _parse_tool_calls(self, message: dict[str, Any]) -> list[ToolCall] | None:
        """Parse tool calls from the response message.

        Handles both standard tool_calls and legacy function_call format.
        """
        raw_calls = message.get("tool_calls")

        # Handle legacy function_call format
        if raw_calls is None:
            fn = message.get("function_call")
            if fn:
                raw_calls = [
                    {
                        "id": "legacy_call_0",
                        "type": "function",
                        "function": fn,
                    }
                ]

        if not raw_calls:
            return None

        # Normalize: some servers return a single object instead of a list
        if isinstance(raw_calls, dict):
            raw_calls = [raw_calls]

        result: list[ToolCall] = []
        for i, call in enumerate(raw_calls):
            func = call.get("function", {})
            name = func.get("name", "")
            raw_args = func.get("arguments", "{}")
            call_id = call.get("id", f"call_{i}")

            # Parse arguments (may be string or already a dict)
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {"_raw": raw_args}
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}

            result.append(ToolCall(id=call_id, name=name, arguments=args))

        return result if result else None

    def _parse_usage(self, usage_data: dict[str, Any] | None) -> TokenUsage | None:
        """Parse token usage from the response."""
        if not usage_data:
            return None
        return TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )
