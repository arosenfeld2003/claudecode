# Feature: Integrations Roadmap

## Overview

Planned integrations to extend Clawdbot into a unified personal assistant across email, social, code, and mobile access.

## Planned Integrations

### 1. iCloud (Priority: High)
**Status**: In Progress - see `email-inbox-cleanup.md`

- **Email** (IMAP): Read-only inbox analysis, then cleanup
- **Calendar**: Event queries, scheduling assistance
- **Reminders**: Task management via chat
- **Notes**: Search and reference

**Auth**: App-specific passwords via appleid.apple.com

### 2. Slack (Priority: Medium)
**Purpose**: Work communication hub

- Read/send messages in channels and DMs
- Respond to mentions
- Search message history
- Integration with workflows/automations

**Auth**: Slack App with Bot Token (xoxb-)

### 3. Mastodon / Fediverse (Priority: Medium)
**Purpose**: Social presence and monitoring

- Post updates
- Monitor mentions and replies
- Follow hashtags
- Cross-post from other sources

**Auth**: OAuth 2.0 via instance settings

### 4. GitHub (Priority: Medium)
**Purpose**: Code and project management

- PR notifications and summaries
- Issue triage assistance
- Code review reminders
- Release monitoring

**Auth**: GitHub App or Personal Access Token

### 5. Secure Mobile Access (Priority: High)
**Purpose**: Interact with Clawdbot from phone

**Options to evaluate**:
- **Signal**: E2E encrypted, Clawdbot has native support
- **Telegram**: Good mobile experience, bot API
- **WhatsApp**: Already supported, but Meta privacy concerns
- **Self-hosted**: Matrix/Element for full control

**Security requirements**:
- E2E encryption preferred
- Sender whitelisting (only your devices)
- Optional: Require passphrase for sensitive commands
- Audit log of all remote commands

## Integration Priority Matrix

| Integration | Value | Complexity | Priority |
|-------------|-------|------------|----------|
| iCloud Email | High | Medium | 1 |
| Mobile Access | High | Low | 2 |
| GitHub | Medium | Low | 3 |
| Slack | Medium | Medium | 4 |
| Mastodon | Low | Low | 5 |
| iCloud Calendar | Medium | Medium | 6 |

## Security Principles

1. **Least privilege**: Request minimum scopes needed
2. **Read-only first**: Prove classification before write access
3. **Audit everything**: Log all actions for review
4. **Isolated runtime**: Docker container, not on host
5. **Credential hygiene**: No plaintext secrets, use env vars or secrets manager
6. **Revocable access**: Use tokens that can be rotated/revoked

## Out of Scope

- Self-hosting Mastodon instance
- Building custom mobile app
- Multi-user / family access
- Payment or financial integrations

## Next Steps

1. [ ] Complete email inbox cleanup (read-only phase)
2. [ ] Choose mobile access platform (Signal vs Telegram)
3. [ ] Set up GitHub notifications
4. [ ] Evaluate Slack workspace integration
5. [ ] Create Mastodon bot account
