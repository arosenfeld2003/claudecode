# Security Architecture

## Overview

Ensure all monitoring operations are isolated, sandboxed, and cannot leak credentials or execute malicious code on the host system.

## Requirements

### Container Isolation
- Monitor containers have NO direct internet access
- All outbound traffic MUST route through reverse proxy container
- No volume mounts to sensitive host directories
- Read-only root filesystem where possible
- Non-root user inside containers

### Reverse Proxy (Nginx/Caddy)
- Only component with outbound internet access
- Allowlist of permitted domains (github.com, openclaw endpoints)
- Request logging for audit trail
- Rate limiting at proxy level
- TLS verification for all outbound connections

### Network Architecture
```
┌─────────────────────────────────────────────────────┐
│ Docker Network: openclaw-internal (no external)    │
│  ┌─────────────┐    ┌─────────────────────────┐    │
│  │  Monitor    │───▶│  Reverse Proxy          │────┼──▶ Internet
│  │  Container  │    │  (allowlist only)       │    │    (allowlisted)
│  └─────────────┘    └─────────────────────────┘    │
│        │                                            │
│        ▼                                            │
│  ┌─────────────┐                                    │
│  │  DuckDB     │                                    │
│  │  (refs+tags)│                                    │
│  └─────────────┘                                    │
└─────────────────────────────────────────────────────┘
```

### Credential Safety
- No credentials in environment variables
- No credentials in container images
- No credentials mounted as volumes
- If LLM classification used: API key passed securely at runtime

### Remote Access (Tailscale)
- Tailscale runs on HOST, not in containers
- SSH/tmux access to host for monitoring
- Containers accessible only via docker compose commands
- No exposed ports to public internet

## Acceptance Criteria

- [ ] Monitor container cannot reach internet directly
- [ ] Only allowlisted domains accessible through proxy
- [ ] All requests logged with timestamps
- [ ] No credentials in image or runtime
- [ ] `docker compose` enforces network isolation
- [ ] Tailscale provides remote access without exposing containers
