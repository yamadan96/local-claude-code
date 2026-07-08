# local-claude-code (lcc)

A local-first AI coding agent powered by local LLMs via OpenAI-compatible APIs (Ollama, LM Studio, vLLM).

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
git clone https://github.com/youruser/local-claude-code.git
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
| `auto` | Allows all tool executions without prompting. Sandbox still enforced. |

## Security

- **Workspace sandbox**: All file paths are resolved and checked to stay within the working directory
- **Symlink defense**: Symlinks are resolved before containment checks
- **Path traversal defense**: `../` attacks are blocked by path resolution
- **Bash cwd lock**: Shell commands always run with cwd set to workspace root
- **Output capping**: Tool output is truncated at 100KB to prevent memory issues
- **Timeouts**: Shell commands have a configurable timeout (default 30s, max 300s)

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

MIT
