# Implementation Plan

## Gap Analysis Summary

Last analyzed: 2026-02-01 (Updated)

| Category | Count | Status |
|----------|-------|--------|
| Total Acceptance Criteria | 51 | From 6 specs (updated) |
| Fully Covered | 51 | 100% |
| Partially Covered | 0 | 0% |
| Gaps Identified | 0 | 0% |
| Source Code Status | 0 files | Verified empty - no implementation exists |

### Recent Changes (2026-02-01)
- Added content storage with 7-day retention (full post/comment text)
- Added TextBlob sentiment analysis
- Added Web Dashboard (FastAPI + Jinja2)
- Added Data Export (CSV, JSON, DB snapshot)
- Added snapshots table for time-series metrics
- Updated data-schema.md and trend-analysis.md specs

### Alignment with Moltbook Observatory (2026-02-01)
Compared approach with [kelkalot/moltbook-observatory](https://github.com/kelkalot/moltbook-observatory):
- **Adopted**: Full content storage (7-day window), TextBlob sentiment, Web UI, Data exports
- **Retained advantages**: Rate limiting, goal-aligned analysis, theme taxonomy, security posture
- **Key differentiator**: Non-technical audience focus vs. raw data archive

---

## Current Focus

### Phase 1: Foundation & Security Infrastructure (Priority: Critical)

- [x] **1.1 Create Docker Compose base configuration**
  - Define `openclaw-internal` network with no external access
  - Configure reverse proxy container (Nginx) with internet access
  - Configure monitor container with NO direct internet access
  - Mount DuckDB data volume (not to sensitive host paths)
  - Ensure non-root user in containers
  - **Enable read-only root filesystem for monitor container**
  - **Verify no volume mounts to sensitive host directories (~/.ssh, ~/.aws, etc.)**
  - Reference: `specs/security-architecture.md` Network Architecture diagram
  - Acceptance criteria: `docker compose` enforces network isolation

- [x] **1.2 Implement Nginx reverse proxy with domain allowlisting**
  - Allowlist: `www.moltbook.com`, `api.moltbook.com`, `github.com`, `raw.githubusercontent.com`
  - Note: "Moltbook" is the platform name; "OpenClaw" is this project name
  - Enable request logging for audit trail (JSON format with timestamps)
  - Configure rate limiting (100 req/min to match Moltbook limits) - serves as backup to client-side limiting
  - Enforce TLS verification for all outbound connections
  - **Handle proxy errors gracefully with logging**
  - Reference: `specs/security-architecture.md` Reverse Proxy requirements
  - Acceptance criteria: Only allowlisted domains accessible through proxy

- [x] **1.3 Create Python project structure**
  - `pyproject.toml` with Python 3.12
  - **Dependencies: httpx, typer, rich, duckdb, pytest, mypy, ruff, apscheduler, textblob, fastapi, uvicorn, jinja2, python-multipart**
  - `src/monitor/` package structure with `__init__.py`, `cli.py`, `__main__.py`
  - Dockerfile for monitor container (read-only root, non-root user)
  - **Configure pytest for test discovery** (`tests/` directory)
  - **Configure mypy and ruff for type checking and linting**
  - Create `.dockerignore` and `.gitignore`
  - Reference: `AGENTS.md` Tech Stack

- [x] **1.4 Implement network isolation verification tests**
  - Test: Monitor container cannot reach internet directly (expect connection refused)
  - Test: Only allowlisted domains accessible through proxy
  - Test: All requests logged with timestamps
  - Test: No credentials in image or runtime (`docker inspect` validation)
  - **Test: No volume mounts to sensitive host directories**
  - **Test: Read-only root filesystem is enforced** (attempt write, expect failure)
  - Reference: `specs/security-architecture.md` Acceptance Criteria (6 items)

- [x] **1.5 Implement health check endpoint** (moved from Phase 8)
  - HTTP endpoint for container health checks (`/health`)
  - Check: database connectivity
  - Check: proxy connectivity
  - Return: JSON with component status and timestamp
  - Configure Docker HEALTHCHECK directive
  - Reference: Required for container orchestration reliability

### Phase 2: Moltbook API Client (Priority: High)

- [x] **2.1 Implement read-only Moltbook API client**
  - Base URL: `https://www.moltbook.com/api/v1` (routed via reverse proxy)
  - Implement `GET /posts?sort=new&limit=25` - fetch new posts
  - Implement `GET /posts?sort=hot&limit=25` - fetch trending posts
  - Implement `GET /posts?sort=top&limit=25` - fetch top posts
  - Implement `GET /posts?sort=rising&limit=25` - fetch rising posts
  - Implement `GET /posts/:id` - fetch single post
  - Implement `GET /posts/:id/comments?sort={top|new|controversial}` - fetch post comments
  - Implement `GET /submolts` - list all communities
  - Implement `GET /submolts/:name` - get community details
  - Implement `GET /agents/profile?name=X` - fetch agent profiles
  - Implement `GET /search?q=X&limit=25` - search functionality
  - NO authentication required (read-only public data)
  - Respect rate limits: 100 req/min, 5000/hr, 50000/day
  - Set User-Agent: `OpenClawMonitor/1.0 (research purposes)`
  - Reference: `specs/openclaw-api.md` API Interaction, IMPLEMENTATION_PLAN.md API Reference

- [x] **2.2 Implement robots.txt compliance**
  - Fetch and parse robots.txt on startup
  - Cache for 24 hours
  - Honor Crawl-delay if specified
  - Skip disallowed paths
  - Reference: `specs/polling-strategy.md` robots.txt Compliance

- [x] **2.3 Implement rate limiter**
  - Track requests per minute using sliding window (primary limit: 100/min)
  - **Track requests per hour** (secondary limit: 5,000/hr)
  - **Track requests per day** (tertiary limit: 50,000/day)
  - Track rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
  - Implement `can_request()` and `wait_time()` methods
  - **Warn when approaching hourly/daily limits** (at 80% threshold)
  - Budget allocation: 40% new posts, 20% trending, 20% comments, 10% agents, 10% reserve
  - Note: Client-side rate limiting is primary; proxy rate limiting is backup
  - Reference: `specs/polling-strategy.md` Budget Enforcement

- [x] **2.4 Implement content deduplication**
  - Calculate `content_hash`: SHA-256 of `{id}:{agent_id}:{title}:{submolt}`
  - Check post ID exists before processing
  - Check content_hash exists for duplicate content detection
  - Store post references (id, url, agent_id, timestamp) NOT full content
  - Reference: `specs/polling-strategy.md` Deduplication Strategy

- [x] **2.5 Implement error handling and backoff**
  - Handle 429 Rate Limited: exponential backoff, respect Retry-After header
  - Handle 500-599 Server Error: exponential backoff
  - Handle 400-499 Client Error: log and skip (don't retry)
  - Handle Timeout: linear backoff
  - Backoff formula: `delay = 1.0 * 2^min(error_count, 8) * jitter(0.8-1.2)`, capped at 5 min
  - Reset error count on successful request
  - Reference: `specs/polling-strategy.md` Error Handling & Backoff

- [x] **2.6 Implement polling scheduler**
  - Default intervals: new=5min, hot=15min, top=1hr, submolts=6hr, comments/agents=on-demand
  - Adaptive intervals based on activity rate (high activity → more frequent, low → less)
  - Track last seen post ID per endpoint in `poll_state` table
  - Graceful shutdown: complete current request, persist state, exit
  - Reference: `specs/polling-strategy.md` Polling Intervals, Adaptive Intervals

### Phase 3: DuckDB Data Layer (Priority: High)

- [ ] **3.1 Implement DuckDB schema - Core tables**
  - Table: `posts` (id PK, url, agent_id, thread_id, submolt, title, **content TEXT**, score, content_hash, themes[], confidence, **sentiment**, created_at, fetched_at)
  - Table: `comments` (id PK, post_id FK, parent_id, agent_id, **content TEXT**, content_hash, score, **sentiment**, created_at, fetched_at)
  - Table: `themes` (name PK, description, relevance[], examples[], parent_theme FK, post_count, created_at, deprecated_at)
  - Table: `agents` (id PK, name, description, karma, first_seen_at, last_seen_at, interaction_graph JSON, theme_profile JSON)
  - Table: `agent_interactions` (from_agent_id, to_agent_id, interaction_type) PK, count, first_interaction, last_interaction
  - Table: `theme_changelog` (id PK, timestamp, action, theme_name, details JSON, reviewed_at, reviewed_by)
  - Table: `poll_state` (endpoint PK, last_post_id, last_poll_at, next_poll_at, error_count, last_error)
  - **Table: `snapshots` (id PK, timestamp, total_agents, total_posts, total_comments, active_agents_24h, avg_sentiment, top_themes JSON, top_words JSON)**
  - Create all indexes as specified
  - Reference: `specs/data-schema.md` (full SQL definitions)

- [ ] **3.2 Implement JSON schema validation**
  - Validate `agents.interaction_graph`: `{agent_id: count}` format
  - Validate `agents.theme_profile`: `{theme_name: count}` format
  - Validate `theme_changelog.details`: oneOf [create, merge, split, deprecate] schemas
  - Reference: `specs/data-schema.md` JSON Schemas section

- [ ] **3.3 Implement rolling window views**
  - View: `theme_activity_1h` - theme, post_count, unique_agents for last hour
  - View: `theme_activity_6h` - same for 6 hours
  - View: `theme_activity_24h` - same for 24 hours
  - View: `theme_activity_7d` - same for 7 days
  - Reference: `specs/data-schema.md` Materialized Views

- [ ] **3.4 Implement trending score calculation**
  - View: `theme_trending` with velocity calculation
  - Velocity formula: `post_count_1h * 24.0 / post_count_24h`
  - Spike detection: `is_spiking = post_count_1h * 24 > post_count_24h * 2`
  - Reference: `specs/data-schema.md` Trending Scores view

- [ ] **3.5 Implement spike detection queries**
  - Activity spike threshold: 3x normal rate → increase polling frequency
  - Trending surge threshold: theme activity 5x hourly average → flag for analysis
  - Viral content threshold: single post gets 10x comments → deep fetch
  - Formula: `is_spiking = current_rate > historical_avg * 3.0` (or > 10 if new)
  - Reference: `specs/polling-strategy.md` Spike Detection

- [ ] **3.6 Implement agent interaction graph storage**
  - Track interactions via `agent_interactions` table
  - Interaction types: 'reply', 'mention', 'quote'
  - Update counts and timestamps on each interaction
  - Update `agents.interaction_graph` JSON as denormalized cache
  - Reference: `specs/data-schema.md` agent_interactions table

- [ ] **3.7 Implement two-tier data retention with scheduler**
  - **Content (posts.content, comments.content): 7 days** - purge content, keep metadata
  - **Metadata (full rows): 90 days** - then delete entirely
  - Theme changelog: indefinite (audit trail)
  - Agent profiles: indefinite (updated, not deleted)
  - Snapshots: indefinite (time-series history)
  - Poll state: current only (single row per endpoint)
  - Implement content purge job: `UPDATE posts SET content = NULL WHERE fetched_at < NOW() - INTERVAL '7 days'`
  - Implement metadata cleanup job: `DELETE FROM posts WHERE fetched_at < NOW() - INTERVAL '90 days'`
  - **Schedule content purge using APScheduler** (daily at 02:00 UTC)
  - **Schedule metadata cleanup using APScheduler** (daily at 03:00 UTC)
  - **Log cleanup results** (rows affected, execution time)
  - Reference: `specs/data-schema.md` Data Retention Policy

- [ ] **3.8 Implement sentiment analysis with TextBlob**
  - Calculate sentiment polarity on post/comment ingest
  - TextBlob polarity returns -1.0 to +1.0
  - Store in `posts.sentiment` and `comments.sentiment` columns
  - Provide categorical labels: positive (≥0.3), negative (≤-0.3), neutral
  - Handle empty/null content gracefully (sentiment = NULL)
  - Performance target: < 5ms per text
  - Reference: `specs/trend-analysis.md` Sentiment Analysis

- [ ] **3.9 Implement hourly snapshots**
  - Schedule hourly snapshot capture using APScheduler
  - Calculate: total_agents, total_posts, total_comments, active_agents_24h
  - Calculate: avg_sentiment across last hour's posts
  - Calculate: top_themes (top 10 by activity in last hour)
  - Calculate: top_words (top 20 by frequency in last hour, excluding stop words)
  - Store in `snapshots` table
  - Reference: `specs/data-schema.md` snapshots table

### Phase 4: Dynamic Theme Discovery (Priority: High)

- [ ] **4.1 Load seed themes into database with keyword weights**
  - Insert 20 seed themes from 5 categories:
    - Social Network (4): agent_collaboration, agent_conflict, agent_hierarchy, agent_reputation
    - Trends (4): emerging_tech, industry_news, hot_debate, viral_content
    - Developer Tooling (4): code_assistance, workflow_automation, integration_requests, documentation
    - AI Safety (4): alignment_discussion, capability_limits, unexpected_behavior, safety_practices
    - Mobile Apps (4): app_requests, pain_points, monetization, quick_wins
  - Each theme includes keywords, description, and research goal mapping
  - **Define keyword weights for each theme** (rarer/more specific keywords get higher weights)
  - **Store weights in theme metadata** (JSON column or separate table)
  - Log creation to `theme_changelog` with action='create'
  - Reference: `specs/theme-classification.md` Seed Themes tables, Step 1: Keyword Matching

- [ ] **4.2 Implement keyword-based theme scoring**
  - Function: `calculate_theme_score(content, theme) -> 0.0-1.0`
  - Lowercase content, extract word set
  - Count keyword matches (direct matches in content)
  - Apply keyword weights (rarer keywords score higher)
  - Normalize to 0-1 range
  - Reference: `specs/theme-classification.md` Step 1: Keyword Matching

- [ ] **4.3 Implement confidence scoring and theme assignment**
  - Function: `calculate_confidence(scores) -> (themes[], confidence)`
  - Assignment threshold: 0.3 (themes below this not assigned)
  - Sort themes by score, assign those above threshold
  - Confidence = highest score (or avg of top 2 if within 0.1)
  - Max 5 themes per post
  - Reference: `specs/theme-classification.md` Step 2: Confidence Scoring

- [ ] **4.4 Implement research goal mapping**
  - Each assigned theme maps to its research goal(s)
  - Post's research goal relevance = union of all assigned themes' goals
  - Goals: social_network, trends, developer_tooling, ai_safety, mobile_apps
  - Reference: `specs/theme-classification.md` Step 3: Research Goal Mapping

- [ ] **4.5 Implement theme split detection**
  - Trigger conditions: posts > 100 AND intra-cluster similarity < 0.5 AND min cluster size ≥ 20
  - Analyze keyword co-occurrence to find distinct clusters
  - Log proposed split to `theme_changelog` with action='split' and redistribution details
  - Reference: `specs/theme-classification.md` Split Detection

- [ ] **4.6 Implement theme merge detection**
  - Trigger conditions: Jaccard similarity > 0.7 AND keyword overlap > 50% AND same research goals
  - Calculate post overlap between theme pairs
  - Log proposed merge to `theme_changelog` with action='merge' and reason
  - Reference: `specs/theme-classification.md` Merge Detection

- [ ] **4.7 Implement theme deprecation detection**
  - Trigger conditions: no posts in 30 days AND (total < 10 posts OR goal no longer relevant)
  - Set `deprecated_at` timestamp on theme
  - Log deprecation to `theme_changelog` with action='deprecate' and reason
  - Reference: `specs/theme-classification.md` Deprecation Detection

- [ ] **4.8 Implement local LLM integration (optional enhancement)**
  - Use Ollama with `qwen2.5-coder:7b` model
  - Temperature: 0.3, max_tokens: 200, timeout: 10s
  - Prompt includes post content, available themes, research goals
  - Response: JSON with themes[], confidence, optional new_theme_suggestion
  - Fallback to rule-based on timeout or error
  - API key via runtime environment variable only (not in image)
  - Log all prompts/responses for audit
  - Reference: `specs/theme-classification.md` LLM Enhancement

- [ ] **4.9 Implement classification performance validation**
  - Rule-based: < 10ms per post, 100 posts/second batch
  - LLM: < 2s per post
  - Max 100 active themes enforced
  - Reference: `specs/theme-classification.md` Performance Requirements

- [ ] **4.10 Implement emerging pattern detection** (NEW)
  - Detect posts that don't match any theme well (all scores < 0.2)
  - Track unclassified post patterns (keyword frequency analysis)
  - Surface "emerging patterns not yet named" for human review
  - Log to `theme_changelog` with action='suggest' when pattern threshold reached
  - Threshold: 20+ similar unclassified posts in 24 hours
  - Reference: `specs/trend-analysis.md` "Emerging patterns not yet named"

### Phase 5: CLI Commands - Basic (Priority: Medium)

Note: This phase implements basic CLI commands that use direct database queries.
Advanced analysis features (network analysis, app scoring) are implemented in Phase 6
and their CLI enhancements are added in Phase 6 tasks.

- [ ] **5.1 Implement CLI base with Typer**
  - Create `src/monitor/cli.py` with Typer app
  - Create `src/monitor/__main__.py` for `python -m monitor` execution
  - Configure Rich console for output formatting
  - Add global `--format` option (text/json)
  - Add global `--verbose` option for debug output
  - Reference: `AGENTS.md` Tech Stack (Typer, Rich)

- [ ] **5.2 Implement `monitor stream` command**
  - Show live tagged feed with Rich formatting (table or panel)
  - Display columns: timestamp, agent_id, submolt, title, themes[], confidence
  - Filter options: `--submolt NAME`, `--theme NAME`, `--goal GOAL`
  - Auto-refresh with configurable interval
  - Reference: `specs/openclaw-api.md` CLI requirements

- [ ] **5.3 Implement `monitor themes` command**
  - List discovered themes with descriptions
  - Show research goal mapping for each theme (color-coded)
  - Display post count and trending status (↑↓→)
  - Option: `--goal GOAL` to filter by research goal
  - Reference: `specs/openclaw-api.md` CLI: `monitor themes`

- [ ] **5.4 Implement `monitor themes --evolve` command**
  - Review theme taxonomy changes from `theme_changelog`
  - Show: timestamp, action, theme_name, details (formatted)
  - Filter: `--action {create|merge|split|deprecate|suggest}`
  - Filter: `--since DATE` for time range
  - Mark as reviewed: `--review ID` to update reviewed_at/reviewed_by
  - Reference: `specs/trend-analysis.md` CLI: `monitor themes --evolve`

- [ ] **5.5 Implement `monitor trends` command (basic)**
  - Current trends from `theme_trending` view
  - Display: theme, post_count_1h, velocity, is_spiking flag
  - Sort by velocity (highest first)
  - Highlight sudden spikes with color
  - Option: `--window {1h|6h|24h|7d}` to change time window
  - Reference: `specs/trend-analysis.md` CLI: `monitor trends`

- [ ] **5.6 Implement `monitor agent <name>` command (basic)**
  - Show agent profile: name, description, karma, first_seen, last_seen
  - Display theme distribution (theme_profile JSON as bar chart or table)
  - Show top 10 interactions from `agent_interactions` table
  - Display recent posts by this agent
  - Reference: `specs/data-schema.md` agents table

- [ ] **5.7 Implement `monitor status` command** (moved from Phase 7)
  - Show current poll state for all endpoints
  - Display rate limit remaining (minute/hour/day), next poll time, error count
  - Show database stats: total posts, comments, themes, agents
  - Show uptime and last successful poll
  - Reference: Operational visibility requirement

- [ ] **5.8 Implement `--format json` for all commands**
  - JSON output schema consistent across commands
  - Include metadata: timestamp, command, version
  - Disable Rich formatting when JSON requested
  - Enable piping to jq or other tools
  - Reference: General developer tooling best practice

### Phase 6: Analysis & Insights + Advanced CLI (Priority: Medium)

Note: This phase implements analysis logic AND the CLI commands that depend on it.

- [ ] **6.1 Implement goal-aligned analysis framework**
  - Tag all analysis outputs with research goal relevance
  - Create analysis report data structures per goal
  - Report fields: goal, insights[], supporting_data, generated_at
  - Reference: `specs/trend-analysis.md` Research Goals frame all analysis

- [ ] **6.2 Implement social network analysis**
  - Build interaction graph from `agent_interactions` table
  - Calculate node metrics: degree centrality, betweenness centrality
  - Identify clusters using connected components or modularity-based approach
  - Rank agents by influence (outbound interaction count + karma)
  - Reference: `specs/trend-analysis.md` Analysis Outputs for Social Network

- [ ] **6.3 Implement `monitor network` command** (depends on 6.2)
  - Agent interaction analysis using social network analysis module
  - Display top interacting agent pairs with count
  - Community detection: show identified clusters
  - Influence mapping: rank agents by influence score
  - Reference: `specs/trend-analysis.md` Analysis Outputs for Social Network

- [ ] **6.4 Implement trend correlation analysis**
  - Calculate theme co-occurrence: which themes appear together
  - Build correlation matrix for theme pairs
  - Identify emerging patterns (themes with accelerating velocity)
  - Reference: `specs/trend-analysis.md` Analysis Outputs for Trends

- [ ] **6.5 Implement developer tooling insights**
  - Aggregate posts with developer_tooling themes
  - Extract pain points from code_assistance, documentation requests
  - Identify workflow patterns from workflow_automation discussions
  - Surface integration opportunities from integration_requests
  - Reference: `specs/trend-analysis.md` Analysis Outputs for Developer Tooling

- [ ] **6.6 Implement AI safety report generation**
  - Aggregate posts with ai_safety themes
  - Categorize: alignment_discussion, capability_limits, unexpected_behavior, safety_practices
  - Identify risk patterns (capability_limits + unexpected_behavior clusters)
  - Extract best practices (safety_practices with high engagement)
  - Reference: `specs/trend-analysis.md` Analysis Outputs for AI Safety

- [ ] **6.7 Implement `monitor safety` command** (depends on 6.6)
  - Alignment-focused insights view using safety report module
  - Filter posts tagged with AI Safety themes
  - Show: alignment_discussion, capability_limits, unexpected_behavior, safety_practices
  - Highlight risk patterns and best practices
  - Reference: `specs/trend-analysis.md` Analysis Outputs for AI Safety

- [ ] **6.8 Implement mobile app opportunity scoring**
  - Score formula: demand × speed × revenue
  - Demand: frequency of app_requests + pain_points mentions
  - Speed proxy: presence of quick_wins theme
  - Revenue: presence of monetization signals (pay, subscribe, premium)
  - Output ranked list of MVP candidates
  - Reference: `specs/trend-analysis.md` Analysis Outputs for Mobile App Ideas

- [ ] **6.9 Implement `monitor apps` command** (depends on 6.8)
  - Mobile app opportunity pipeline using scoring module
  - Filter posts tagged with Mobile Apps themes
  - Show: app_requests, pain_points, monetization, quick_wins
  - Display prioritized list with scores
  - Highlight quick MVP candidates (quick_wins + pain_points intersection)
  - Reference: `specs/trend-analysis.md` Analysis Outputs for Mobile App Ideas

### Phase 7: Monitoring & Observability (Priority: Medium)

- [ ] **7.1 Implement polling metrics collection**
  - Counter: `requests_total` - total API requests
  - Counter: `requests_failed` - failed requests by error type
  - Counter: `rate_limit_hits` - times hit rate limit
  - Counter: `posts_processed` - posts successfully processed
  - Counter: `duplicates_skipped` - duplicate posts skipped
  - Histogram: `poll_latency_ms` - time per poll cycle
  - Gauge: `backoff_seconds` - current backoff delay
  - Reference: `specs/polling-strategy.md` Monitoring Metrics

- [ ] **7.2 Implement structured logging**
  - JSON log format with fields: timestamp, level, event, endpoint, posts_fetched, posts_new, duplicates, latency_ms, rate_limit_remaining
  - Log all poll completions, errors, rate limit events
  - Log all theme taxonomy changes
  - **Log hourly/daily rate limit warnings** (when approaching 80% threshold)
  - Reference: `specs/polling-strategy.md` Logging Format

### Phase 8: Remote Access & Operations (Priority: Low)

- [ ] **8.1 Document Tailscale setup for host**
  - Tailscale runs on HOST only, not in containers
  - SSH/tmux access to host for monitoring
  - No exposed ports to public internet
  - Document: installation, authentication, ACLs
  - Reference: `specs/security-architecture.md` Remote Access

- [ ] **8.2 Create operational runbooks**
  - Runbook: Start monitoring (`docker compose up -d`)
  - Runbook: Stop monitoring (`docker compose down`)
  - Runbook: Export data (DuckDB backup, CSV export)
  - Runbook: Review theme changes (`monitor themes --evolve`)
  - Runbook: Troubleshooting common issues
  - Reference: `AGENTS.md` Build & Run section

Note: Health check endpoint moved to Phase 1 (Task 1.5) for early availability.

### Phase 9: Web Dashboard & Data Export (Priority: Medium)

- [ ] **9.1 Create FastAPI web application structure**
  - `src/monitor/web/` package with `app.py`, `routes.py`, `templates/`
  - Mount static files for CSS/JS
  - Configure Jinja2 template engine
  - Add CORS middleware for API access
  - Integrate with existing CLI database connection
  - Reference: `specs/trend-analysis.md` Web Dashboard

- [ ] **9.2 Implement dashboard home page**
  - Platform stats overview (total posts, agents, comments)
  - Current sentiment indicator with emoji (like Observatory)
  - Top 5 trending themes with sparklines
  - Recent activity feed (last 20 posts)
  - Responsive layout for desktop/mobile
  - Reference: Non-technical audience accessibility

- [ ] **9.3 Implement live feed page**
  - Real-time post stream (auto-refresh every 30s)
  - Sentiment indicators per post (color-coded)
  - Theme tags displayed as pills
  - Filter by submolt, theme, sentiment
  - Pagination for historical browsing
  - Reference: `specs/trend-analysis.md` Web Dashboard

- [ ] **9.4 Implement theme browser page**
  - List all themes with descriptions
  - Post count and trend direction (↑↓→)
  - Research goal mapping visible
  - Click-through to posts with that theme
  - Sentiment breakdown per theme
  - Reference: `specs/trend-analysis.md` Web Dashboard

- [ ] **9.5 Implement agent directory page**
  - Searchable agent list
  - Sort by karma, activity, name
  - Top themes per agent
  - Recent posts preview
  - Click-through to agent detail view
  - Reference: `specs/trend-analysis.md` Web Dashboard

- [ ] **9.6 Implement data export API endpoints**
  - `GET /api/export/posts.csv` - Posts with metadata (respects 7-day content window)
  - `GET /api/export/agents.csv` - Agent profiles with stats
  - `GET /api/export/themes.csv` - Theme taxonomy and metrics
  - `GET /api/export/snapshots.csv` - Time-series platform metrics
  - All exports include timestamp and data freshness indicator
  - Reference: `specs/trend-analysis.md` Data Export

- [ ] **9.7 Implement database snapshot download**
  - `GET /api/export/database.db` - Full DuckDB file download
  - Requires simple auth token (environment variable)
  - Creates temporary copy to avoid locking
  - Logs all download requests for audit
  - Include README with schema documentation in zip
  - Reference: `specs/trend-analysis.md` Data Export

- [ ] **9.8 Implement sentiment dashboard page**
  - Platform-wide sentiment over time (chart)
  - Sentiment by submolt (heatmap or bar chart)
  - Sentiment by theme
  - Most positive/negative recent posts
  - Reference: `specs/trend-analysis.md` Sentiment Analysis

## Specification Files

### Created Specifications (6 complete)
| Spec | Contents | Acceptance Criteria |
|------|----------|---------------------|
| `specs/security-architecture.md` | Container isolation, reverse proxy, network security | 6 criteria |
| `specs/openclaw-api.md` | API monitoring, data model, theme discovery, research goals | 6 criteria |
| `specs/trend-analysis.md` | Analytics, CLI, sentiment, web dashboard, data export | 9 criteria |
| `specs/data-schema.md` | DuckDB schema (8 tables), views, JSON schemas, retention | 11 criteria |
| `specs/theme-classification.md` | 20 seed themes, classification algorithm, evolution rules | 8 criteria |
| `specs/polling-strategy.md` | Polling intervals, rate limits, backoff, deduplication | 8 criteria |

### Open Questions (Require User Input)

1. **Moltbook API specifics** - Which submolts to monitor? All or specific ones?
   - Default: Monitor all (using `/submolts` endpoint to discover)
   - **Capacity note**: May need to limit if performance becomes an issue
2. ~~**Theme seed list** - Initial themes to bootstrap taxonomy, or start blank?~~
   - RESOLVED: Use 20 seed themes from `specs/theme-classification.md`
3. ~~**LLM configuration** - Which model for classification? Local vs API?~~
   - RESOLVED: Optional local LLM via Ollama (`qwen2.5-coder:7b`), default to rule-based
4. ~~**Data retention policy** - How long to keep post references?~~
   - RESOLVED: **7 days for content**, 90 days for metadata, indefinite for themes/agents/snapshots
5. **Alert thresholds** - When to notify about trending spikes?
   - Current: 3x normal rate for activity, 5x hourly average for themes
   - Need: How to notify? (stdout, file, webhook?)
6. **AI Safety monitoring spec** - What specific alignment-relevant behaviors to track?
   - Current: 4 themes (alignment_discussion, capability_limits, unexpected_behavior, safety_practices)
   - Need: Additional specific behaviors or risk patterns to watch for?
7. **"Real-time" SLA definition** - What latency is acceptable?
   - Current: 5-minute polling interval for `/posts?sort=new`
   - Clarify: Is this sufficient for "real-time feed monitoring"?
8. **Comment classification** - Should comments be theme-classified?
   - Current: Only posts have `themes[]` column in schema
   - Clarify: Add theme classification to comments, or posts only?

## Resolved Inconsistencies

These inconsistencies between specs were identified and resolved:

1. **Domain naming (openclaw vs moltbook)**
   - `specs/security-architecture.md` says "openclaw endpoints"
   - Plan uses `www.moltbook.com`, `api.moltbook.com`
   - **Resolution**: "Moltbook" is the platform; "OpenClaw" is this project name. Domain list in plan is correct.

2. **Rate limiting layers (proxy vs client)**
   - Spec: "Rate limiting at proxy level"
   - Plan: Client-side rate limiter implementation
   - **Resolution**: Both are implemented. Client-side is primary (authoritative), proxy is backup defense.

3. **Theme changelog action types**
   - Spec defines `create`, `merge`, `split`, `deprecate`, `update` but JSON schema only covers first 4
   - **Resolution**: Added `suggest` action for emerging patterns. `update` and `schema_migration` to be documented in schema spec.

4. **Comments theme classification**
   - `comments` table has no `themes` column in schema
   - **Status**: Captured in Open Questions #8. Default: posts only, unless clarified otherwise.

## Implementation Status

### Pre-Implementation Checklist
- [x] All 6 specification files complete and consistent
- [x] IMPLEMENTATION_PLAN.md created with 60 prioritized tasks
- [x] AGENTS.md operational guide created
- [x] Ralph loop scripts configured (loop.sh, PROMPT_plan.md, PROMPT_build.md)
- [x] Phase 1: Foundation & Security Infrastructure (5 tasks)
- [x] Phase 2: Moltbook API Client (6 tasks)
- [ ] Phase 3: DuckDB Data Layer (9 tasks) — includes sentiment, snapshots
- [ ] Phase 4: Dynamic Theme Discovery (10 tasks)
- [ ] Phase 5: CLI Commands - Basic (8 tasks)
- [ ] Phase 6: Analysis & Insights + Advanced CLI (9 tasks)
- [ ] Phase 7: Monitoring & Observability (2 tasks)
- [ ] Phase 8: Remote Access & Operations (2 tasks)
- [ ] Phase 9: Web Dashboard & Data Export (8 tasks) — NEW

## Completed

### Phase 1: Foundation & Security Infrastructure (2026-02-01)
- Created Docker Compose configuration with network isolation (openclaw-internal + openclaw-external)
- Implemented Nginx reverse proxy with domain allowlisting (moltbook.com, github.com)
- Created Python 3.11+ project structure with pyproject.toml
- Implemented health check endpoint (/health) with FastAPI
- Added network isolation verification tests (5 skipped outside Docker, will run in container)
- All 38 tests passing, mypy + ruff checks passing

### Phase 2: Moltbook API Client (2026-02-01)
- Created api_client.py with MoltbookClient class supporting all read-only endpoints
- Created rate_limiter.py with sliding window rate limiting (100/min, 5000/hr, 50000/day)
- Created backoff.py with exponential backoff and error classification
- Created robots.py for robots.txt compliance with caching
- Created deduplication.py for content hash-based deduplication
- Created scheduler.py with APScheduler for adaptive polling
- All 192 tests passing, 5 skipped (Docker-only), mypy + ruff passing

---

## Task Count Summary

| Phase | Tasks | Priority | Changes |
|-------|-------|----------|---------|
| Phase 1: Foundation & Security | 5 | Critical | +1 (health check moved here) |
| Phase 2: Moltbook API Client | 6 | High | Updated rate limit tracking |
| Phase 3: DuckDB Data Layer | 9 | High | +2 (sentiment, snapshots, content storage) |
| Phase 4: Dynamic Theme Discovery | 10 | High | +1 (emerging pattern detection) |
| Phase 5: CLI Commands - Basic | 8 | Medium | Simplified, moved advanced to Phase 6 |
| Phase 6: Analysis & Insights + CLI | 9 | Medium | +3 (network, safety, apps commands) |
| Phase 7: Monitoring & Observability | 2 | Medium | -1 (status command moved to Phase 5) |
| Phase 8: Remote Access & Operations | 2 | Low | -1 (health check moved to Phase 1) |
| Phase 9: Web Dashboard & Data Export | 8 | Medium | **NEW** (FastAPI UI, exports) |
| **Total** | **60** | | +11 net new tasks |

---

## API Reference (from research)

### Moltbook API Base URL
`https://www.moltbook.com/api/v1`

### Read-Only Endpoints (no auth required for public data)
- `GET /posts?sort={hot|new|top|rising}&limit=25`
- `GET /posts/:id`
- `GET /posts/:id/comments?sort={top|new|controversial}`
- `GET /submolts`
- `GET /submolts/:name`
- `GET /agents/profile?name=AGENT_NAME`
- `GET /search?q=query&limit=25`

### Rate Limits
- 100 requests per minute (general)
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Data Models
- Posts: id, title, content/url, submolt, agent_id, created_at, score
- Comments: id, post_id, parent_id, content, agent_id, created_at
- Agents: name, description, karma, created_at
- Submolts: name, display_name, description, subscriber_count

---

## Research Sources

- [Moltbook API Repository](https://github.com/moltbook/api)
- [Moltbook Official Site](https://www.moltbook.com/)
- [Fortune: Moltbook Coverage](https://fortune.com/2026/01/31/ai-agent-moltbot-clawdbot-openclaw-data-privacy-security-nightmare-moltbook-social-network/)
- [Wikipedia: Moltbook](https://en.wikipedia.org/wiki/Moltbook)
- [VentureBeat: OpenClaw Security](https://venturebeat.com/security/openclaw-agentic-ai-security-risk-ciso-guide/)
