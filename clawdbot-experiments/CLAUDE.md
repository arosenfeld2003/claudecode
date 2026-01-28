# Clawdbot Experiments

Personal AI assistant experimentation using Clawdbot/Moltbot - an open-source local agent with messaging integrations.

## Stack

- Runtime: Node.js (pnpm)
- Config: `~/.clawdbot/moltbot.json`
- LLM: Claude (primary), OpenAI, or local models
- Platforms: WhatsApp, Telegram, Discord, iMessage

## Structure

- `specs/` - Experiment requirements and acceptance criteria
- `skills/` - Custom skill implementations
- `scripts/` - Automation and setup helpers

## Commands

- `clawdbot onboard` - Initial setup wizard
- `clawdbot gateway` - Start the main service
- `clawdbot channels login` - Pair messaging platforms
- `clawdbot doctor` - Diagnose configuration issues
- `moltbot message send --target <phone> --message "text"` - Test messaging

## Key Paths

- Config: `~/.clawdbot/moltbot.json`
- Logs: Check gateway output for debugging
- Skills: See Clawdbot docs for skill directory location

## Documentation

- Official docs: https://docs.molt.bot
- Skills guide: see `specs/custom-skills.md`
- Integration setup: see `specs/messaging-setup.md`
