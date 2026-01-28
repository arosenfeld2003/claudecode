# Feature: Email Inbox Cleanup (Read-Only Phase)

## Overview

Tame an overflowing inbox by classifying thousands of unread emails into actionable categories. Phase 1 is strictly read-only to review classification accuracy before granting delete permissions.

## Target Account

- **Email**: arosenfeld2003@mac.com
- **Provider**: iCloud Mail (Apple)
- **Protocol**: IMAP (read-only access)
- **Server**: imap.mail.me.com:993 (SSL)

## Jobs To Be Done

1. User can connect iCloud Mail via IMAP with read-only operations
2. User can see a summary of inbox state (total, unread, oldest, newest)
3. User can view emails grouped by sender/domain frequency
4. User can view emails grouped by category (newsletters, promotions, notifications, personal, important)
5. User can review proposed cleanup actions before any destructive operations
6. User can export classification report for manual review

## Acceptance Criteria

### Connection & Permissions
- [ ] IMAP connection uses app-specific password (not main Apple ID password)
- [ ] Connection only performs FETCH operations (no STORE, DELETE, EXPUNGE)
- [ ] Connection status visible in Clawdbot
- [ ] Graceful handling if connection drops or credentials expire

### Inbox Analysis
- [ ] Total email count displayed
- [ ] Unread email count displayed
- [ ] Date range of emails shown (oldest to newest)
- [ ] Processing handles large inboxes (10k+ emails) without timeout

### Classification Output
- [ ] Emails grouped by sender domain with counts
- [ ] Top 20 highest-volume senders identified
- [ ] Categories assigned: newsletter, promotion, notification, transactional, personal, unknown
- [ ] Confidence score for each classification
- [ ] "Safe to delete" vs "review needed" vs "keep" recommendations

### Reporting
- [ ] Summary report generated (markdown or JSON)
- [ ] Report includes sample subjects from each category
- [ ] Report shows proposed actions WITHOUT executing them
- [ ] Report exportable for offline review

## Classification Heuristics

### Safe to Delete (High Confidence)
- **Older than 5 years**: Any email before cutoff date (auto-delete candidate)
- Unsubscribe link present + sender sent 10+ similar emails
- Known promotional domains (marketing platforms, ad networks)
- Auto-generated notifications older than 30 days
- Duplicate emails (same subject + sender within 24h)
- Emails currently in Junk that match spam patterns

### Review Needed (Medium Confidence)
- First-time senders
- Mixed signals (promotional format but from known contact)
- Calendar/event related
- Contains attachments
- **Junk folder rescue**: Emails in Junk that don't match spam patterns

### Keep (Protected)
- Direct replies to emails you sent
- Contains your name in body (not just greeting)
- From contacts in your address book
- Flagged/starred emails
- Recent emails (< 7 days) from unknown senders

## Constraints

- **Read-only only**: No delete, archive, or label modifications in Phase 1
- Gmail API rate limits: Batch requests, respect quotas
- Privacy: Email content processed locally, not sent to external services
- Memory: Don't store full email bodies, only metadata for classification

## Out of Scope (Phase 1)

- Deleting or archiving emails
- Creating Gmail filters
- Unsubscribing from lists
- Processing sent mail or drafts
- Multi-account support

## Phase 2 Preview (Future)

After reviewing Phase 1 classifications:
1. Approve/reject proposed deletions by category
2. Enable STORE/DELETE commands in implementation
3. Execute bulk cleanup (move to Trash first, not permanent delete)
4. Set up recurring maintenance runs
5. Consider Apple Mail rules for ongoing filtering

## Setup Checklist

1. [ ] Generate app-specific password at appleid.apple.com
2. [ ] Store credentials securely (not in plaintext config)
3. [ ] Test IMAP connection with read-only operations
4. [ ] Configure Clawdbot iCloud/IMAP integration
5. [ ] Run initial inbox scan
6. [ ] Review classification report

## Example Output

```
## Scan Summary
- Account: arosenfeld2003@mac.com
- Folders scanned: INBOX, Junk
- Date range: 2021-01-28 to 2026-01-28 (5 years)
- Total emails: 14,523
  - INBOX: 12,847 (read: 4,613 / unread: 8,234)
  - Junk: 1,676

## Age-Based Cleanup
- Older than 5 years: 2,341 emails (AUTO-DELETE CANDIDATES)

## Top Senders (by volume)
1. notifications@linkedin.com - 847 emails (SAFE TO DELETE)
2. noreply@medium.com - 623 emails (SAFE TO DELETE)
3. hello@substack.com - 412 emails (REVIEW - some subscribed)
4. no-reply@accounts.google.com - 234 emails (KEEP - security)
5. amazon@amazon.com - 198 emails (REVIEW - mixed orders/promos)

## Category Breakdown
- Newsletters: 3,421 (SAFE: 2,890 / REVIEW: 531)
- Promotions: 2,156 (SAFE: 2,156)
- Notifications: 1,847 (SAFE: 1,203 / REVIEW: 644)
- Transactional: 892 (KEEP: 892)
- Personal: 234 (KEEP: 234)
- Unknown: 97 (REVIEW: 97)

## Junk Folder Analysis
- Confirmed spam: 1,542 (SAFE TO DELETE)
- Potential rescues: 134 (REVIEW - may be legitimate)

## Recommended Actions (NOT EXECUTED)
- Delete 8,590 emails (59% of total)
  - Age-based: 2,341
  - Spam/promotional: 6,249
- Review 1,406 emails before deciding
- Keep 1,126 emails (protected)
- Rescue from Junk: 134 candidates
```

## Scan Parameters

- **Time range**: Last 5 years (emails older than 5 years → auto-delete candidates)
- **Read status**: All emails (read and unread)
- **Folders**: INBOX and Junk (important emails sometimes land in Junk)
- **Output format**: TBD (Markdown, JSON, or CSV)

## IMAP Read-Only Enforcement

To ensure Phase 1 is truly read-only, the implementation must:
1. **Never issue**: STORE, DELETE, EXPUNGE, COPY, MOVE commands
2. **Only use**: SELECT (not EXAMINE for extra safety), FETCH, SEARCH, LIST
3. **Log all commands**: Audit trail of every IMAP operation
4. **Credential scope**: App-specific password can't be scoped, so enforcement is in code

## References

- iCloud IMAP settings: https://support.apple.com/en-us/102525
- App-specific passwords: https://support.apple.com/en-us/HT204397
- IMAP protocol: RFC 3501
- Clawdbot email integration: Check docs for IMAP setup
