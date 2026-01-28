# Feature: Custom Skills

## Overview

Create and deploy custom skills that extend Clawdbot's capabilities. Skills are reusable automation workflows with guardrails and documentation.

## Jobs To Be Done

1. Developer can create a new skill from a template
2. Developer can define skill triggers (commands, patterns, events)
3. Developer can set guardrails (confirmations, rate limits, scope restrictions)
4. Developer can test a skill locally before deployment
5. Developer can share skills via ClawdHub marketplace

## Acceptance Criteria

- [ ] Skill responds to its defined trigger phrase
- [ ] Skill executes its automation steps in sequence
- [ ] Guardrails block unauthorized or dangerous actions
- [ ] Skill errors are logged with actionable messages
- [ ] Skill can be enabled/disabled without code changes

## Constraints

- Skills must declare required permissions upfront
- Skills must not bypass user confirmation for destructive actions
- Skills should fail gracefully when dependencies are unavailable

## Out of Scope

- Building a skill marketplace (use ClawdHub)
- Multi-tenant skill isolation
- Skill versioning and rollback

## Experiment Ideas

1. **Daily briefing skill**: Aggregate calendar, weather, and task list each morning
2. **GitHub PR notifier**: Alert on PR reviews and CI failures
3. **Smart home control**: Toggle lights/scenes via chat commands
4. **Expense tracker**: Parse receipts from photos, log to spreadsheet

## References

- Skills docs: https://docs.molt.bot/tools/skills
- Skills config: https://docs.molt.bot/tools/skills-config
