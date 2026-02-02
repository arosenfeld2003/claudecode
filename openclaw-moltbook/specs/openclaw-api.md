# OpenClaw API Monitoring

## Overview

Interface with the OpenClaw/Moltbook platform (https://github.com/openclaw/openclaw) to observe agent communications in real-time with dynamic theme discovery.

## Research Goals (Guide All Decisions)

All theme discovery and analysis must serve these goals:
1. **Agent Social Network Study** - Understand how agents interact, form relationships, and coordinate
2. **Trend Identification** - Surface emerging patterns relevant to the research community
3. **Developer Tooling** - Identify opportunities for tools that improve human-agent collaboration
4. **AI Safety & Alignment** - Detect and document alignment-relevant behaviors, risks, and best practices
5. **Mobile App Ideas** - Identify quick-to-build mobile app opportunities for income generation (prioritize: clear market need, fast MVP, monetization path)

## Requirements

### Real-Time Stream Processing
- Subscribe to/poll the feed for new posts
- Let the agent discover and assign themes dynamically
- Store: post reference + dynamically assigned tags
- Theme taxonomy evolves based on observed content

### Data Model
```
posts:
  - id: unique identifier
  - url: permalink to original post
  - agent_id: who posted
  - thread_id: conversation context
  - timestamp: when posted
  - themes: [dynamically assigned]
  - confidence: theme assignment confidence
  - content_hash: for deduplication

themes:
  - name: discovered theme name
  - description: what this theme captures
  - relevance: which research goal(s) it serves
  - examples: sample posts demonstrating theme
  - created_at: when first discovered
  - post_count: how many posts tagged
  - parent_theme: optional hierarchy

agents:
  - id: unique identifier
  - interaction_graph: who they interact with
  - theme_profile: distribution of themes in their posts
```

### Dynamic Theme Discovery
- Agent analyzes posts and proposes themes
- New themes must map to at least one research goal
- Themes can be merged, split, or deprecated over time
- Human-reviewable theme changelog

### API Interaction
- All requests routed through reverse proxy container
- No authentication credentials stored or used
- Read-only operations only
- Respect robots.txt and rate limits

## Acceptance Criteria

- [ ] Real-time feed monitoring
- [ ] Dynamic theme assignment at ingestion
- [ ] Theme taxonomy stored and versioned
- [ ] Each theme linked to research goal(s)
- [ ] CLI: `monitor stream` shows live tagged feed
- [ ] CLI: `monitor themes` shows discovered themes with research goal mapping
