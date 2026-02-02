# Trend Analysis

## Overview

Aggregate and analyze dynamically-tagged posts to surface insights aligned with research goals.

## Research Goals (Frame All Analysis)

Every analysis output must connect to:
1. **Agent Social Network Study** - How do agents interact and coordinate?
2. **Trend Identification** - What patterns are emerging?
3. **Developer Tooling** - What tools would help?
4. **AI Safety & Alignment** - What risks and best practices are evident?
5. **Mobile App Ideas** - What quick-to-build mobile apps could generate income?

## Requirements

### Sentiment Analysis
- Calculate sentiment polarity for all posts and comments using TextBlob
- Score range: -1.0 (negative) to +1.0 (positive)
- Categorical labels: "positive" (≥0.3), "negative" (≤-0.3), "neutral" (between)
- Track platform-wide sentiment in hourly snapshots
- Surface sentiment trends by theme and submolt

### Adaptive Theme Evolution
- Agent continuously evaluates theme taxonomy effectiveness
- Proposes theme splits when variance is high
- Proposes theme merges when overlap is significant
- Retires themes that no longer serve research goals
- All changes logged for human review

### Real-Time Aggregation
- Maintain rolling windows: 1h, 6h, 24h, 7d
- Calculate trending scores per theme
- Detect sudden spikes in theme activity
- Cross-reference trends with research goals

### Analysis Outputs (Goal-Aligned)

**For Agent Social Network:**
- Interaction graphs: who talks to whom
- Community detection: clusters of agents
- Influence mapping: who drives conversations

**For Trend Identification:**
- Trending themes with velocity
- Emerging patterns not yet named
- Correlation between themes

**For Developer Tooling:**
- Common pain points agents help with
- Workflow patterns that work/fail
- Integration opportunities

**For AI Safety & Alignment:**
- Alignment-relevant behaviors
- Risk patterns and mitigations
- Best practices emerging from agent interactions

**For Mobile App Ideas:**
- Pain points that could be solved with a mobile app
- Frequently requested features/tools
- Market gaps (things people ask for but don't exist)
- Monetization signals (willingness to pay, subscription potential)
- Quick MVP candidates (can ship in days/weeks, not months)
- Prioritize by: market demand × build speed × revenue potential

### CLI Commands
- `monitor trends` - Current trends mapped to research goals
- `monitor network` - Agent interaction analysis
- `monitor safety` - Alignment-focused insights
- `monitor apps` - Mobile app opportunity pipeline
- `monitor themes --evolve` - Review theme taxonomy changes
- `monitor sentiment` - Platform-wide mood, by theme, by submolt

### Web Dashboard
- Simple FastAPI + Jinja2 web interface for non-technical users
- Live feed with sentiment indicators
- Theme browser with trend sparklines
- Agent directory with search
- Platform health/stats overview
- Data export downloads (CSV, JSON)

### Data Export
- `GET /api/export/posts.csv` - Posts with metadata (content excluded after 7 days)
- `GET /api/export/agents.csv` - Agent profiles and stats
- `GET /api/export/themes.csv` - Theme taxonomy with metrics
- `GET /api/export/database.db` - Full DuckDB snapshot (authenticated access)

## Acceptance Criteria

- [ ] All analysis outputs tagged with research goal relevance
- [ ] Theme evolution logged and human-reviewable
- [ ] Trending detection with research goal context
- [ ] Network analysis for social dynamics
- [ ] Safety-focused analysis view
- [ ] App idea pipeline with prioritization
- [ ] Sentiment analysis on all posts/comments
- [ ] Web dashboard functional and accessible
- [ ] Data exports available (CSV, JSON, DB snapshot)
