# Ralph Wiggum Methodology

Synthesized from Geoff Huntley's [Ralph Playbook](https://ghuntley.com/ralph/) and the [how-to-ralph-wiggum](https://github.com/ClaytonFarr/how-to-ralph-wiggum) repository.

## The Core Loop

At its simplest, Ralph is a bash loop that repeatedly feeds a prompt to Claude:

```bash
while :; do cat PROMPT.md | claude ; done
```

The power comes from how context is managed: each iteration starts fresh, reads the current state from disk, does one task, commits, and exits. The plan file (`IMPLEMENTATION_PLAN.md`) persists between iterations as shared state.

## Three Phases, Two Prompts, One Loop

### Phase 1: Define Requirements (Human + LLM Conversation)

1. Discuss project ideas, identify Jobs to Be Done (JTBD)
2. Break each JTBD into topics of concern
3. Use subagents to load info from URLs into context
4. Write `specs/FILENAME.md` for each topic

**Topic Scope Test**: Can you describe the topic in one sentence without "and"?
- "The color extraction system analyzes images to identify dominant colors" (one topic)
- "The user system handles authentication, profiles, and billing" (three topics)

### Phase 2: Planning Loop

**Prompt**: `PROMPT_plan.md`
**Output**: Creates/updates `IMPLEMENTATION_PLAN.md`

1. Subagents study `specs/*` and existing code
2. Compare specs against code (gap analysis)
3. Create prioritized task list
4. No implementation - plan only

### Phase 3: Building Loop

**Prompt**: `PROMPT_build.md`
**Output**: Implemented code, updated plan, commits

Each iteration:
1. **Orient** - Study specs
2. **Read plan** - Study `IMPLEMENTATION_PLAN.md`
3. **Select** - Pick the most important task
4. **Investigate** - Search codebase ("don't assume not implemented")
5. **Implement** - Use subagents for file operations
6. **Validate** - Run tests (backpressure)
7. **Update plan** - Mark done, note discoveries
8. **Update AGENTS.md** - If operational learnings
9. **Commit**
10. **Loop ends** - Context cleared, next iteration starts fresh

## Key Principles

### Context Is Everything

- ~176K tokens truly usable (not the advertised 200K+)
- 40-60% context utilization is the "smart zone"
- Tight tasks + 1 task per loop = 100% smart zone utilization

**Implications**:
- Use main agent as scheduler, spawn subagents for work
- Each subagent gets ~156kb that's garbage collected
- Simplicity and brevity win - verbose inputs degrade determinism
- Prefer Markdown over JSON for better token efficiency

### Steering: Patterns + Backpressure

Steer from two directions:

**Upstream (Inputs)**:
- Deterministic setup: same files loaded each iteration
- Prompt guardrails (explicit instructions)
- `AGENTS.md` (operational knowledge)
- Code patterns in your codebase (Ralph discovers and follows)

**Downstream (Validation)**:
- Tests, typechecks, lints, builds reject invalid work
- `AGENTS.md` specifies actual commands per project
- LLM-as-judge tests for subjective criteria (tone, aesthetics)

### Let Ralph Ralph

Trust iteration for eventual consistency:
- Lean into LLM's ability to self-identify, self-correct, self-improve
- Eventual consistency achieved through iteration
- The plan is disposable - regenerate when wrong/stale

**Regenerate plan when**:
- Ralph is implementing wrong things or duplicating work
- Plan feels stale or doesn't match current state
- Too much clutter from completed items
- Significant spec changes
- Confused about what's actually done

### Move Outside the Loop

Your job is to sit *on* the loop, not *in* it:
- Observe and course correct, especially early on
- When Ralph fails a specific way, add a sign to help next time
- Signs aren't just prompt text - they're anything Ralph can discover

## File Roles

| File | Purpose | Who Creates | When Updated |
|------|---------|-------------|--------------|
| `specs/*.md` | Requirements (one per topic) | Human + LLM | Rare (if inconsistencies) |
| `IMPLEMENTATION_PLAN.md` | Prioritized task list | Planning loop | Every build iteration |
| `AGENTS.md` | Operational guide | Human initially | When learnings discovered |
| `PROMPT_plan.md` | Planning instructions | Human | When tuning needed |
| `PROMPT_build.md` | Building instructions | Human | When tuning needed |

### AGENTS.md Guidelines

The "heart of the loop" - a concise operational guide:
- **Is**: How to build/run, validation commands, codebase patterns
- **Is Not**: A changelog or progress diary
- Keep brief (~60 lines)
- Status and progress belong in `IMPLEMENTATION_PLAN.md`

### specs/* Guidelines

One markdown file per topic of concern:
- Source of truth for what should be built
- Created during Phase 1 (requirements)
- No pre-specified template - let Ralph dictate format

## JTBD Breakdown

```
Job to Be Done (JTBD)
    └── Topic of Concern (1:many)
            └── Spec file (1:1)
                    └── Tasks (1:many)
```

**Example**:
- JTBD: "Help designers create mood boards"
- Topics: image collection, color extraction, layout, sharing
- Each topic → one spec file
- Each spec → many tasks in implementation plan

## Loop Mechanics

### Outer Loop (Bash)

Controls iteration count and mode selection:

```bash
./loop.sh              # Build mode, unlimited
./loop.sh 20           # Build mode, max 20 iterations
./loop.sh plan         # Plan mode, unlimited
./loop.sh plan 5       # Plan mode, max 5 iterations
```

### Inner Loop (Task Execution)

No hard technical limit. Control relies on:
- **Scope discipline**: Prompt says "one task" and "commit when tests pass"
- **Backpressure**: Test failures force fixes before committing
- **Natural completion**: Agent exits after successful commit

### Continuation Mechanism

1. Bash loop feeds `PROMPT.md` to claude
2. Prompt instructs: "Study IMPLEMENTATION_PLAN.md and choose most important thing"
3. Agent completes one task, updates plan, commits, exits
4. Bash loop restarts immediately with fresh context
5. Agent reads updated plan, picks next task

No sophisticated orchestration - just a dumb bash loop. The agent figures out what to do by reading the plan file each time.

## Key Language Patterns

Geoff's specific phrasing (use these in prompts):
- "study" (not "read" or "look at")
- "don't assume not implemented" (critical)
- "using parallel subagents" / "up to N subagents"
- "only 1 subagent for build/tests"
- "Ultrathink" (extended thinking trigger)
- "capture the why"
- "keep it up to date"
- "resolve them or document them"

## Guardrail Numbering

In `PROMPT_build.md`, guardrails use escalating 9s:
```
99999. When authoring documentation, capture the why...
999999. Single sources of truth, no migrations/adapters...
9999999. Create git tags when no errors...
```

Higher numbers = more critical invariants.

## Further Reading

- `ralph-playbook/README.md` - Full original documentation
- `ralph-playbook/references/sandbox-environments.md` - Sandbox options
- Original blog post: https://ghuntley.com/ralph/
