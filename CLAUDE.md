# Agentic Development Optimization

This repository contains patterns, templates, and documentation for atomic control and oversight when managing Claude agents. It synthesizes Geoff Huntley's Ralph Wiggum methodology with Anthropic's official best practices.

## Repository Structure

```
claudecode/
├── CLAUDE.md                    # This file - loaded every Claude session
├── ralph-playbook/              # Full reference copy from how-to-ralph-wiggum
│   ├── README.md                # Comprehensive Ralph methodology guide
│   ├── files/                   # Original prompt templates and loop.sh
│   └── references/              # Sandbox environment documentation
├── docs/
│   ├── ralph-wiggum-methodology.md   # Synthesized Ralph workflow guide
│   ├── anthropic-best-practices.md   # Official Anthropic guidance
│   ├── oversight-and-control.md      # Atomic control patterns
│   └── open-source-models.md         # Local model setup guide
├── templates/                   # Ready-to-use customizable files
│   ├── PROMPT_plan.md           # Planning mode prompt
│   ├── PROMPT_build.md          # Building mode prompt
│   ├── AGENTS.md                # Operational guide template
│   └── loop.sh                  # Enhanced Ralph loop script
├── scripts/                     # Automation scripts
│   ├── setup-ollama.sh          # Ollama + model setup
│   └── evaluate-models.sh       # Model comparison runner
└── specs/                       # Your requirement specs go here
```

## Quick Reference: Ralph Wiggum Workflow

### Core Loop
```bash
while :; do cat PROMPT.md | claude ; done
```

### Three Phases
1. **Define Requirements**: JTBD → Topics of Concern → `specs/*.md`
2. **Planning Loop**: Gap analysis → `IMPLEMENTATION_PLAN.md`
3. **Building Loop**: Implement → Test → Commit → Repeat

### Run Commands
```bash
./templates/loop.sh              # Build mode, unlimited
./templates/loop.sh 20           # Build mode, max 20 iterations
./templates/loop.sh plan         # Plan mode, unlimited
./templates/loop.sh plan 5       # Plan mode, max 5 iterations

# Local models via Ollama
./templates/loop.sh --local qwen2.5-coder:32b  # Build with local model
./templates/loop.sh plan --local qwen2.5-coder:7b  # Plan with local model
```

## Key Principles

### Context Management
- 40-60% context utilization is the "smart zone"
- Use main agent as scheduler, spawn subagents for work
- Each loop iteration gets fresh context
- `/clear` frequently in interactive sessions

### Steering: Patterns + Backpressure
- **Upstream**: Prompt guardrails, AGENTS.md, code patterns
- **Downstream**: Tests, typechecks, lints, builds that reject invalid work
- Backpressure commands defined in AGENTS.md per project

### Oversight Philosophy
- "It's not if it gets popped, it's when. What's the blast radius?"
- Run in sandboxed environments (Docker, E2B, Sprites)
- Minimum viable access: only required credentials
- Escape hatches: Ctrl+C, `git reset --hard`, regenerate plan

### Let Ralph Ralph
- Trust iteration for eventual consistency
- Plan is disposable - regenerate when stale
- Don't prescribe implementation details
- Observe failures, add signs to guide next iteration

## Extended Thinking Triggers
Use these keywords to invoke deeper reasoning:
- "think" < "think hard" < "think harder" < "ultrathink"

## File Roles

| File | Purpose |
|------|---------|
| `specs/*.md` | Source of truth for requirements (one per topic) |
| `IMPLEMENTATION_PLAN.md` | Prioritized task list (generated/updated by Ralph) |
| `AGENTS.md` | Operational guide: build/test commands, patterns |
| `PROMPT_plan.md` | Instructions for planning mode |
| `PROMPT_build.md` | Instructions for building mode |

## Local Models (Ollama)

Use local open source models via Ollama as alternatives to Claude Code:

```bash
# Setup
./scripts/setup-ollama.sh

# Use with Ralph loop
./templates/loop.sh --local qwen2.5-coder:32b
./templates/loop.sh plan --local qwen2.5-coder:7b

# Direct Claude Code usage
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_BASE_URL=http://localhost:11434
claude --model qwen2.5-coder:32b
```

### Recommended Models (48GB Mac)

| Model | Memory | Best For |
|-------|--------|----------|
| Qwen2.5 Coder 32B | ~20GB | Max coding power, complex tasks |
| Qwen2.5 Coder 7B | ~4GB | Fast iterations |
| DeepSeek Coder V2 | ~15GB | Multi-language support |

> **Note**: Some Ollama models like `minimax-m2.1:cloud` are cloud-proxied (not truly local). They cost money per token and send data to external servers. The models above run entirely on your machine.

See `docs/open-source-models.md` for full setup and evaluation guide.

## See Also
- `docs/ralph-wiggum-methodology.md` - Full methodology details
- `docs/anthropic-best-practices.md` - Official Anthropic guidance
- `docs/oversight-and-control.md` - Sandbox setup, escape hatches
- `docs/open-source-models.md` - Local model setup and evaluation
- `ralph-playbook/README.md` - Original comprehensive reference
