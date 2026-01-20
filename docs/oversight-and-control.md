# Oversight and Control

Patterns for atomic control when letting agents work autonomously.

## Philosophy

> "It's not if it gets popped, it's when. What's the blast radius?"

Autonomous agents require `--dangerously-skip-permissions` which bypasses Claude's permission system entirely. The sandbox becomes your only security boundary. Design for failure containment, not failure prevention.

**Principles**:
- Assume the agent will eventually do something unexpected
- Limit the blast radius of unexpected behavior
- Make it easy to stop, revert, and restart
- Provide validation gates that catch problems early

## Local Docker Setup

Docker sandboxes are the recommended option for local development.

### Quick Start

```bash
# Basic usage
docker sandbox run claude

# With custom workspace
docker sandbox run -w ~/my-project claude

# With initial prompt
docker sandbox run claude "implement the auth module"

# Continue last session
docker sandbox run claude -c
```

### What's Included

The base image provides:
- Node.js, Python 3, Go
- Git, Docker CLI, GitHub CLI
- ripgrep, jq
- Non-root user with sudo access

### Credential Management

Credentials are stored in a persistent volume: `docker-claude-sandbox-data`

```bash
# The volume persists between sessions
# First run: authenticate once
# Subsequent runs: credentials are available

# To reset credentials:
docker volume rm docker-claude-sandbox-data
```

### Network Isolation Options

```bash
# Full network access (default)
docker sandbox run claude

# Limited network (custom Dockerfile)
# See Docker documentation for network policies
```

### Running the Ralph Loop

```bash
# Start sandbox
docker sandbox run -w ~/my-project claude

# Inside sandbox, run the loop
./loop.sh plan 5      # Planning
./loop.sh 20          # Building
```

## Backpressure Mechanisms

Backpressure creates validation gates that reject invalid work. Without backpressure, the agent can claim tasks are "done" without verification.

### Programmatic Backpressure

Defined in `AGENTS.md` per project:

```markdown
## Validation

Run these after implementing:

- Tests: `npm test`
- Typecheck: `npm run typecheck`
- Lint: `npm run lint`
- Build: `npm run build`
```

The prompt instructs "run tests" generically; `AGENTS.md` specifies actual commands.

### Types of Backpressure

| Type | What It Catches |
|------|-----------------|
| Unit tests | Logic errors, regressions |
| Type checks | Type mismatches, missing properties |
| Lints | Style violations, potential bugs |
| Builds | Compilation errors, missing deps |
| Integration tests | System interaction failures |
| E2E tests | User-facing regressions |

### LLM-as-Judge (Non-Deterministic)

For criteria that resist programmatic validation:
- Creative quality (tone, narrative)
- Aesthetic judgments (visual harmony)
- UX quality (intuitive navigation)

```typescript
// Example: Binary pass/fail LLM review
const result = await createReview({
  criteria: "Message uses warm, conversational tone",
  artifact: message,
});
expect(result.pass).toBe(true);
```

Non-deterministic backpressure aligns with Ralph philosophy: "deterministically bad in an undeterministic world." Loop until pass.

## Steering

### Upstream Steering (Inputs)

Control what the agent sees at the start of each iteration:

**Prompt Guardrails**:
```markdown
IMPORTANT: Do NOT assume functionality is missing.
Search the codebase first to confirm.
```

**AGENTS.md Patterns**:
```markdown
## Codebase Patterns

- API routes follow REST conventions in `src/api/`
- Use the ErrorHandler utility for consistent error responses
- Database operations go through the Repository pattern
```

**Code as Signs**:
When Ralph generates wrong patterns, add/update utilities and code patterns. Ralph discovers and follows existing patterns.

### Downstream Steering (Validation)

Create gates that reject invalid work:

```markdown
# In PROMPT_build.md

4. When the tests pass, update @IMPLEMENTATION_PLAN.md,
   then `git add -A` then `git commit`...

# Tests MUST pass before commit
```

## Escape Hatches

When things go wrong, you need quick recovery options:

### Stop the Loop

```bash
# Ctrl+C stops the current iteration
^C

# The loop script exits
# Changes since last commit are in working directory
```

### Revert Changes

```bash
# Discard all uncommitted changes
git reset --hard

# Revert to specific commit
git reset --hard <commit-sha>

# Undo last commit (keep changes)
git reset --soft HEAD~1
```

### Regenerate Plan

When the plan is wrong or stale:
```bash
# Delete current plan
rm IMPLEMENTATION_PLAN.md

# Run planning loop
./loop.sh plan 5
```

Regeneration cost is one planning loop - cheap compared to Ralph going in circles.

### Start Fresh

```bash
# Clear everything and restart
git reset --hard
rm IMPLEMENTATION_PLAN.md
./loop.sh plan
```

## Multi-Agent Oversight

### Git Worktrees for Isolation

Each Claude session gets its own working directory:

```bash
# Create worktrees for parallel work
git worktree add ../feature-a feature/auth
git worktree add ../feature-b feature/dashboard

# Run independent Claude sessions
# Terminal 1:
cd ../feature-a && ./loop.sh 20

# Terminal 2:
cd ../feature-b && ./loop.sh 20

# Each worktree is fully isolated
# No context pollution between sessions
```

### Branch-per-Task Pattern

```bash
# Main has the full plan
git checkout main
./loop.sh plan

# Create scoped branch
git checkout -b ralph/user-auth

# Run scoped planning
./loop.sh plan-work "user authentication with OAuth"

# Build on branch
./loop.sh 20

# PR when done
gh pr create --base main
```

### PR-Based Review Gates

Before merging Ralph's work:

1. **Automated checks**: CI runs tests, lints, security scans
2. **Human review**: Inspect changes for quality, security
3. **Parallel verification**: Second Claude session reviews
4. **Staged rollout**: Merge to staging before production

```bash
# Create PR
gh pr create --base main --title "Add OAuth authentication"

# CI runs automatically
# Human reviews diff
# Merge when satisfied
```

## Monitoring

### Watch the Loop

Especially early on, observe Ralph's behavior:
- What patterns emerge?
- Where does it go wrong?
- What signs does it need?

The prompts you start with won't be the prompts you end with.

### Iteration Limits

Use max iterations to bound autonomous work:

```bash
# Limited iterations
./loop.sh 20  # Max 20 iterations, then stop

# Unlimited (manual stop)
./loop.sh     # Run until Ctrl+C
```

### Output Logging

```bash
# JSON output for structured logging
cat PROMPT.md | claude -p \
    --output-format=stream-json \
    --verbose \
    | tee ralph.log
```

## Recovery Patterns

### Agent Going in Circles

Symptoms: Same task keeps appearing, no progress

Solutions:
1. Regenerate plan
2. Add more specific guardrails
3. Break task into smaller pieces
4. Check if tests are flaky

### Agent Implementing Wrong Thing

Symptoms: Code doesn't match specs, wrong approach

Solutions:
1. Stop loop (Ctrl+C)
2. Revert changes (`git reset --hard`)
3. Update specs for clarity
4. Add explicit constraints to prompt
5. Regenerate plan

### Agent Breaking Existing Code

Symptoms: Previously passing tests now fail

Solutions:
1. Stop loop
2. Review the failing tests
3. Revert to last known good commit
4. Add guardrail: "If tests unrelated to your work fail, resolve them"

### Context Exhaustion

Symptoms: Agent seems confused, repeating itself

Solutions:
1. Loop iteration clears context automatically
2. For interactive: `/clear`
3. Break large tasks into smaller iterations

## Security Checklist

Before running autonomous agents:

- [ ] Running in sandbox (Docker/E2B/Sprites)
- [ ] Only required credentials provided
- [ ] Network restricted if possible
- [ ] Git remote set up for recovery
- [ ] Iteration limits configured
- [ ] Human available for monitoring
- [ ] CI/CD gates in place for PRs
- [ ] No access to production data/systems

## Further Reading

- `ralph-playbook/references/sandbox-environments.md` - Detailed sandbox comparison
- [Docker Sandbox Docs](https://docs.docker.com/ai/sandboxes/claude-code/)
- [E2B Documentation](https://e2b.dev/docs)
- [Sprites Documentation](https://docs.sprites.dev/)
