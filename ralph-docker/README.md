# Ralph Docker

Containerized Ralph Loop for secure, headless autonomous development.

## Overview

This container runs the Ralph Wiggum methodology in a Docker environment, providing:

- **Security isolation** via containerization
- **Human-readable output** (no more raw stream-json)
- **Support for OAuth (Max subscription) AND local Ollama models**
- **Easy switching between cloud and local modes**

## Quick Start

### OAuth Mode (Max Subscription)

```bash
# Run with current directory as workspace
docker compose up ralph

# Run with specific project
WORKSPACE_PATH=/path/to/project docker compose up ralph

# Plan mode, limited iterations
RALPH_MODE=plan RALPH_MAX_ITERATIONS=5 docker compose up ralph
```

### Ollama Mode (Local Models)

```bash
# Make sure Ollama is running on your host
ollama serve

# Run with default model (qwen2.5-coder:32b)
docker compose --profile ollama up ralph-ollama

# Run with different model
RALPH_MODEL=qwen2.5-coder:7b docker compose --profile ollama up ralph-ollama
```

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

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                     entrypoint.sh                    │ │
│  │  - Auth detection                                    │ │
│  │  - Command routing                                   │ │
│  │  - Environment setup                                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                           │                              │
│                           ▼                              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                      loop.sh                         │ │
│  │  - Iteration management                              │ │
│  │  - Claude CLI invocation                             │ │
│  │  - Git operations                                    │ │
│  └─────────────────────────────────────────────────────┘ │
│                           │                              │
│                           ▼                              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              format-output.sh / .js                  │ │
│  │  - stream-json parsing                               │ │
│  │  - Human-readable formatting                         │ │
│  │  - Color coding                                      │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
          │                                    │
          ▼                                    ▼
    ┌───────────┐                      ┌───────────────┐
    │ Workspace │                      │ Claude API /  │
    │ (mounted) │                      │ Ollama        │
    └───────────┘                      └───────────────┘
```
