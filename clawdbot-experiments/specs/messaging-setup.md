# Feature: Messaging Platform Integration

## Overview

Connect Clawdbot to messaging platforms (WhatsApp, Telegram, Discord, iMessage) for conversational AI access from any device.

## Jobs To Be Done

1. User can pair WhatsApp via QR code scan
2. User can receive and respond to messages in real-time
3. User can configure which contacts/groups can interact with the bot
4. User can set mention requirements for group chats
5. User can test connectivity with a manual message send

## Acceptance Criteria

- [ ] Gateway starts without errors
- [ ] QR code appears for WhatsApp pairing
- [ ] Bot responds to direct messages from whitelisted senders
- [ ] Bot ignores messages from non-whitelisted senders
- [ ] Group messages require @mention when configured
- [ ] Test message sends successfully via CLI

## Constraints

- WhatsApp: Must stay connected (phone needs internet)
- iMessage: macOS only, requires imsg CLI
- Rate limits: Respect platform ToS to avoid bans
- Privacy: Messages processed locally by default

## Out of Scope

- Multi-account support per platform
- Message scheduling/queuing
- Read receipts and typing indicators

## Setup Checklist

1. [ ] Run `clawdbot onboard --install-daemon`
2. [ ] Run `clawdbot channels login` and scan QR
3. [ ] Configure `~/.clawdbot/moltbot.json` with allowed senders
4. [ ] Test with `moltbot message send --target <phone> --message "Hello"`
5. [ ] Start gateway: `clawdbot gateway`

## Configuration Example

```json
{
  "channels": {
    "whatsapp": {
      "allowFrom": ["+1555123456", "+1555987654"]
    }
  },
  "groups": {
    "*": {
      "requireMention": true
    }
  }
}
```

## References

- Channel setup: https://docs.molt.bot
- WhatsApp protocol: Baileys
- Telegram: grammY framework
