# Agentic Development with Claude Code

Patterns and templates for running Claude Code in autonomous loops, based on Geoff Huntley's "Ralph Wiggum" methodology combined with Anthropic best practices.

## What This Is

A toolkit for letting Claude Code work autonomously on your codebase:
- **Plan mode**: Claude analyzes specs and creates an implementation plan
- **Build mode**: Claude implements, tests, commits, and iterates until done
- **Local models**: Optional support for running open source models via Ollama

## Core Principle: Bash Controls Claude

**This is the most important concept to understand.**

There are two ways to run autonomous AI coding loops:

```
CORRECT (this repo):              WRONG (plugin approach):
┌─────────────────────┐           ┌─────────────────────┐
│  Bash loop (loop.sh)│           │  Claude Code        │
│         │           │           │         │           │
│         ▼           │           │         ▼           │
│  spawns Claude      │           │  internal plugin    │
│  fresh each time    │           │  prevents completion│
└─────────────────────┘           └─────────────────────┘
```

**Why this matters:**

- **Context windows are arrays** - every message adds to them, and eventually they compress/compact, losing data
- **Plugin loops don't solve context rot** - Claude stays running with the same context, just working longer
- **External bash loops give fresh context** - each iteration spawns a new Claude instance with clean state

**How we implement it:**

```bash
# loop.sh spawns Claude as a child process
while true; do
    cat PROMPT.md | claude -p --dangerously-skip-permissions
done
```

Each iteration: fresh Claude → does one task → commits → exits → bash spawns fresh Claude again.

The plan and progress persist in files (`IMPLEMENTATION_PLAN.md`), not in Claude's context.

## Quick Start

```bash
# Copy templates to your project
cp templates/PROMPT_plan.md templates/PROMPT_build.md templates/loop.sh your-project/

# Edit PROMPT_plan.md - set your project goal
# Edit PROMPT_build.md - adjust paths to match your project

# Run planning (creates IMPLEMENTATION_PLAN.md)
./loop.sh plan 5

# Run building (implements the plan)
./loop.sh 20
```

## Repository Structure

```
├── templates/           # Copy these to your project
│   ├── loop.sh          # Main loop script
│   ├── PROMPT_plan.md   # Planning mode instructions
│   ├── PROMPT_build.md  # Building mode instructions
│   └── AGENTS.md        # Operational guide template
├── docs/                # Reference documentation
│   ├── ralph-wiggum-methodology.md
│   ├── anthropic-best-practices.md
│   ├── oversight-and-control.md
│   └── open-source-models.md
├── scripts/             # Setup automation
│   ├── setup-ollama.sh  # Local model setup
│   └── evaluate-models.sh
├── ralph-playbook/      # Original methodology reference
└── specs/               # Example specs directory
```

## Usage

### Basic Commands

```bash
./loop.sh              # Build mode, runs until stopped (Ctrl+C)
./loop.sh 20           # Build mode, max 20 iterations
./loop.sh plan         # Plan mode, runs until stopped
./loop.sh plan 5       # Plan mode, max 5 iterations
```

### With Local Models (Ollama)

```bash
# Setup once
./scripts/setup-ollama.sh

# Use local models
./loop.sh --local qwen2.5-coder:32b
./loop.sh plan --local qwen2.5-coder:7b
```

## How It Works

1. **You define specs** in `specs/*.md` describing what you want built
2. **Plan mode** reads specs, analyzes your codebase, creates `IMPLEMENTATION_PLAN.md`
3. **Build mode** works through the plan: implement → test → commit → repeat
4. **Each loop iteration** gets fresh context, preventing context exhaustion

The loop runs Claude in headless mode (`-p`) with auto-approved tool calls. Each iteration pushes to git, creating checkpoints you can roll back to.

## Key Files in Your Project

| File | Purpose |
|------|---------|
| `specs/*.md` | Your requirements (source of truth) |
| `IMPLEMENTATION_PLAN.md` | Task list (generated/updated by Claude) |
| `AGENTS.md` | Build commands, test commands, project patterns |
| `PROMPT_plan.md` | Instructions for planning mode |
| `PROMPT_build.md` | Instructions for building mode |

## Safety

- Run in a sandbox (Docker, VM) for untrusted codebases
- Git provides rollback: `git reset --hard HEAD~1`
- Stop anytime with Ctrl+C
- Review commits before pushing to shared branches

## Documentation

- [`docs/ralph-wiggum-methodology.md`](docs/ralph-wiggum-methodology.md) - Full methodology explanation
- [`docs/anthropic-best-practices.md`](docs/anthropic-best-practices.md) - Official Anthropic guidance
- [`docs/open-source-models.md`](docs/open-source-models.md) - Local model setup
- [`ralph-playbook/README.md`](ralph-playbook/README.md) - Original reference material

## Credits

- [Geoff Huntley](https://ghuntley.com) - Ralph Wiggum methodology
- [Alex Dunlop](https://medium.com/@alexjamesdunlop) - ["Everyone's Using Ralph Loops Wrong"](https://medium.com/@alexjamesdunlop/everyones-using-ralph-loops-wrong-here-s-what-actually-works-e5e4208873c1) article explaining the bash-controls-Claude principle
- [Anthropic](https://anthropic.com) - Claude Code and best practices documentation
