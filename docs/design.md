# local-claude-code (lcc) -- Architecture & Implementation Plan

> Generated via Codex (gpt-5.4) consultation + critical review.
> Date: 2026-07-08

---

## 1. Architecture

### Module Layout

```text
local-claude-code/
├── pyproject.toml
├── README.md
├── .env.example
├── src/lcc/
│   ├── __init__.py
│   ├── __main__.py          # python -m lcc entry
│   ├── cli.py               # argparse, one-shot mode
│   ├── repl.py              # interactive REPL session
│   ├── slash_commands.py    # /help, /clear, /model, /exit, etc.
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── loop.py          # AgentRunner: send-execute-repeat loop
│   │   ├── messages.py      # ConversationState, ChatMessage models
│   │   ├── context.py       # ContextManager: token-budget trimming
│   │   ├── prompts.py       # System prompt templates
│   │   └── recovery.py      # Malformed tool-call JSON recovery
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py          # ChatProvider protocol + shared types
│   │   ├── openai_compat.py # OpenAI-compatible endpoint (Ollama/LM Studio/vLLM)
│   │   ├── anthropic.py     # (stub for future Anthropic API backend)
│   │   └── mock.py          # Deterministic scripted provider for tests
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py      # ToolRegistry: lookup, schema export, dispatch
│   │   ├── base.py          # Tool protocol, ToolSpec, ToolResult
│   │   ├── fs_read.py       # read_file
│   │   ├── fs_write.py      # write_file
│   │   ├── fs_edit.py       # edit_file (exact string replace)
│   │   ├── shell.py         # bash (subprocess execution)
│   │   ├── glob_search.py   # glob (file pattern search)
│   │   ├── grep_search.py   # grep (content search)
│   │   └── list_dir.py      # list_dir
│   ├── safety/
│   │   ├── __init__.py
│   │   ├── permissions.py   # PermissionMode, PermissionManager
│   │   ├── sandbox.py       # WorkspaceSandbox: path resolution + containment
│   │   └── prompts.py       # User-facing permission prompt formatting
│   ├── config/
│   │   ├── __init__.py
│   │   ├── loader.py        # Multi-source config merging
│   │   └── models.py        # AppConfig dataclass
│   └── utils/
│       ├── logging.py       # Structured logging setup
│       ├── paths.py         # Path normalization helpers
│       └── json.py          # Lenient JSON parsing helpers
└── tests/
    ├── conftest.py           # Shared fixtures (mock provider, temp workspace)
    ├── test_agent_loop.py
    ├── test_context.py
    ├── test_permissions.py
    ├── test_sandbox.py
    ├── test_recovery.py
    ├── test_config.py
    ├── test_provider_openai_compat.py
    └── tools/
        ├── test_fs_read.py
        ├── test_fs_write.py
        ├── test_fs_edit.py
        ├── test_shell.py
        ├── test_glob.py
        ├── test_grep.py
        └── test_list_dir.py
```

### Key Classes & Signatures

```python
# --- cli.py ---
def main(argv: list[str] | None = None) -> int: ...
# Parses: -p/--prompt, --model, --base-url, --permission-mode, --cwd

# --- repl.py ---
class ReplSession:
    def __init__(self, config: AppConfig, provider: ChatProvider, runner: AgentRunner) -> None: ...
    def run(self) -> int: ...

# --- agent/loop.py ---
class AgentRunner:
    def run_turn(self, user_input: str) -> AgentTurnResult: ...
    def _execute_tool_calls(self, tool_calls: list[ToolCall]) -> list[ToolResultMessage]: ...
    # max_iterations: int = 10 (prevent infinite loops)

# --- agent/messages.py ---
@dataclass
class ConversationState:
    messages: list[ChatMessage]
    def append_user(self, content: str) -> None: ...
    def append_assistant(self, content: str | None, tool_calls: list[ToolCall] | None) -> None: ...
    def append_tool_result(self, tool_call_id: str, content: str) -> None: ...

# --- agent/context.py ---
class ContextManager:
    def trim(self, messages: list[ChatMessage], max_input_tokens: int) -> list[ChatMessage]: ...
    # v1: character-based estimate (chars / 4), drop oldest user/assistant/tool groups

# --- agent/recovery.py ---
def recover_tool_call_json(raw: str) -> dict[str, Any] | None: ...
# Strips markdown fences, extracts first {...}, attempts json.loads

# --- providers/base.py ---
class ChatProvider(Protocol):
    def complete(self, request: ChatRequest) -> ChatResponse: ...

@dataclass
class ChatRequest:
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None
    model: str
    max_tokens: int | None

@dataclass
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall] | None
    usage: TokenUsage | None

# --- providers/openai_compat.py ---
class OpenAICompatProvider:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: float = 120.0) -> None: ...
    def complete(self, request: ChatRequest) -> ChatResponse: ...
    # Uses httpx; retries transient errors (429, 500, 502, 503); normalizes response

# --- providers/mock.py ---
class MockProvider:
    def __init__(self, responses: list[ChatResponse]) -> None: ...
    def complete(self, request: ChatRequest) -> ChatResponse: ...
    # Pops from queue; raises if exhausted

# --- tools/base.py ---
class Tool(Protocol):
    name: str
    def schema(self) -> dict[str, Any]: ...
    def execute(self, args: dict[str, Any], ctx: ToolExecutionContext) -> ToolResult: ...

@dataclass
class ToolResult:
    status: Literal["ok", "error"]
    output: str

@dataclass
class ToolExecutionContext:
    sandbox: WorkspaceSandbox
    permissions: PermissionManager

# --- tools/registry.py ---
class ToolRegistry:
    def register(self, tool: Tool) -> None: ...
    def get(self, name: str) -> Tool | None: ...
    def openai_schemas(self) -> list[dict[str, Any]]: ...
    def execute_tool_call(self, name: str, arguments_json: str, ctx: ToolExecutionContext) -> ToolResult: ...

# --- safety/sandbox.py ---
class WorkspaceSandbox:
    def __init__(self, workspace_root: Path) -> None: ...
    def resolve_path(self, path: str) -> Path: ...
    def ensure_within_workspace(self, path: Path) -> None: ...

# --- safety/permissions.py ---
class PermissionMode(StrEnum):
    ASK = "ask"
    AUTO = "auto"

class PermissionManager:
    def require(self, action: PermissionRequest) -> PermissionDecision: ...

# --- config/models.py ---
@dataclass
class AppConfig:
    model: str = "qwen2.5-coder:14b"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = ""
    permission_mode: PermissionMode = PermissionMode.ASK
    max_input_tokens: int = 16000
    max_output_tokens: int = 2000
    tool_timeout_seconds: int = 30
    allow_outside_cwd: bool = False
```

---

## 2. Agent Loop Design

### Message Flow

```
User input
  │
  ▼
[1] Build/refresh system prompt (tools, sandbox rules, style)
  │
  ▼
[2] Append user message to ConversationState
  │
  ▼
[3] Trim conversation to token budget (ContextManager.trim)
  │
  ▼
[4] Send messages + tool schemas to ChatProvider.complete()
  │
  ▼
[5] Parse response ──► plain text only? ──► Render & STOP
  │
  ▼ (tool_calls present)
[6] For each tool_call:
    a. Parse arguments (with recovery.recover_tool_call_json on failure)
    b. Check permissions (PermissionManager.require)
    c. Execute tool (Tool.execute)
    d. Append tool result message (role="tool", tool_call_id=...)
  │
  ▼
[7] Append assistant message (with tool_calls) to history
  │
  ▼
[8] If iterations < max_iterations → go to [3]
    Else → emit "max iterations reached" error and STOP
```

### Message Roles (OpenAI-style normalization)

- `system` -- system prompt (always kept, never trimmed)
- `user` -- user input
- `assistant` -- model response (may include `tool_calls`)
- `tool` -- tool execution result (must include `tool_call_id`)

### Error Handling

| Error Type | Action |
|---|---|
| Invalid JSON in tool args | `recovery.recover_tool_call_json()`: strip fences, extract `{...}`, retry parse. If still fails, append error tool result and continue loop. |
| Unknown tool name | Append error tool result: "Unknown tool: {name}. Available: ..." |
| Tool execution exception | Catch, return `ToolResult(status="error", output=str(e))`, continue |
| Provider HTTP error (429/5xx) | Retry with exponential backoff (max 3 retries) |
| Provider returns unparseable response | Log warning, attempt JSON extraction from raw body |
| Infinite loop (identical tool calls repeated) | Detect 3 consecutive identical calls, emit error, stop |
| Max iterations reached | Emit user-facing warning, stop loop |

### Context Trimming (v1)

- System prompt: **always kept** (pinned).
- Newest messages: kept first.
- Drop oldest complete groups (user + assistant + tool results as a unit).
- Token estimate: `len(json.dumps(message)) / 4` (rough chars-to-tokens).
- Safety margin: reserve 20% of budget for output.
- v2 enhancement: summarize dropped history into a synthetic system note.

---

## 3. Tool Specs

All tools use OpenAI function-calling JSON schema format.

### read_file

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read the contents of a file. Returns the file content with line numbers.",
    "parameters": {
      "type": "object",
      "properties": {
        "path": { "type": "string", "description": "File path (relative to workspace root)" },
        "start_line": { "type": "integer", "description": "Start line (1-indexed, optional)", "minimum": 1 },
        "end_line": { "type": "integer", "description": "End line (1-indexed, optional)", "minimum": 1 }
      },
      "required": ["path"],
      "additionalProperties": false
    }
  }
}
```
Safety: sandbox path check, file existence, text-file heuristic (reject binary), size cap (1MB default).

### write_file

```json
{
  "type": "function",
  "function": {
    "name": "write_file",
    "description": "Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
    "parameters": {
      "type": "object",
      "properties": {
        "path": { "type": "string", "description": "File path (relative to workspace root)" },
        "content": { "type": "string", "description": "Content to write" }
      },
      "required": ["path", "content"],
      "additionalProperties": false
    }
  }
}
```
Safety: sandbox, permission required (ask mode), create parent dirs if needed.

### edit_file

```json
{
  "type": "function",
  "function": {
    "name": "edit_file",
    "description": "Replace exact text in a file. old_text must match exactly once unless replace_all is true.",
    "parameters": {
      "type": "object",
      "properties": {
        "path": { "type": "string", "description": "File path (relative to workspace root)" },
        "old_text": { "type": "string", "description": "Exact text to find and replace" },
        "new_text": { "type": "string", "description": "Replacement text" },
        "replace_all": { "type": "boolean", "description": "Replace all occurrences (default false)", "default": false }
      },
      "required": ["path", "old_text", "new_text"],
      "additionalProperties": false
    }
  }
}
```
Safety: sandbox, permission, match count validation (must be exactly 1 unless replace_all).

### bash

```json
{
  "type": "function",
  "function": {
    "name": "bash",
    "description": "Execute a shell command and return stdout/stderr.",
    "parameters": {
      "type": "object",
      "properties": {
        "command": { "type": "string", "description": "Shell command to execute" },
        "timeout_seconds": { "type": "integer", "description": "Timeout in seconds (default 30)", "minimum": 1, "maximum": 300 }
      },
      "required": ["command"],
      "additionalProperties": false
    }
  }
}
```
Safety: permission always required, cwd locked to workspace, timeout enforced, stdout/stderr captured and size-capped.

### glob

```json
{
  "type": "function",
  "function": {
    "name": "glob",
    "description": "Find files matching a glob pattern within the workspace.",
    "parameters": {
      "type": "object",
      "properties": {
        "pattern": { "type": "string", "description": "Glob pattern (e.g. '**/*.py')" },
        "include_hidden": { "type": "boolean", "description": "Include hidden files (default false)", "default": false }
      },
      "required": ["pattern"],
      "additionalProperties": false
    }
  }
}
```
Safety: workspace-rooted only, result count cap (1000 entries).

### grep

```json
{
  "type": "function",
  "function": {
    "name": "grep",
    "description": "Search file contents for a regex or literal pattern.",
    "parameters": {
      "type": "object",
      "properties": {
        "pattern": { "type": "string", "description": "Search pattern (regex)" },
        "path": { "type": "string", "description": "Directory or file to search (default: workspace root)" },
        "file_glob": { "type": "string", "description": "Only search files matching this glob (e.g. '*.py')" },
        "max_matches": { "type": "integer", "description": "Max results to return (default 50)", "minimum": 1 }
      },
      "required": ["pattern"],
      "additionalProperties": false
    }
  }
}
```
Safety: workspace-only, result count cap.

### list_dir

```json
{
  "type": "function",
  "function": {
    "name": "list_dir",
    "description": "List directory contents with file types and sizes.",
    "parameters": {
      "type": "object",
      "properties": {
        "path": { "type": "string", "description": "Directory path (default: workspace root)", "default": "." },
        "recursive": { "type": "boolean", "description": "List recursively (default false)", "default": false }
      },
      "required": [],
      "additionalProperties": false
    }
  }
}
```
Safety: sandbox, recursion depth cap (3 levels), entry count cap.

---

## 4. Permission & Sandbox Design

### Permission Modes

| Mode | Behavior |
|---|---|
| `ask` (default) | Prompt user `[y/N]` before `write_file`, `edit_file`, `bash`. Default deny on empty/timeout. |
| `auto` | Allow all tool executions without prompting. Sandbox still enforced. |

Prompt format (ask mode):
```
[permission] bash: rm -rf build/
  Allow? [y/N]:
```

### Sandbox Rules

1. **Canonical workspace root**: `Path(cwd).resolve()` at session start.
2. **Path resolution**: all tool paths resolved as `(workspace_root / user_path).resolve()`.
3. **Symlink defense**: resolve symlinks via `Path.resolve()` BEFORE containment check. A symlink inside workspace pointing outside is rejected.
4. **`..` traversal defense**: resolved path must start with `workspace_root`. Since `Path.resolve()` normalizes `..`, this is automatic.
5. **Absolute paths**: if tool receives an absolute path, resolve it and check containment. Reject if outside workspace (unless `allow_outside_cwd=true`).
6. **`bash` tool**: `subprocess.run(cwd=workspace_root)`. Cannot change cwd. PATH is inherited but execution is always rooted.
7. **`allow_outside_cwd` config flag**: when true, skip containment check (power-user escape hatch). Default false.

### Edge Cases Addressed

- Symlink to `/etc/passwd` inside workspace: **rejected** (resolved path escapes).
- `../../etc/passwd` relative path: **rejected** (resolved path escapes).
- Absolute path `/tmp/foo`: **rejected** unless `allow_outside_cwd=true`.
- Path with `~`: expanded via `Path.expanduser()` then resolved and checked.
- Race condition (TOCTOU): acknowledged as v1 limitation; atomic ops not guaranteed for local dev tool.

---

## 5. CLI/UX Design

### Entry Points

```bash
# Interactive REPL
lcc

# One-shot mode
lcc -p "fix the failing test in test_auth.py"

# With overrides
lcc --model llama3.1:8b --base-url http://localhost:1234/v1 --permission-mode auto
```

### REPL Flow

```
1. Load config (home → project → env → CLI flags)
2. Initialize provider + agent
3. Print banner:
   lcc v0.1.0 | model: qwen2.5-coder:14b | http://localhost:11434/v1 | mode: ask
   Type /help for commands, /exit to quit.
4. Loop:
   a. Read input (supports multiline via trailing \)
   b. If starts with / → dispatch slash command
   c. Else → agent.run_turn(input) → render result
5. On /exit or Ctrl+D → clean exit
```

### Slash Commands

| Command | Action |
|---|---|
| `/help` | Show available commands |
| `/clear` | Reset conversation history |
| `/model [name]` | Show or switch current model |
| `/base_url [url]` | Show or switch endpoint URL |
| `/permission [ask\|auto]` | Show or switch permission mode |
| `/tools` | List registered tools with descriptions |
| `/exit` | Exit the REPL |

### Rendering (via `rich`)

- **Assistant text**: `rich.Markdown` rendering (syntax highlighting, headings, lists).
- **Tool execution**: compact panel showing tool name + args summary + spinner.
- **Tool result**: collapsed by default, expandable. Truncated if >100 lines.
- **Permission prompt**: yellow-highlighted synchronous `[y/N]` prompt.
- **Errors**: red panel with error type and message (no Python traceback).

### Signal Handling

- **Ctrl+C during tool execution**: cancel the running tool (kill subprocess for bash), append cancellation result, let agent know the tool was cancelled.
- **Ctrl+C during LLM call**: cancel the HTTP request, return to prompt.
- **Ctrl+C at prompt**: print hint ("Press Ctrl+D or type /exit to quit").
- **Ctrl+D**: clean exit.

---

## 6. Config Design

### Precedence (lowest to highest)

1. Built-in defaults
2. `~/.lcc/config.toml` (global user config)
3. `.lcc.toml` in project directory (project-specific)
4. Environment variables
5. CLI flags

### Config File Format

```toml
# ~/.lcc/config.toml
model = "qwen2.5-coder:14b"
base_url = "http://localhost:11434/v1"
api_key = ""                      # optional, most local servers don't need it
permission_mode = "ask"           # "ask" | "auto"
max_input_tokens = 16000
max_output_tokens = 2000
tool_timeout_seconds = 30
allow_outside_cwd = false
```

### Environment Variables

| Variable | Maps to |
|---|---|
| `LCC_MODEL` | `model` |
| `LCC_BASE_URL` | `base_url` |
| `LCC_API_KEY` | `api_key` |
| `LCC_PERMISSION_MODE` | `permission_mode` |
| `LCC_MAX_INPUT_TOKENS` | `max_input_tokens` |

### CLI Flags

```
--model TEXT         Override model name
--base-url TEXT      Override API base URL
--api-key TEXT       Override API key
--permission-mode    Override permission mode (ask/auto)
--cwd PATH           Override working directory
-p, --prompt TEXT    One-shot mode prompt
```

---

## 7. Implementation Plan

### Step 1: Bootstrap project
- Create `pyproject.toml` with dependencies: `httpx`, `rich`, `tomli` (for py<3.11 compat, or use stdlib tomllib), `pytest`, `ruff`.
- Set up `src/lcc/__init__.py`, `__main__.py`.
- Configure ruff in pyproject.toml.
- **Acceptance**: `uv sync && uv run ruff check . && uv run pytest` all succeed (with 0 tests).

### Step 2: Core models & config
- Implement `config/models.py` (AppConfig dataclass).
- Implement `config/loader.py` (TOML + env + defaults merging).
- Implement `agent/messages.py` (ChatMessage, ConversationState, ChatRequest, ChatResponse, ToolCall).
- **Acceptance**: unit tests for config precedence, message serialization.

### Step 3: Sandbox & permissions
- Implement `safety/sandbox.py` (WorkspaceSandbox with resolve + containment).
- Implement `safety/permissions.py` (PermissionManager, ask/auto modes).
- **Acceptance**: tests for `..` traversal, symlinks, absolute paths, ask-mode deny.

### Step 4: Tool framework & registry
- Implement `tools/base.py` (Tool protocol, ToolSpec, ToolResult, ToolExecutionContext).
- Implement `tools/registry.py` (registration, schema export, dispatch).
- **Acceptance**: registry returns valid OpenAI-format tool schemas.

### Step 5: Filesystem & search tools
- Implement `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `list_dir`.
- Each tool: schema + execute + sandbox integration.
- **Acceptance**: per-tool tests including happy path, error cases (missing file, no match, binary file).

### Step 6: Bash tool
- Implement `shell.py` with `subprocess.run`, timeout, cwd lock, output capture.
- **Acceptance**: tests for successful command, nonzero exit, timeout, permission denial in ask mode.

### Step 7: Providers (OpenAI-compat + Mock)
- Implement `providers/base.py` (ChatProvider protocol).
- Implement `providers/openai_compat.py` (httpx POST, response parsing, retry logic).
- Implement `providers/mock.py` (scripted response queue).
- **Acceptance**: mocked HTTP tests for plain-text response, tool-call response, error recovery.

### Step 8: Agent loop
- Implement `agent/loop.py` (AgentRunner).
- Implement `agent/context.py` (ContextManager with trimming).
- Implement `agent/prompts.py` (system prompt template).
- Implement `agent/recovery.py` (malformed JSON recovery).
- **Acceptance**: multi-turn tests with MockProvider: normal flow, tool errors, unknown tool, max iterations, JSON recovery.

### Step 9: CLI one-shot mode
- Implement `cli.py` (argparse, one-shot `-p` path).
- Wire up: config load → provider init → agent run → print result → exit.
- **Acceptance**: subprocess-level test: `uv run python -m lcc -p "test"` with mock.

### Step 10: REPL & slash commands
- Implement `repl.py` (ReplSession with input loop).
- Implement `slash_commands.py` (dispatch table).
- Implement `ui/console.py` + `ui/render.py` (rich markdown rendering, tool panels).
- **Acceptance**: unit tests for slash command parsing; manual smoke test for REPL interaction.

### Step 11: Weak-model hardening
- Enhance `recovery.py`: markdown fence stripping, first-`{...}` extraction, arguments-as-string handling, tool-name fuzzy match.
- Add repeated-call detection in agent loop.
- **Acceptance**: tests with intentionally malformed tool-call payloads.

### Step 12: Polish & documentation
- System prompt tuning (tool usage instructions for local models).
- README with setup guide for Ollama, LM Studio, vLLM.
- `.env.example`.
- Ensure `ruff check` and `ruff format --check` pass.
- Full test suite green.
- **Acceptance**: `uv run ruff check . && uv run ruff format --check . && uv run pytest -v` all pass.

---

## 8. Risks & Mitigations

### R1: Weak tool-calling in small local models
Small models (7B-14B) frequently produce malformed JSON, ignore schemas, hallucinate tool names, or emit tool calls as plain text.

**Mitigations:**
- Keep tool schemas minimal (few parameters, short descriptions).
- `recovery.py`: strip markdown fences, extract first `{...}`, parse `arguments` when it's a string instead of object.
- Fuzzy tool-name matching (Levenshtein distance < 3 from a known tool name).
- One-retry protocol: if args are unparseable, send a follow-up message asking the model to re-emit only the JSON arguments.
- System prompt explicitly instructs: "Always respond with valid JSON for tool arguments. Never wrap in markdown."
- Detect 3 consecutive identical tool calls as infinite loop and break.

### R2: OpenAI-compatible API variance
Different servers (Ollama vs LM Studio vs vLLM) return slightly different tool-call response shapes.

**Mitigations:**
- Normalize all responses into internal `ChatResponse` dataclass immediately after HTTP response.
- Handle both `tool_calls` as list of objects and as a single object.
- Handle `function_call` (legacy format) as fallback.
- Test against mocked response variants from each server type.

### R3: Token counting without model-specific tokenizer
No access to the actual tokenizer for local models.

**Mitigations:**
- v1: rough estimate at `len(json.dumps(messages)) / 4` tokens.
- Trim conservatively (leave 20% margin for output).
- Make `max_input_tokens` user-configurable so they can tune for their model's actual context window.
- v2: optional tiktoken integration for known model families.

### R4: Bash tool security
Arbitrary command execution is the highest-risk tool.

**Mitigations:**
- Default to `ask` permission mode (always prompt before bash).
- `cwd` locked to workspace root (tool cannot `cd` outside).
- Timeout enforced (default 30s, max 300s).
- Output size capped (truncate stdout/stderr beyond 100KB).
- Consider optional command denylist in v2 (e.g., `rm -rf /`).

### R5: edit_file frustration
Exact-string matching can frustrate weak models that hallucinate whitespace or partial matches.

**Mitigations:**
- Return clear error: "Found 0 matches for old_text. Use read_file first to see exact content."
- System prompt instructs: "Always read_file before edit_file to see exact text."
- Return match count in error to help model adjust.

### R6: REPL UX degradation with verbose tool output
Large file reads or command outputs can flood the terminal.

**Mitigations:**
- Cap displayed tool output (100 lines, 10KB visible; full content still passed to model).
- Show "[truncated, N lines omitted]" indicator.
- Collapsible output in rich panel (v2).

### R7: Streaming (out of v1 scope)
v1 uses non-streaming completions. This means the user sees nothing until the full response arrives, which can be slow for large responses on local models.

**Mitigation (v2):**
- Add streaming support via SSE parsing in `openai_compat.py`.
- Accumulate tool_calls from deltas before dispatching.
- This is explicitly deferred to v2 to keep v1 implementation simple.

---

## Appendix: Scope Boundaries

### v1 (this plan)
- Agent loop with tool calling
- 7 tools (read_file, write_file, edit_file, bash, glob, grep, list_dir)
- Permission system (ask/auto)
- Workspace sandbox
- Interactive REPL + one-shot mode
- Config (TOML + env + CLI)
- Context trimming (simple truncation)
- Mock provider for testing
- Weak-model JSON recovery

### v2 (future)
- Streaming responses
- History summarization (instead of truncation)
- Anthropic API provider
- Multi-file diff view
- Session persistence / conversation save-load
- Plugin/extension system for custom tools
- Shell command safety heuristics (denylist, risk scoring)
- Optional tiktoken integration
