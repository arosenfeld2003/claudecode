# Data Schema Specification

## Overview

Complete DuckDB schema definitions for the OpenClaw Moltbook Monitor. Content is stored for 7 days to enable analysis, then purged while retaining metadata long-term.

## Database: `monitor.duckdb`

### Table: `posts`

Primary table for tracking observed posts from Moltbook.

```sql
CREATE TABLE posts (
    id              VARCHAR PRIMARY KEY,    -- Moltbook post ID
    url             VARCHAR NOT NULL,       -- Permalink to original
    agent_id        VARCHAR NOT NULL,       -- Who posted
    thread_id       VARCHAR,                -- Conversation context (nullable for top-level)
    submolt         VARCHAR NOT NULL,       -- Community/subreddit name
    title           VARCHAR,                -- Post title (nullable for comments)
    content         TEXT,                   -- Full post body (purged after 7 days)
    score           INTEGER DEFAULT 0,      -- Upvote score at time of fetch
    content_hash    VARCHAR NOT NULL,       -- SHA-256 for deduplication
    themes          VARCHAR[],              -- Dynamically assigned theme names
    confidence      DECIMAL(3,2),           -- Theme assignment confidence (0.00-1.00)
    sentiment       DECIMAL(3,2),           -- TextBlob polarity (-1.00 to 1.00)
    created_at      TIMESTAMP NOT NULL,     -- When posted on Moltbook
    fetched_at      TIMESTAMP DEFAULT NOW() -- When we observed it
);

CREATE INDEX idx_posts_agent ON posts(agent_id);
CREATE INDEX idx_posts_submolt ON posts(submolt);
CREATE INDEX idx_posts_created ON posts(created_at);
CREATE INDEX idx_posts_content_hash ON posts(content_hash);
CREATE INDEX idx_posts_sentiment ON posts(sentiment);
```

### Table: `comments`

Tracks comments for conversation threading and interaction analysis.

```sql
CREATE TABLE comments (
    id              VARCHAR PRIMARY KEY,    -- Moltbook comment ID
    post_id         VARCHAR NOT NULL,       -- Parent post
    parent_id       VARCHAR,                -- Parent comment (nullable for direct replies)
    agent_id        VARCHAR NOT NULL,       -- Who commented
    content         TEXT,                   -- Full comment body (purged after 7 days)
    content_hash    VARCHAR NOT NULL,       -- SHA-256 for deduplication
    score           INTEGER DEFAULT 0,      -- Upvote score
    sentiment       DECIMAL(3,2),           -- TextBlob polarity (-1.00 to 1.00)
    created_at      TIMESTAMP NOT NULL,     -- When posted
    fetched_at      TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (post_id) REFERENCES posts(id)
);

CREATE INDEX idx_comments_post ON comments(post_id);
CREATE INDEX idx_comments_agent ON comments(agent_id);
CREATE INDEX idx_comments_parent ON comments(parent_id);
CREATE INDEX idx_comments_sentiment ON comments(sentiment);
```

### Table: `themes`

Dynamic theme taxonomy discovered through content analysis.

```sql
CREATE TABLE themes (
    name            VARCHAR PRIMARY KEY,    -- Unique theme identifier
    description     VARCHAR NOT NULL,       -- What this theme captures
    relevance       VARCHAR[] NOT NULL,     -- Research goals served (see enum below)
    examples        VARCHAR[],              -- Array of post IDs demonstrating theme
    parent_theme    VARCHAR,                -- Hierarchical parent (nullable)
    post_count      INTEGER DEFAULT 0,      -- Number of posts tagged
    created_at      TIMESTAMP DEFAULT NOW(),
    deprecated_at   TIMESTAMP,              -- When retired (nullable if active)

    FOREIGN KEY (parent_theme) REFERENCES themes(name)
);

-- Research goal enum values:
-- 'social_network', 'trends', 'developer_tooling', 'ai_safety', 'mobile_apps'
```

### Table: `agents`

Profile and interaction data for observed agents.

```sql
CREATE TABLE agents (
    id              VARCHAR PRIMARY KEY,    -- Unique agent identifier
    name            VARCHAR NOT NULL,       -- Display name
    description     VARCHAR,                -- Agent bio/description
    karma           INTEGER DEFAULT 0,      -- Total karma score
    first_seen_at   TIMESTAMP DEFAULT NOW(),
    last_seen_at    TIMESTAMP DEFAULT NOW(),

    -- JSON blob: {"agent_id": interaction_count, ...}
    interaction_graph   JSON DEFAULT '{}',

    -- JSON blob: {"theme_name": post_count, ...}
    theme_profile       JSON DEFAULT '{}'
);

CREATE INDEX idx_agents_name ON agents(name);
CREATE INDEX idx_agents_karma ON agents(karma);
```

### Table: `agent_interactions`

Denormalized table for efficient interaction queries.

```sql
CREATE TABLE agent_interactions (
    from_agent_id       VARCHAR NOT NULL,
    to_agent_id         VARCHAR NOT NULL,
    interaction_type    VARCHAR NOT NULL,   -- 'reply', 'mention', 'quote'
    count               INTEGER DEFAULT 1,
    first_interaction   TIMESTAMP DEFAULT NOW(),
    last_interaction    TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (from_agent_id, to_agent_id, interaction_type)
);

CREATE INDEX idx_interactions_from ON agent_interactions(from_agent_id);
CREATE INDEX idx_interactions_to ON agent_interactions(to_agent_id);
```

### Table: `theme_changelog`

Audit log for theme taxonomy evolution.

```sql
CREATE TABLE theme_changelog (
    id              INTEGER PRIMARY KEY,
    timestamp       TIMESTAMP DEFAULT NOW(),
    action          VARCHAR NOT NULL,       -- 'create', 'merge', 'split', 'deprecate', 'update', 'suggest', 'schema_migration'
    theme_name      VARCHAR NOT NULL,
    details         JSON NOT NULL,          -- Action-specific details
    reviewed_at     TIMESTAMP,              -- When human reviewed (nullable)
    reviewed_by     VARCHAR                 -- Who reviewed (nullable)
);

CREATE INDEX idx_changelog_timestamp ON theme_changelog(timestamp);
CREATE INDEX idx_changelog_action ON theme_changelog(action);
```

### Table: `poll_state`

Tracks polling progress to avoid reprocessing.

```sql
CREATE TABLE poll_state (
    endpoint        VARCHAR PRIMARY KEY,    -- API endpoint identifier
    last_post_id    VARCHAR,                -- Last processed post ID
    last_poll_at    TIMESTAMP,              -- When last polled
    next_poll_at    TIMESTAMP,              -- When to poll next
    error_count     INTEGER DEFAULT 0,      -- Consecutive errors (for backoff)
    last_error      VARCHAR                 -- Last error message
);
```

### Table: `snapshots`

Hourly platform-wide metrics for time-series analysis.

```sql
CREATE TABLE snapshots (
    id              INTEGER PRIMARY KEY,
    timestamp       TIMESTAMP DEFAULT NOW(),
    total_agents    INTEGER DEFAULT 0,      -- Agents seen so far
    total_posts     INTEGER DEFAULT 0,      -- Posts in database
    total_comments  INTEGER DEFAULT 0,      -- Comments in database
    active_agents_24h INTEGER DEFAULT 0,    -- Agents active in last 24h
    avg_sentiment   DECIMAL(3,2),           -- Platform-wide average sentiment
    top_themes      JSON DEFAULT '[]',      -- Top 10 themes by activity
    top_words       JSON DEFAULT '[]'       -- Top 20 words by frequency
);

CREATE INDEX idx_snapshots_timestamp ON snapshots(timestamp);
```

## Materialized Views

### Rolling Window Aggregations

```sql
-- Theme activity in last hour
CREATE VIEW theme_activity_1h AS
SELECT
    unnest(themes) as theme,
    COUNT(*) as post_count,
    COUNT(DISTINCT agent_id) as unique_agents
FROM posts
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY theme;

-- Similar views for 6h, 24h, 7d windows
-- (Generated programmatically with different intervals)
```

### Trending Scores

```sql
CREATE VIEW theme_trending AS
SELECT
    theme,
    post_count_1h,
    post_count_24h,
    (post_count_1h * 24.0 / NULLIF(post_count_24h, 0)) as velocity,
    CASE
        WHEN post_count_1h * 24 > post_count_24h * 2 THEN true
        ELSE false
    END as is_spiking
FROM (
    SELECT
        a1.theme,
        a1.post_count as post_count_1h,
        a24.post_count as post_count_24h
    FROM theme_activity_1h a1
    JOIN theme_activity_24h a24 ON a1.theme = a24.theme
);
```

## JSON Schemas

### agents.interaction_graph

```json
{
    "type": "object",
    "description": "Map of agent_id to interaction count",
    "additionalProperties": {
        "type": "integer",
        "minimum": 0
    },
    "example": {
        "agent_123": 15,
        "agent_456": 8,
        "agent_789": 3
    }
}
```

### agents.theme_profile

```json
{
    "type": "object",
    "description": "Map of theme_name to post count",
    "additionalProperties": {
        "type": "integer",
        "minimum": 0
    },
    "example": {
        "developer_tools": 25,
        "ai_safety": 12,
        "code_review": 8
    }
}
```

### theme_changelog.details

```json
{
    "oneOf": [
        {
            "description": "Create action",
            "properties": {
                "initial_description": {"type": "string"},
                "research_goals": {"type": "array", "items": {"type": "string"}}
            }
        },
        {
            "description": "Merge action",
            "properties": {
                "merged_from": {"type": "array", "items": {"type": "string"}},
                "reason": {"type": "string"}
            }
        },
        {
            "description": "Split action",
            "properties": {
                "split_into": {"type": "array", "items": {"type": "string"}},
                "reason": {"type": "string"}
            }
        },
        {
            "description": "Deprecate action",
            "properties": {
                "reason": {"type": "string"},
                "replacement": {"type": "string"}
            }
        },
        {
            "description": "Update action",
            "properties": {
                "field": {"type": "string"},
                "old_value": {},
                "new_value": {},
                "reason": {"type": "string"}
            }
        },
        {
            "description": "Suggest action (emerging pattern detected)",
            "properties": {
                "suggested_name": {"type": "string"},
                "suggested_description": {"type": "string"},
                "sample_post_ids": {"type": "array", "items": {"type": "string"}},
                "keyword_frequency": {"type": "object"},
                "proposed_research_goals": {"type": "array", "items": {"type": "string"}}
            }
        },
        {
            "description": "Schema migration action",
            "properties": {
                "migration_name": {"type": "string"},
                "tables_affected": {"type": "array", "items": {"type": "string"}},
                "changes": {"type": "string"}
            }
        }
    ]
}
```

## Data Retention Policy

**Two-tier retention (configurable):**

| Data Type | Retention | Rationale |
|-----------|-----------|-----------|
| Post/comment content | 7 days | Enables analysis, then purge for storage/legal |
| Post/comment metadata | 90 days | Trends, themes, sentiment persist |
| Theme changelog | Indefinite | Audit trail |
| Agent profiles | Indefinite | Updated, not deleted |
| Snapshots | Indefinite | Time-series history |
| Poll state | Current only | Single row per endpoint |

**Content purge query (daily at 02:00 UTC):**
```sql
-- Purge content but keep metadata
UPDATE posts SET content = NULL WHERE fetched_at < NOW() - INTERVAL '7 days' AND content IS NOT NULL;
UPDATE comments SET content = NULL WHERE fetched_at < NOW() - INTERVAL '7 days' AND content IS NOT NULL;
```

**Metadata cleanup query (daily at 03:00 UTC):**
```sql
DELETE FROM posts WHERE fetched_at < NOW() - INTERVAL '90 days';
DELETE FROM comments WHERE fetched_at < NOW() - INTERVAL '90 days';
```

## Migration Strategy

When schema evolves:
1. New columns added with DEFAULT values (no migration needed)
2. Column type changes require backup + recreate
3. All migrations logged to `theme_changelog` with action='schema_migration'

## Acceptance Criteria

- [ ] All tables created with specified columns and types (including snapshots)
- [ ] Indexes created for query performance
- [ ] JSON schemas validated on insert/update
- [ ] Rolling window views functional (1h, 6h, 24h, 7d)
- [ ] Trending score calculation accurate
- [ ] Content purge job scheduled (7-day content retention)
- [ ] Metadata cleanup job scheduled (90-day metadata retention)
- [ ] Hourly snapshots captured
- [ ] Sentiment scores stored for posts and comments
- [ ] All 7 changelog action types supported
- [ ] Foreign key constraints enforced
