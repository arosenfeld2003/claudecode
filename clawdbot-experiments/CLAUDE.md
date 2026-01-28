# Clawdbot Experiments

Personal AI assistant experimentation using Clawdbot/Moltbot - an open-source local agent with messaging integrations.

## Stack

- Runtime: Node.js 22+ (via Docker for isolation)
- Config: Docker volume `clawdbot-config`
- LLM: Claude via Anthropic API
- Platforms: WhatsApp, Telegram, Discord, iMessage

## Structure

- `specs/` - Experiment requirements and acceptance criteria
- `skills/` - Custom skill implementations (mounted read-only in container)
- `Dockerfile` - Container definition
- `docker-compose.yml` - Service configuration
- `clawdbot.sh` - Wrapper script for Docker commands

## Setup (Docker)

```bash
# 1. Copy env template and add your Anthropic API key
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# 2. Build the Docker image
docker compose build

# 3. Run onboarding
./clawdbot.sh onboard
```

## Commands (via Docker wrapper)

- `./clawdbot.sh onboard` - Initial setup wizard
- `./clawdbot.sh gateway` - Start the main service
- `./clawdbot.sh channels login` - Pair messaging platforms
- `./clawdbot.sh doctor` - Diagnose configuration issues
- `./clawdbot.sh --help` - Show all commands

## Key Paths

- Config: Stored in Docker volume `clawdbot-config`
- Logs: Check gateway output for debugging
- Skills: `./skills/` directory (mounted into container)

## Documentation

- Official docs: https://docs.molt.bot
- Email cleanup: see `specs/email-inbox-cleanup.md`
- Skills guide: see `specs/custom-skills.md`
- Integration setup: see `specs/messaging-setup.md`
