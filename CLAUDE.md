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
│   └── oversight-and-control.md      # Atomic control patterns
├── templates/                   # Ready-to-use customizable files
│   ├── PROMPT_plan.md           # Planning mode prompt
│   ├── PROMPT_build.md          # Building mode prompt
│   ├── AGENTS.md                # Operational guide template
│   └── loop.sh                  # Enhanced Ralph loop script
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

## See Also
- `docs/ralph-wiggum-methodology.md` - Full methodology details
- `docs/anthropic-best-practices.md` - Official Anthropic guidance
- `docs/oversight-and-control.md` - Sandbox setup, escape hatches
- `ralph-playbook/README.md` - Original comprehensive reference
