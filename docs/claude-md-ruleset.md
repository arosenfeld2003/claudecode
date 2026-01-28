# Ruleset for Constructing CLAUDE.md Files and Specs

A distilled guide for writing effective CLAUDE.md files and specification documents for agentic projects. Based on [HumanLayer's research](https://www.humanlayer.dev/blog/writing-a-good-claude-md) and practical experience.

---

## Core Principle: Stateless Context

LLMs have no memory between sessions. `CLAUDE.md` is the **only file automatically included** in every conversation. Treat it as your sole mechanism for onboarding Claude to your codebase.

---

## The WHAT-WHY-HOW Framework

Every CLAUDE.md should cover three dimensions:

| Dimension | Content | Example |
|-----------|---------|---------|
| **WHAT** | Tech stack, project structure, codebase organization | "This is a Next.js 14 app with Prisma ORM and PostgreSQL" |
| **WHY** | Project purpose, component functions | "The `/api/webhooks` directory handles Stripe payment events" |
| **HOW** | Build commands, test procedures, verification | "Run `pnpm test` before committing. CI requires all tests pass." |

For monorepos, explicitly explain what each app and shared package does.

---

## Rules for CLAUDE.md

### Rule 1: Less is More

**Target: Under 300 lines. Ideal: Under 60 lines.**

Research shows frontier LLMs reliably follow 150-200 instructions. Claude Code's system prompt already consumes ~50. Every instruction you add competes for attention.

```
BAD:  500-line file covering every edge case
GOOD: 50-line file with universal truths only
```

### Rule 2: Universal Applicability Only

Every line must apply to **most sessions**, not specific tasks.

```
BAD:  "When designing database schemas, use UUIDs for primary keys"
GOOD: "This project uses PostgreSQL with Prisma. Schema at prisma/schema.prisma"
```

Ask yourself: "Does this apply to someone fixing a typo in the README?" If not, it doesn't belong in the root CLAUDE.md.

### Rule 3: Progressive Disclosure

Create separate markdown files for task-specific instructions:

```
agent_docs/
├── building.md          # Build and deployment procedures
├── testing.md           # Test patterns and commands
├── conventions.md       # Code conventions (if complex)
├── architecture.md      # System design decisions
└── troubleshooting.md   # Common issues and solutions
```

Reference from CLAUDE.md:
```markdown
## Documentation
- Build/deploy: see `agent_docs/building.md`
- Testing patterns: see `agent_docs/testing.md`
```

Claude will read these when relevant. You don't need to force everything into one file.

### Rule 4: No Code Style in CLAUDE.md

**Never include formatting or style guidelines.** LLMs are expensive, slow linters.

```
BAD:
- Use 2-space indentation
- Prefer single quotes
- Add trailing commas

GOOD:
- Run `pnpm lint` before committing
- Formatter: Biome (runs on save)
```

Use deterministic tools (Biome, ESLint, Prettier) and hook them into your workflow.

### Rule 5: No Auto-Generation

Never use `/init` or auto-generation tools for CLAUDE.md. This file is your highest-leverage configuration point. Craft every line deliberately.

### Rule 6: Pointers Over Copies

Reference code locations, don't copy code snippets.

```
BAD:
Here's how our auth middleware works:
[50 lines of code]

GOOD:
Auth middleware: `src/middleware/auth.ts:15-45`
```

### Rule 7: State Facts, Not Preferences

```
BAD:  "I prefer functional components over class components"
GOOD: "This codebase uses functional React components exclusively"
```

---

## Rules for Spec Files

Specs live in `specs/` and define requirements. One file per topic of concern.

### Rule 8: Jobs-To-Be-Done Format

Structure specs around what users need to accomplish:

```markdown
# Feature: User Authentication

## Jobs To Be Done
1. User can sign up with email/password
2. User can log in and receive a session
3. User can reset forgotten password
4. Admin can revoke user sessions

## Constraints
- Passwords: bcrypt, min 12 chars
- Sessions: JWT, 24h expiry
- Rate limit: 5 attempts per minute

## Out of Scope
- Social OAuth (future iteration)
- MFA (future iteration)
```

### Rule 9: Testable Acceptance Criteria

Every requirement should be verifiable:

```
BAD:  "Authentication should be secure"
GOOD: "Failed login attempts are rate-limited to 5/minute per IP"
```

### Rule 10: Constraints Over Implementation

Specify boundaries, not solutions:

```
BAD:  "Use Redis for session storage with a 24-hour TTL"
GOOD: "Sessions must expire after 24 hours of inactivity"
```

Let the agent choose implementation within constraints.

### Rule 11: Explicit Non-Goals

State what's out of scope to prevent scope creep:

```markdown
## Out of Scope
- Mobile app support
- Offline functionality
- Multi-tenancy
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Fix |
|--------------|--------------|-----|
| Kitchen-sink CLAUDE.md | Instruction overload degrades all compliance | Ruthlessly prune to universals |
| Code snippets in docs | Stale immediately, wastes context | Use `file:line` pointers |
| Style guides in CLAUDE.md | LLMs are bad linters | Use actual linters |
| Task-specific instructions | Irrelevant content harms performance | Use progressive disclosure |
| Vague requirements | Unverifiable, leads to rework | Write testable acceptance criteria |
| Implementation prescriptions | Blocks agent creativity | Specify constraints only |

---

## Template: Minimal CLAUDE.md

```markdown
# Project Name

Brief description of what this project does.

## Stack
- Framework: [e.g., Next.js 14]
- Database: [e.g., PostgreSQL + Prisma]
- Auth: [e.g., NextAuth.js]

## Structure
- `src/app/` - Next.js app router pages
- `src/lib/` - Shared utilities
- `prisma/` - Database schema and migrations

## Commands
- `pnpm dev` - Start development server
- `pnpm test` - Run tests (required before commit)
- `pnpm lint` - Run linter

## Key Files
- API routes: `src/app/api/`
- Database schema: `prisma/schema.prisma`
- Environment template: `.env.example`

## Documentation
See `agent_docs/` for detailed guides on specific topics.
```

---

## Template: Spec File

```markdown
# Feature: [Name]

## Overview
One paragraph explaining the feature's purpose.

## Jobs To Be Done
1. [Actor] can [action] to [outcome]
2. [Actor] can [action] to [outcome]

## Acceptance Criteria
- [ ] [Testable criterion]
- [ ] [Testable criterion]

## Constraints
- [Technical constraint]
- [Business constraint]

## Out of Scope
- [Explicit non-goal]

## References
- Related spec: `specs/related-feature.md`
- Design doc: `docs/architecture.md`
```

---

## Checklist Before Committing CLAUDE.md

- [ ] Under 300 lines (ideally under 100)
- [ ] Every instruction applies to most sessions
- [ ] No code style/formatting rules
- [ ] No copied code snippets
- [ ] Uses pointers (`file:line`) for specifics
- [ ] Task-specific content moved to separate docs
- [ ] Commands are copy-pasteable
- [ ] Written deliberately, not auto-generated
