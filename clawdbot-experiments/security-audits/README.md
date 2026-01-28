# Security Audits

This directory tracks Clawdbot security audits over time.

## Running an Audit

```bash
# Basic audit
./clawdbot.sh security audit

# Deep audit (probes gateway)
./clawdbot.sh security audit --deep

# Auto-fix issues
./clawdbot.sh security audit --fix
```

## Audit Schedule

Run audits:
- After any configuration changes
- After adding/removing channels
- After enabling new skills or plugins
- After updating Clawdbot version
- Monthly as routine check

## File Naming

`YYYY-MM-DD.md` - One file per audit date.

## Severity Levels

| Level | Meaning |
|-------|---------|
| Critical | Immediate action required - active vulnerability |
| Warning | Should address - potential risk |
| Info | Awareness only - no action needed |
