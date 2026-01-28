# Feature: Memory and Context Persistence

## Overview

Experiment with Clawdbot's memory system to understand how context persists across sessions and platforms, and how to leverage it for personalized assistance.

## Jobs To Be Done

1. User can have bot remember preferences stated in conversation
2. User can have bot recall information from previous sessions
3. User can have bot maintain separate contexts per group/channel
4. User can reset or clear bot memory when needed
5. User can export memory for backup or inspection

## Acceptance Criteria

- [ ] Bot recalls user name after being told once
- [ ] Bot remembers preferences (e.g., "I prefer morning reminders")
- [ ] Context from WhatsApp doesn't leak into Telegram conversations
- [ ] Group conversations have isolated memory from DMs
- [ ] Memory reset command clears relevant context

## Constraints

- Memory stored locally (privacy by default)
- Memory should not grow unbounded (implement pruning strategy)
- Sensitive information (passwords, tokens) must not be stored in memory

## Out of Scope

- Cloud sync of memory across devices
- Memory search/retrieval UI
- Memory sharing between users

## Experiment Ideas

1. **Preference learning**: Tell the bot your preferences over time, verify recall accuracy
2. **Context isolation**: Test that work group context stays separate from personal DMs
3. **Memory limits**: Find where context length causes degradation
4. **Proactive recall**: See if bot surfaces relevant past context unprompted

## Questions to Explore

- How is memory structured internally?
- What triggers memory consolidation vs. forgetting?
- Can skills access and modify memory?
- How does memory interact with heartbeats (proactive check-ins)?

## References

- Memory system: Check docs or source for implementation details
- Session handling: "Direct chats collapse into shared `main`; groups are isolated"
