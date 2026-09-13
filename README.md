# local-claude-code (lcc)

[![CI](https://github.com/yamadan96/local-claude-code/actions/workflows/ci.yml/badge.svg)](https://github.com/yamadan96/local-claude-code/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-3776AB)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A local-first AI coding agent powered by local LLMs via OpenAI-compatible APIs (Ollama, LM Studio, vLLM).

> This is an unofficial project and is not affiliated with or endorsed by Anthropic.

## Features

- **Local-first**: Works with any OpenAI-compatible local LLM server
- **7 built-in tools**: read_file, write_file, edit_file, bash, glob, grep, list_dir
- **Workspace sandbox**: All file operations confined to the working directory
- **Permission system**: `ask` mode (prompt before writes/commands) or `auto` mode
- **Weak-model hardening**: JSON recovery, fuzzy tool-name matching, infinite-loop detection
- **Interactive REPL** with slash commands + one-shot CLI mode

## Installation

```bash
# Clone the repository
git clone https://github.com/yamadan96/local-claude-code.git
cd local-claude-code

# Install with uv
uv sync

# Verify installation
uv run lcc --help
```

## Quick Start

### Prerequisites

You need a local LLM server running an OpenAI-compatible API. Supported servers:

#### Ollama (recommended for beginners)

```bash
# Install Ollama: https://ollama.ai
ollama pull qwen2.5-coder:14b
ollama serve
# API available at http://localhost:11434/v1
```

#### LM Studio

```bash
# Download from https://lmstudio.ai
# Load a model and start the server
# API available at http://localhost:1234/v1
```

#### vLLM

```bash
pip install vllm
vllm serve Qwen/Qwen2.5-Coder-14B-Instruct --port 8000
# API available at http://localhost:8000/v1
```

### Usage

#### Interactive REPL

```bash
# Start with defaults (Ollama on localhost:11434)
uv run lcc

# With custom model and endpoint
uv run lcc --model llama3.1:8b --base-url http://localhost:1234/v1

# Auto-approve all tool executions (use with caution)
uv run lcc --permission-mode auto
```

#### One-shot Mode

```bash
# Run a single prompt and exit
uv run lcc -p "read the README and summarize it"

# Fix a specific file
uv run lcc -p "fix the failing test in test_auth.py"
```

#### REPL Slash Commands

| Command | Action |
|---|---|
| `/help` | Show available commands |
| `/clear` | Reset conversation history |
| `/model [name]` | Show or switch current model |
| `/base_url [url]` | Show or switch endpoint URL |
| `/permission [ask\|auto]` | Show or switch permission mode |
| `/tools` | List registered tools |
| `/exit` | Exit the REPL |

## Configuration

### Config File

Create `~/.lcc/config.toml` for global settings or `.lcc.toml` in your project:

```toml
model = "qwen2.5-coder:14b"
base_url = "http://localhost:11434/v1"
api_key = ""
permission_mode = "ask"
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

### Precedence (lowest to highest)

1. Built-in defaults
2. `~/.lcc/config.toml`
3. `.lcc.toml` in project directory
4. Environment variables
5. CLI flags

## Permission Modes

| Mode | Behavior |
|---|---|
| `ask` (default) | Prompts `[y/N]` before write_file, edit_file, and bash. Default deny. |
| `auto` | Allows all tool executions without prompting. File tools stay confined to the workspace; `bash` does not (see Security). |

## Security

- **Workspace sandbox**: All file paths are resolved and checked to stay within the working directory
- **Symlink defense**: Symlinks are resolved before containment checks
- **Path traversal defense**: `../` attacks are blocked by path resolution
- **Bash cwd lock**: Shell commands always start with cwd set to the workspace root. This is not a sandbox: a command can still read or write outside the workspace (e.g. absolute paths or `cd ..`), so review commands in `ask` mode and use `auto` only in trusted or disposable environments
- **Output capping**: Tool output is truncated at 100KB to prevent memory issues
- **Timeouts**: Shell commands have a configurable timeout (default 30s, max 300s)

## Troubleshooting

### `model 'xxx' not found` even though `ollama list` shows it

On macOS, `localhost` can resolve to the IPv6 loopback (`::1`) instead of
`127.0.0.1`, and other local services (e.g. an editor's bundled model server)
may also be listening on `::1:11434`. If your request gets routed there
instead of to your actual Ollama server, you'll see a 404 for a model that
clearly exists.

Check who is actually listening on the port:

```bash
lsof -nP -iTCP:11434 -sTCP:LISTEN
```

If more than one process shows up, point `lcc` at the IPv4 address
explicitly to avoid the ambiguous `localhost` resolution:

```bash
uv run lcc --base-url http://127.0.0.1:11434/v1
```

You can also bake this into `.lcc.toml` / `~/.lcc/config.toml` so you don't
need the flag every time:

```toml
base_url = "http://127.0.0.1:11434/v1"
```

### Model calls tools for simple greetings or refuses general questions

Small local models (e.g. 14B-class) sometimes struggle to distinguish
"casual chat" from "a task that needs tools," and may invent file operations
just to have something to do, or refuse to answer general knowledge
questions because the system prompt frames the assistant narrowly as a
"coding assistant." This is addressed in the system prompt
(`src/lcc/agent/prompts.py`) with explicit rules to only call tools for
concrete in-workspace tasks and to answer general/conceptual questions
directly. If you still see this with a smaller or more quantized model, try
a larger model or tighten the system prompt further.

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest -v

# Lint and format
uv run ruff check .
uv run ruff format --check .
```

## License

MIT — see [LICENSE](LICENSE).
