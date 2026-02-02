# Polling Strategy Specification

## Overview

Defines how the monitor fetches data from the Moltbook API while respecting rate limits, handling errors gracefully, and avoiding duplicate processing.

## Rate Limits

### Moltbook API Limits

| Limit | Value |
|-------|-------|
| Requests per minute | 100 |
| Requests per hour | 5,000 |
| Requests per day | 50,000 |

### Headers to Track

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1706745600
```

## Polling Intervals

### Default Intervals by Endpoint

| Endpoint | Interval | Rationale |
|----------|----------|-----------|
| `/posts?sort=new` | 5 minutes | Catch new posts quickly |
| `/posts?sort=hot` | 15 minutes | Trending changes slowly |
| `/posts?sort=top` | 1 hour | Top is stable |
| `/submolts` | 6 hours | Community list rarely changes |
| `/posts/:id/comments` | On-demand | Only when analyzing specific post |
| `/agents/profile` | On-demand | Only when agent first seen |

### Adaptive Intervals

Adjust based on activity:

```python
def calculate_next_interval(endpoint: str, base_interval: int, activity_rate: float) -> int:
    """
    Adjust polling interval based on recent activity.

    activity_rate: posts per minute in last window
    """
    if activity_rate > 10:
        # High activity: poll more frequently (min 1 minute)
        return max(60, base_interval // 2)
    elif activity_rate < 1:
        # Low activity: poll less frequently (max 30 minutes)
        return min(1800, base_interval * 2)
    else:
        return base_interval
```

## Request Budget Management

### Budget Allocation

With 100 req/min limit, allocate:

| Category | Budget | Purpose |
|----------|--------|---------|
| New posts | 40% | Primary monitoring |
| Trending | 20% | Hot posts |
| Comments | 20% | Conversation depth |
| Agents | 10% | Profile enrichment |
| Reserve | 10% | Burst capacity |

### Budget Enforcement

```python
class RateLimiter:
    def __init__(self, max_per_minute: int = 100):
        self.max_per_minute = max_per_minute
        self.requests = []  # Timestamps

    def can_request(self) -> bool:
        now = time.time()
        # Remove requests older than 1 minute
        self.requests = [t for t in self.requests if now - t < 60]
        return len(self.requests) < self.max_per_minute

    def wait_time(self) -> float:
        if self.can_request():
            return 0
        oldest = min(self.requests)
        return 60 - (time.time() - oldest)

    def record_request(self):
        self.requests.append(time.time())
```

## Error Handling & Backoff

### Error Categories

| HTTP Status | Category | Action |
|-------------|----------|--------|
| 200-299 | Success | Continue normally |
| 429 | Rate Limited | Exponential backoff, respect Retry-After |
| 500-599 | Server Error | Exponential backoff |
| 400-499 | Client Error | Log and skip (don't retry) |
| Timeout | Network | Linear backoff |

### Exponential Backoff

```python
def calculate_backoff(error_count: int, base_delay: float = 1.0) -> float:
    """
    Calculate backoff delay with jitter.

    Returns delay in seconds, capped at 5 minutes.
    """
    delay = base_delay * (2 ** min(error_count, 8))  # Cap exponent
    jitter = random.uniform(0.8, 1.2)
    return min(300, delay * jitter)  # Max 5 minutes
```

### Recovery

After successful request:
- Reset error count to 0
- Resume normal polling interval

## Deduplication Strategy

### Content Hash Generation

```python
import hashlib

def generate_content_hash(post: dict) -> str:
    """
    Generate SHA-256 hash for post deduplication.
    Uses stable fields only (not score, which changes).
    """
    content = f"{post['id']}:{post['agent_id']}:{post['title']}:{post['submolt']}"
    return hashlib.sha256(content.encode()).hexdigest()
```

### Last-Seen Tracking

Track last seen post ID per endpoint:

```sql
-- Check before processing
SELECT last_post_id FROM poll_state WHERE endpoint = '/posts?sort=new';

-- Update after processing
UPDATE poll_state
SET last_post_id = ?,
    last_poll_at = NOW(),
    next_poll_at = NOW() + INTERVAL '5 minutes',
    error_count = 0
WHERE endpoint = '/posts?sort=new';
```

### Dedup Decision Flow

```
1. Fetch new posts from API
2. For each post:
   a. Check if post.id exists in posts table → skip if exists
   b. Calculate content_hash
   c. Check if content_hash exists → skip if duplicate content
   d. Process and store if new
3. Update last_post_id to newest seen
```

## Spike Detection

### Thresholds

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Activity spike | 3x normal rate | Increase polling frequency |
| Trending surge | Theme activity 5x hourly average | Flag for analysis |
| Viral content | Single post gets 10x comments | Deep fetch comments |

### Spike Calculation

```python
def is_spiking(current_rate: float, historical_avg: float, threshold: float = 3.0) -> bool:
    """
    Detect activity spikes.

    current_rate: posts/comments per hour in last interval
    historical_avg: 7-day average for same metric
    threshold: multiplier to consider a spike
    """
    if historical_avg == 0:
        return current_rate > 10  # Absolute threshold for new monitoring
    return current_rate > historical_avg * threshold
```

## robots.txt Compliance

### Fetch on Startup

```python
async def fetch_robots_txt(base_url: str) -> dict:
    """
    Fetch and parse robots.txt for compliance.
    """
    response = await client.get(f"{base_url}/robots.txt")
    # Parse and return allowed/disallowed paths
    return parse_robots_txt(response.text)
```

### Respect Rules

- Cache robots.txt for 24 hours
- Honor Crawl-delay if specified
- Skip disallowed paths
- Identify as: `User-Agent: OpenClawMonitor/1.0 (research purposes)`

## Poll State Persistence

### State Table Usage

```sql
-- On startup: load state
SELECT * FROM poll_state;

-- After each poll cycle: update
INSERT OR REPLACE INTO poll_state (
    endpoint,
    last_post_id,
    last_poll_at,
    next_poll_at,
    error_count,
    last_error
) VALUES (?, ?, ?, ?, ?, ?);
```

### Graceful Shutdown

On SIGTERM/SIGINT:
1. Complete current request
2. Persist poll state
3. Exit cleanly

## Monitoring Metrics

### Metrics to Track

| Metric | Type | Purpose |
|--------|------|---------|
| `requests_total` | Counter | Total API requests |
| `requests_failed` | Counter | Failed requests by error type |
| `rate_limit_hits` | Counter | Times hit rate limit |
| `posts_processed` | Counter | Posts successfully processed |
| `duplicates_skipped` | Counter | Duplicate posts skipped |
| `poll_latency_ms` | Histogram | Time per poll cycle |
| `backoff_seconds` | Gauge | Current backoff delay |

### Logging Format

```json
{
    "timestamp": "2026-01-31T10:00:00Z",
    "level": "info",
    "event": "poll_complete",
    "endpoint": "/posts?sort=new",
    "posts_fetched": 25,
    "posts_new": 5,
    "duplicates": 20,
    "latency_ms": 342,
    "rate_limit_remaining": 85
}
```

## Acceptance Criteria

- [ ] Respects 100 req/min rate limit
- [ ] Tracks rate limit headers from API responses
- [ ] Implements exponential backoff on errors
- [ ] Deduplicates posts by ID and content hash
- [ ] Persists poll state across restarts
- [ ] Respects robots.txt rules
- [ ] Detects and responds to activity spikes
- [ ] All poll activity logged for audit
