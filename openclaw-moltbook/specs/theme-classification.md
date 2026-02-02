# Theme Classification Specification

## Overview

Dynamic theme discovery and classification system for categorizing Moltbook posts according to research goals. Uses rule-based classification as the default, with optional LLM enhancement.

## Research Goals (Primary Categories)

All themes must map to at least one research goal:

| Goal ID | Name | Description |
|---------|------|-------------|
| `social_network` | Agent Social Network Study | How agents interact, form relationships, coordinate |
| `trends` | Trend Identification | Emerging patterns relevant to research community |
| `developer_tooling` | Developer Tooling | Tools that improve human-agent collaboration |
| `ai_safety` | AI Safety & Alignment | Alignment-relevant behaviors, risks, best practices |
| `mobile_apps` | Mobile App Ideas | Quick-to-build mobile app opportunities |

## Seed Themes

Initial theme taxonomy to bootstrap classification:

### Social Network Themes
| Theme | Keywords | Description |
|-------|----------|-------------|
| `agent_collaboration` | collaborate, team, together, joint, partnership | Agents working together on tasks |
| `agent_conflict` | disagree, conflict, argument, debate, dispute | Disagreements between agents |
| `agent_hierarchy` | lead, follow, boss, subordinate, delegate | Power dynamics between agents |
| `agent_reputation` | trust, reputation, reliable, karma, respect | Trust and reputation signals |

### Trend Themes
| Theme | Keywords | Description |
|-------|----------|-------------|
| `emerging_tech` | new, breakthrough, innovation, cutting-edge | New technologies being discussed |
| `industry_news` | announcement, release, launch, update | Industry news and announcements |
| `hot_debate` | controversial, debate, opinion, disagree | Heated discussions |
| `viral_content` | trending, popular, viral, everyone | Widely shared content |

### Developer Tooling Themes
| Theme | Keywords | Description |
|-------|----------|-------------|
| `code_assistance` | code, debug, fix, implement, refactor | Coding help requests/responses |
| `workflow_automation` | automate, script, workflow, pipeline | Automation discussions |
| `integration_requests` | integrate, connect, API, plugin, extension | Integration needs |
| `documentation` | docs, readme, guide, tutorial, explain | Documentation discussions |

### AI Safety Themes
| Theme | Keywords | Description |
|-------|----------|-------------|
| `alignment_discussion` | alignment, values, ethics, moral, safe | Alignment-relevant discussions |
| `capability_limits` | can't, limitation, boundary, refuse | Capability boundaries |
| `unexpected_behavior` | unexpected, surprising, weird, strange | Unexpected agent behaviors |
| `safety_practices` | safety, guardrail, protection, prevent | Safety best practices |

### Mobile App Themes
| Theme | Keywords | Description |
|-------|----------|-------------|
| `app_requests` | app, mobile, phone, iOS, Android | Mobile app requests |
| `pain_points` | frustrating, annoying, wish, need | User pain points |
| `monetization` | pay, subscribe, premium, revenue | Monetization signals |
| `quick_wins` | simple, easy, quick, basic | Low-complexity opportunities |

## Rule-Based Classification Algorithm

### Step 1: Keyword Matching

```python
def calculate_theme_score(content: str, theme: Theme) -> float:
    """
    Calculate match score for a theme based on keyword presence.
    Returns: 0.0 to 1.0
    """
    content_lower = content.lower()
    words = set(content_lower.split())

    # Direct keyword matches
    keyword_matches = sum(1 for kw in theme.keywords if kw in content_lower)

    # Weighted by keyword specificity (rarer keywords score higher)
    weighted_score = sum(
        theme.keyword_weights.get(kw, 1.0)
        for kw in theme.keywords
        if kw in content_lower
    )

    # Normalize to 0-1 range
    max_possible = sum(theme.keyword_weights.values())
    return min(1.0, weighted_score / max_possible) if max_possible > 0 else 0.0
```

### Step 2: Confidence Scoring

```python
def calculate_confidence(scores: dict[str, float]) -> tuple[list[str], float]:
    """
    Determine which themes to assign and overall confidence.
    """
    # Threshold for theme assignment
    ASSIGNMENT_THRESHOLD = 0.3

    # Sort themes by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Assign themes above threshold
    assigned = [theme for theme, score in ranked if score >= ASSIGNMENT_THRESHOLD]

    # Confidence = highest score (or average of top 2 if close)
    if len(ranked) >= 2 and ranked[0][1] - ranked[1][1] < 0.1:
        confidence = (ranked[0][1] + ranked[1][1]) / 2
    else:
        confidence = ranked[0][1] if ranked else 0.0

    return assigned[:5], confidence  # Max 5 themes per post
```

### Step 3: Research Goal Mapping

Each assigned theme automatically maps to its research goal(s). A post's research goal relevance is the union of all assigned themes' goals.

## Theme Taxonomy Evolution

### Split Detection

A theme should be **split** when:
- Post count > 100 AND
- Keyword co-occurrence analysis shows distinct clusters AND
- Intra-cluster similarity < 0.5

```python
SPLIT_THRESHOLD = {
    'min_posts': 100,
    'max_variance': 0.5,  # If posts under theme are too different
    'min_cluster_size': 20  # Each new theme needs enough posts
}
```

### Merge Detection

Themes should be **merged** when:
- Jaccard similarity of assigned posts > 0.7 AND
- Keyword overlap > 50% AND
- Both serve same research goals

```python
MERGE_THRESHOLD = {
    'min_jaccard': 0.7,
    'min_keyword_overlap': 0.5,
    'same_research_goals': True
}
```

### Deprecation Detection

A theme should be **deprecated** when:
- No posts assigned in last 30 days AND
- Total post count < 10 OR
- Research goal no longer relevant

```python
DEPRECATION_THRESHOLD = {
    'inactive_days': 30,
    'min_posts': 10
}
```

### Changelog Format

All taxonomy changes logged to `theme_changelog`:

```json
{
    "action": "split",
    "theme_name": "code_assistance",
    "details": {
        "split_into": ["code_debugging", "code_generation", "code_review"],
        "reason": "High variance detected - posts cluster around 3 distinct use cases",
        "post_redistribution": {
            "code_debugging": 45,
            "code_generation": 38,
            "code_review": 22
        }
    }
}
```

## LLM Enhancement (Optional)

When local LLM is available (Ollama), enhance classification:

### Prompt Template

```
Analyze this Moltbook post and suggest themes.

POST CONTENT:
{content}

AVAILABLE THEMES:
{theme_list_with_descriptions}

RESEARCH GOALS:
- social_network: Agent interaction patterns
- trends: Emerging patterns
- developer_tooling: Development tools
- ai_safety: Alignment and safety
- mobile_apps: Mobile app opportunities

Respond with JSON:
{
    "themes": ["theme1", "theme2"],
    "confidence": 0.85,
    "new_theme_suggestion": null | {"name": "...", "description": "...", "goal": "..."}
}
```

### LLM Configuration

```yaml
model: qwen2.5-coder:7b  # Or other Ollama-compatible model
temperature: 0.3  # Low for consistent classification
max_tokens: 200
timeout_seconds: 10
fallback_on_timeout: true  # Use rule-based if LLM slow
```

### Security Requirements

- API key passed via runtime environment variable (not in image)
- LLM runs locally via Ollama (no external API calls)
- All prompts/responses logged for audit

## Performance Requirements

| Metric | Target |
|--------|--------|
| Classification latency (rule-based) | < 10ms per post |
| Classification latency (LLM) | < 2s per post |
| Batch processing | 100 posts/second (rule-based) |
| Theme taxonomy size | < 100 active themes |

## Acceptance Criteria

- [ ] Seed themes loaded on first run
- [ ] Rule-based classification functional without LLM
- [ ] Confidence scores between 0.0 and 1.0
- [ ] Each theme maps to at least one research goal
- [ ] Split/merge/deprecate proposals logged for human review
- [ ] LLM enhancement optional and gracefully degrades
- [ ] All taxonomy changes auditable via changelog
