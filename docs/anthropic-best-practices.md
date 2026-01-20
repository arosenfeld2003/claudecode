# Anthropic Best Practices for Claude Code

Official guidance from Anthropic engineering for effective Claude Code usage.

## CLAUDE.md Optimization

The `CLAUDE.md` file is loaded at the start of every Claude session. Optimize it for:

### What to Include
- **Bash commands**: Common operations (build, test, lint, deploy)
- **Style guides**: Code conventions, naming patterns
- **Testing instructions**: How to run tests, what framework
- **Architecture overview**: Key directories, module relationships
- **Common gotchas**: Project-specific pitfalls

### What to Avoid
- Lengthy prose (prefer bullet points)
- Information that changes frequently
- Content that duplicates README.md
- Implementation details (Claude can read the code)

### Example Structure
```markdown
# Project Name

## Commands
- Build: `npm run build`
- Test: `npm test`
- Lint: `npm run lint`

## Architecture
- `src/api/` - API endpoints
- `src/models/` - Data models
- `src/utils/` - Shared utilities

## Conventions
- Use TypeScript strict mode
- Prefer async/await over callbacks
- Tests go in `__tests__/` directories
```

## Extended Thinking

Invoke deeper reasoning with progressive keywords:

| Keyword | When to Use |
|---------|-------------|
| "think" | Default reasoning |
| "think hard" | Complex multi-step problems |
| "think harder" | Architectural decisions, debugging |
| "ultrathink" | Maximum reasoning depth |

**Example**:
```
Before implementing authentication, ultrathink about the security
implications and potential edge cases.
```

Extended thinking is particularly useful for:
- Complex debugging scenarios
- Architectural trade-offs
- Security-sensitive code
- Multi-system integration

## Explore-Plan-Code-Commit Workflow

A structured approach for non-trivial tasks:

### 1. Explore
```
First, explore the codebase to understand how authentication
currently works. Look at existing patterns before proposing changes.
```

### 2. Plan
```
Based on your exploration, create a plan for implementing OAuth.
Consider what files need to change and in what order.
```

### 3. Code
```
Implement the plan. Start with the core OAuth flow before
adding the UI components.
```

### 4. Commit
```
Create atomic commits for each logical change. Use conventional
commit messages.
```

This workflow prevents:
- Premature implementation
- Missing edge cases
- Conflicting changes
- Incomplete understanding of existing code

## Test-Driven Development with Agents

TDD works well with Claude agents:

### Write Failing Tests First
```
Write tests for the user registration endpoint. Include:
- Valid registration
- Duplicate email handling
- Invalid input validation
Don't implement the endpoint yet.
```

### Then Implement
```
Now implement the registration endpoint to make all tests pass.
Run tests after each change.
```

### Benefits
- Clear acceptance criteria
- Prevents "cheating" (implementation without verification)
- Provides backpressure for the agent
- Documents expected behavior

## Multi-Agent Patterns

### Parallel Verification

One agent writes, another reviews:
```
# Terminal 1: Implementation agent
claude "Implement the payment processing module"

# Terminal 2: Review agent
claude "Review the payment module for security issues"
```

### Git Worktrees for Concurrent Sessions

Run multiple Claude sessions on different tasks:
```bash
# Create worktrees
git worktree add ../feature-auth feature/auth
git worktree add ../feature-dashboard feature/dashboard

# Run Claude in each
cd ../feature-auth && claude "Implement OAuth"
cd ../feature-dashboard && claude "Add dashboard widgets"
```

Benefits:
- True isolation between tasks
- No context pollution
- Can run in parallel
- Easy to discard failed experiments

### Headless Automation

Use `-p` flag for non-interactive execution:
```bash
cat PROMPT.md | claude -p \
    --dangerously-skip-permissions \
    --output-format=stream-json \
    --model opus
```

Useful for:
- CI/CD pipelines
- Automated code review
- Batch processing
- Ralph loops

## Context Management

### When to Clear Context

Use `/clear` when:
- Switching to unrelated task
- Context feels cluttered
- Agent is going in circles
- Starting fresh iteration

### Course Correction with Escape

Press `Escape` to:
- Interrupt long-running operations
- Redirect agent mid-task
- Provide new instructions
- Abort failed approaches

### Managing Large Codebases

For large projects:
- Focus on specific directories
- Use targeted file reading
- Leverage subagents for exploration
- Keep specs scoped to topics

## Prompt Engineering Tips

### Be Specific
```
# Bad
"Fix the bug"

# Good
"Fix the race condition in UserService.updateProfile()
that causes duplicate database writes when called concurrently"
```

### Provide Context
```
# Bad
"Add tests"

# Good
"Add unit tests for the PaymentProcessor class using Jest.
Follow the existing test patterns in src/__tests__/.
Focus on the processRefund method edge cases."
```

### Set Boundaries
```
# Bad
"Improve the codebase"

# Good
"Refactor the authentication module only.
Don't change the API interface.
Keep all existing tests passing."
```

## Subagent Usage

### When to Use Subagents
- File exploration (many files)
- Parallel searches
- Independent investigations
- Build/test operations

### Subagent Allocation
```
# Many subagents for reads/searches
"Use up to 500 parallel Sonnet subagents for searches"

# Single subagent for builds/tests
"Use only 1 subagent for build/tests"

# Opus for complex reasoning
"Use an Opus subagent for architectural decisions"
```

### Context Efficiency
Each subagent gets fresh context that's garbage collected:
- Use subagents to avoid polluting main context
- Fan out for exploration
- Keep main agent focused on coordination

## Error Handling

### When Agent Gets Stuck
1. **Clear context**: `/clear` and restart with refined prompt
2. **Narrow scope**: Break task into smaller pieces
3. **Provide examples**: Show expected patterns
4. **Add constraints**: Specify what NOT to do

### When Tests Fail
1. Let agent analyze failures first
2. Don't immediately prescribe solution
3. Ask for root cause analysis
4. Trust iterative fixing

### When Plan Goes Wrong
1. Regenerate plan (it's disposable)
2. Update specs if requirements unclear
3. Add guardrails to prompts
4. Consider scope reduction

## Security Considerations

### Credential Management
- Never hardcode secrets
- Use environment variables
- Leverage secret managers
- Audit agent access to credentials

### Code Review
- Review security-sensitive changes manually
- Use parallel verification pattern
- Run security linters
- Check for common vulnerabilities (OWASP)

### Sandboxing
- Use Docker/E2B for untrusted code
- Limit network access where possible
- Provide minimum viable credentials
- Monitor for unexpected behavior

## Further Reading

- [Anthropic Documentation](https://docs.anthropic.com/)
- [Claude Code CLI Reference](https://docs.anthropic.com/claude-code)
- [Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)
