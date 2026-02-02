# OpenClaw Moltbook Monitor

## Project Goal

Safely monitor and analyze the OpenClaw/Moltbook platform (agents communicating in an open world) to identify trends for building developer tools, security applications, and agent alignment research tools. All monitoring runs in Docker containers - NEVER local, NEVER sharing credentials.

## Tech Stack

- **Python 3.12** - Data analysis, web scraping, ML/AI tooling
- **Docker** - Mandatory isolation for all monitoring operations
- **DuckDB** - Analytical database for trend analysis (reference-based storage for scalability)
- **Typer** - CLI framework
- **httpx** - Async HTTP client
- **Rich** - Terminal visualizations
- **Tailscale** - Remote monitoring access (tmux/Claude app integration)
- **Nginx/Caddy** - Reverse proxy for additional network security layer

## Security Constraints

**CRITICAL - These are non-negotiable:**
- All monitoring runs inside Docker containers
- No credentials shared with any external services
- No local execution of untrusted code
- Network isolation from host system via reverse proxy
- All outbound traffic routed through reverse proxy container
- Read-only access to external platforms
- No direct container-to-internet connections (proxy only)

## Network Architecture

```
[Host] <--Tailscale--> [Remote Access]
   |
   v
[Reverse Proxy Container] <-- All traffic routes here
   |
   v
[Monitor Container(s)] -- No direct internet access
   |
   v
[DuckDB Volume] -- Metadata & references (not full content)
```

## Build & Run

```bash
# Build Docker containers
docker compose build

# Run monitoring CLI
docker compose run --rm monitor [command]

# Remote access via Tailscale
# (TBD - Ralph will configure)
```

## Validation

- Tests: `docker compose run --rm monitor pytest`
- Typecheck: `docker compose run --rm monitor mypy src/`
- Lint: `docker compose run --rm monitor ruff check src/`

## Operational Notes

_Ralph will update this section as it learns about the codebase._

### Codebase Patterns

_Document patterns as they emerge._

### OpenClaw API Notes

_Document API findings here._
