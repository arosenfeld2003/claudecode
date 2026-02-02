# Ralph Docker

Containerized Ralph Loop for secure, headless autonomous development.

## Overview

This container runs the Ralph Wiggum methodology in a Docker environment, providing:

- **Security isolation** via containerization
- **Human-readable output** (no more raw stream-json)
- **Support for OAuth (Max subscription) AND local Ollama models**
- **Easy switching between cloud and local modes**

## Quick Start

### OAuth Mode (Max Subscription) - macOS

On macOS, use the keychain helper script to extract credentials:

```bash
# Run with current directory as workspace
./scripts/run-with-keychain.sh up ralph

# Run with specific project
WORKSPACE_PATH=/path/to/project ./scripts/run-with-keychain.sh up ralph

# Plan mode, limited iterations
RALPH_MODE=plan RALPH_MAX_ITERATIONS=5 ./scripts/run-with-keychain.sh up ralph
```

The script extracts your Claude credentials from macOS Keychain, makes them available to the container, and automatically cleans them up when finished.

### OAuth Mode (Max Subscription) - Linux/Direct

If credentials are stored in a file (not keychain):

```bash
docker compose up ralph
```

### Ollama Mode (Local Models)

Uses LiteLLM proxy to translate Anthropic API calls to Ollama format.

```bash
# Make sure Ollama is running on your host
ollama serve

# Pull a model if needed
ollama pull qwen2.5-coder:32b

# Run with default model (qwen2.5-coder:32b)
docker compose --profile ollama up ralph-ollama

# Run with different model
RALPH_MODEL=ollama/qwen2.5-coder:7b docker compose --profile ollama up ralph-ollama
```

The `--profile ollama` flag starts both the LiteLLM proxy and ralph-ollama containers.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKSPACE_PATH` | `.` | Project directory to mount |
| `CLAUDE_CONFIG` | `~/.claude` | Claude credentials directory |
| `RALPH_MODE` | `build` | `build` or `plan` |
| `RALPH_MAX_ITERATIONS` | `0` | Max iterations (0=unlimited) |
| `RALPH_MODEL` | `opus` | Model name |
| `RALPH_OUTPUT_FORMAT` | `pretty` | `pretty` or `json` |
| `RALPH_PUSH_AFTER_COMMIT` | `true` | Git push after commits |

### Using .env File

```bash
cp .env.example .env
# Edit .env with your settings
docker compose up ralph
```

## Commands

```bash
# Run the loop (default)
docker compose run --rm ralph loop

# Interactive shell for debugging
docker compose run --rm ralph shell

# Check version
docker compose run --rm ralph version

# Test connectivity
docker compose run --rm ralph test

# Help
docker compose run --rm ralph help
```

## Project Prompts

Ralph uses prompt files to guide its work. You can:

1. **Use default prompts**: Built into the container at `/home/ralph/prompts/`
2. **Use project prompts**: Place `PROMPT_build.md` or `PROMPT_plan.md` in your project root

Project prompts override defaults, allowing customization per project.

## Output Formatting

The container includes two formatters:

- **format-output.sh**: Shell-based, lightweight
- **output-formatter.js**: Node.js-based, richer features (spinners, timing)

Set `RALPH_OUTPUT_FORMAT=json` for raw stream-json output.

## Security

- Runs as non-root user (`ralph`)
- Claude credentials mounted read-only
- Workspace is isolated in `/home/ralph/workspace`
- No network access except Ollama (when using local mode)

## Building

```bash
# Build the image
docker compose build

# Build with no cache
docker compose build --no-cache
```

## LiteLLM Configuration

The `litellm-config.yaml` file defines available Ollama models. Pre-configured models:

- `ollama/qwen2.5-coder:32b` (default)
- `ollama/qwen2.5-coder:14b`
- `ollama/qwen2.5-coder:7b`
- `ollama/deepseek-coder-v2`
- `ollama/codellama:34b`
- `ollama/llama3.1:70b`
- And more...

To use a model, specify it with the `ollama/` prefix:
```bash
RALPH_MODEL=ollama/codellama:13b docker compose --profile ollama up ralph-ollama
```

## Troubleshooting

### OAuth Authentication Failed

```bash
# Verify credentials exist
ls -la ~/.claude/

# Test authentication
docker compose run --rm ralph test
```

### Ollama Connection Failed

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve

# Verify model is available
ollama list
```

### Workspace Not Mounted

```bash
# Check workspace path
docker compose run --rm ralph shell
ls -la /home/ralph/workspace
```

## Using with /ralph Skill

The `/ralph` skill in Claude Code can launch this container:

```
/ralph                              # Build mode, current directory
/ralph --plan                       # Plan mode
/ralph --max 10                     # Max 10 iterations
/ralph --ollama                     # Use local Ollama
/ralph /path/to/project             # Different workspace
```

## Architecture

### OAuth Mode (Cloud)
```
┌─────────────────────────────────────────────────────────┐
│                    ralph container                       │
│  entrypoint.sh → loop.sh → format-output.sh              │
│                      │                                   │
│                      ▼                                   │
│                 Claude CLI                               │
└──────────────────────┼──────────────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Claude API     │
              │  (Anthropic)    │
              └─────────────────┘
```

### Ollama Mode (Local)
```
┌─────────────────────────────────────────────────────────┐
│                 ralph-ollama container                   │
│  entrypoint.sh → loop.sh → format-output.sh              │
│                      │                                   │
│                      ▼                                   │
│                 Claude CLI                               │
│                      │                                   │
│         ANTHROPIC_BASE_URL=http://litellm:4000           │
└──────────────────────┼──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  litellm container                       │
│  Translates Anthropic API → Ollama API                   │
└──────────────────────┼──────────────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Ollama         │
              │  (host machine) │
              └─────────────────┘
```
