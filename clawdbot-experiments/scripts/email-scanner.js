#!/usr/bin/env node
/**
 * iCloud Email Scanner (Read-Only)
 *
 * Connects to iCloud IMAP and generates a classification report
 * WITHOUT modifying any emails.
 *
 * Usage:
 *   ICLOUD_EMAIL=you@mac.com ICLOUD_APP_PASSWORD=xxxx node email-scanner.js
 *
 * Or with .env file:
 *   node email-scanner.js
 */

const Imap = require('imap');
const { simpleParser } = require('mailparser');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
  email: process.env.ICLOUD_EMAIL || 'arosenfeld2003@mac.com',
  password: process.env.ICLOUD_APP_PASSWORD,
  host: 'imap.mail.me.com',
  port: 993,
  tls: true,
  // Scan parameters
  yearsBack: 5,
  folders: ['INBOX', 'Junk'],
  // Output
  outputDir: process.env.OUTPUT_DIR || '/home/clawdbot/reports',
};

// Validate required config
if (!CONFIG.password) {
  console.error('ERROR: ICLOUD_APP_PASSWORD environment variable required');
  console.error('Generate one at: https://appleid.apple.com → Security → App-Specific Passwords');
  process.exit(1);
}

// Classification patterns
const PATTERNS = {
  newsletter: [
    /unsubscribe/i,
    /email preferences/i,
    /manage subscriptions/i,
    /newsletter/i,
    /weekly digest/i,
    /daily digest/i,
  ],
  promotion: [
    /% off/i,
    /sale ends/i,
    /limited time/i,
    /discount code/i,
    /promo code/i,
    /free shipping/i,
    /shop now/i,
    /buy now/i,
  ],
  notification: [
    /notification/i,
    /alert/i,
    /your order/i,
    /shipping confirmation/i,
    /delivery update/i,
    /password reset/i,
    /verify your/i,
    /confirm your/i,
  ],
  transactional: [
    /receipt/i,
    /invoice/i,
    /payment/i,
    /statement/i,
    /order confirmation/i,
    /booking confirmation/i,
  ],
};

// Known high-volume senders (likely safe to bulk delete)
const BULK_SENDERS = [
  'linkedin.com',
  'facebookmail.com',
  'twitter.com',
  'x.com',
  'medium.com',
  'substack.com',
  'quora.com',
  'pinterest.com',
  'instagram.com',
  'tiktok.com',
  'marketing',
  'noreply',
  'no-reply',
  'notifications',
  'newsletter',
  'promo',
  'offers',
];

// Stats collection
const stats = {
  total: 0,
  byFolder: {},
  bySender: {},
  byDomain: {},
  byCategory: {
    newsletter: [],
    promotion: [],
    notification: [],
    transactional: [],
    personal: [],
    unknown: [],
  },
  byAge: {
    older_than_5_years: [],
    last_5_years: [],
    last_year: [],
    last_month: [],
    last_week: [],
  },
  recommendations: {
    safe_to_delete: [],
    review_needed: [],
    keep: [],
  },
};

/**
 * Classify an email based on headers and content hints
 */
function classifyEmail(email) {
  const subject = email.subject || '';
  const from = email.from || '';
  const hasUnsubscribe = email.headers?.['list-unsubscribe'] ? true : false;

  // Check patterns
  for (const [category, patterns] of Object.entries(PATTERNS)) {
    for (const pattern of patterns) {
      if (pattern.test(subject)) {
        return category;
      }
    }
  }

  // Has unsubscribe header = likely newsletter/promotion
  if (hasUnsubscribe) {
    return 'newsletter';
  }

  // Check if from bulk sender domain
  const fromLower = from.toLowerCase();
  if (BULK_SENDERS.some(s => fromLower.includes(s))) {
    return 'promotion';
  }

  // Default
  return 'unknown';
}

/**
 * Determine if email is safe to delete
 */
function getRecommendation(email, category) {
  const dominated = email.senderCount > 10;
  const hasUnsubscribe = email.headers?.['list-unsubscribe'] ? true : false;
  const isOld = email.ageYears > 5;
  const isFromBulkSender = BULK_SENDERS.some(s =>
    (email.from || '').toLowerCase().includes(s)
  );

  // Safe to delete
  if (isOld) return 'safe_to_delete';
  if (category === 'promotion' && dominated) return 'safe_to_delete';
  if (category === 'newsletter' && dominated && hasUnsubscribe) return 'safe_to_delete';
  if (category === 'notification' && email.ageYears > 1) return 'safe_to_delete';

  // Keep
  if (category === 'transactional' && email.ageYears < 2) return 'keep';
  if (category === 'personal') return 'keep';

  // Review
  return 'review_needed';
}

/**
 * Connect to IMAP and scan folders
 */
async function scanEmails() {
  console.log('📧 iCloud Email Scanner (Read-Only Mode)');
  console.log('=========================================');
  console.log(`Account: ${CONFIG.email}`);
  console.log(`Folders: ${CONFIG.folders.join(', ')}`);
  console.log(`Lookback: ${CONFIG.yearsBack} years`);
  console.log('');

  const imap = new Imap({
    user: CONFIG.email,
    password: CONFIG.password,
    host: CONFIG.host,
    port: CONFIG.port,
    tls: CONFIG.tls,
    tlsOptions: { rejectUnauthorized: true },
  });

  return new Promise((resolve, reject) => {
    imap.once('ready', async () => {
      console.log('✅ Connected to iCloud IMAP');

      try {
        for (const folder of CONFIG.folders) {
          await scanFolder(imap, folder);
        }

        imap.end();
        resolve();
      } catch (err) {
        imap.end();
        reject(err);
      }
    });

    imap.once('error', (err) => {
      console.error('❌ IMAP Error:', err.message);
      reject(err);
    });

    imap.once('end', () => {
      console.log('📪 Disconnected from IMAP');
    });

    console.log('🔌 Connecting to iCloud IMAP...');
    imap.connect();
  });
}

/**
 * Scan a single folder
 */
function scanFolder(imap, folderName) {
  return new Promise((resolve, reject) => {
    // Open folder in read-only mode
    imap.openBox(folderName, true, (err, box) => {
      if (err) {
        console.warn(`⚠️  Could not open ${folderName}: ${err.message}`);
        resolve(); // Continue with other folders
        return;
      }

      console.log(`\n📂 Scanning ${folderName} (${box.messages.total} messages)...`);
      stats.byFolder[folderName] = { total: box.messages.total, scanned: 0 };

      if (box.messages.total === 0) {
        resolve();
        return;
      }

      // Calculate date range (5 years back)
      const sinceDate = new Date();
      sinceDate.setFullYear(sinceDate.getFullYear() - CONFIG.yearsBack);
      const sinceDateStr = sinceDate.toISOString().split('T')[0];

      // Search for emails in date range
      imap.search([['SINCE', sinceDateStr]], (err, results) => {
        if (err) {
          console.warn(`⚠️  Search failed in ${folderName}: ${err.message}`);
          resolve();
          return;
        }

        if (!results || results.length === 0) {
          console.log(`   No messages in date range`);
          resolve();
          return;
        }

        console.log(`   Found ${results.length} messages since ${sinceDateStr}`);

        // Fetch headers only (not full body - faster and less data)
        const fetch = imap.fetch(results, {
          bodies: 'HEADER.FIELDS (FROM TO SUBJECT DATE LIST-UNSUBSCRIBE)',
          struct: false,
        });

        let processed = 0;

        fetch.on('message', (msg, seqno) => {
          msg.on('body', (stream, info) => {
            let buffer = '';
            stream.on('data', (chunk) => {
              buffer += chunk.toString('utf8');
            });
            stream.on('end', () => {
              try {
                const headers = Imap.parseHeader(buffer);
                processEmail({
                  folder: folderName,
                  seqno,
                  from: headers.from?.[0] || 'unknown',
                  to: headers.to?.[0] || '',
                  subject: headers.subject?.[0] || '(no subject)',
                  date: headers.date?.[0] ? new Date(headers.date[0]) : new Date(),
                  headers: {
                    'list-unsubscribe': headers['list-unsubscribe']?.[0],
                  },
                });
                processed++;
                if (processed % 500 === 0) {
                  console.log(`   Processed ${processed}/${results.length}...`);
                }
              } catch (e) {
                // Skip unparseable emails
              }
            });
          });
        });

        fetch.once('error', (err) => {
          console.warn(`⚠️  Fetch error: ${err.message}`);
        });

        fetch.once('end', () => {
          stats.byFolder[folderName].scanned = processed;
          console.log(`   ✅ Processed ${processed} messages`);
          resolve();
        });
      });
    });
  });
}

/**
 * Process a single email and update stats
 */
function processEmail(email) {
  stats.total++;

  // Extract domain from sender
  const fromMatch = email.from.match(/@([^>]+)/);
  const domain = fromMatch ? fromMatch[1].toLowerCase() : 'unknown';

  // Track by sender
  if (!stats.bySender[email.from]) {
    stats.bySender[email.from] = { count: 0, subjects: [] };
  }
  stats.bySender[email.from].count++;
  if (stats.bySender[email.from].subjects.length < 3) {
    stats.bySender[email.from].subjects.push(email.subject.substring(0, 60));
  }

  // Track by domain
  if (!stats.byDomain[domain]) {
    stats.byDomain[domain] = 0;
  }
  stats.byDomain[domain]++;

  // Calculate age
  const now = new Date();
  const ageMs = now - email.date;
  const ageDays = ageMs / (1000 * 60 * 60 * 24);
  const ageYears = ageDays / 365;

  email.ageYears = ageYears;
  email.senderCount = stats.bySender[email.from].count;

  // Age buckets
  if (ageYears > 5) {
    stats.byAge.older_than_5_years.push(email);
  } else if (ageYears > 1) {
    stats.byAge.last_5_years.push(email);
  } else if (ageDays > 30) {
    stats.byAge.last_year.push(email);
  } else if (ageDays > 7) {
    stats.byAge.last_month.push(email);
  } else {
    stats.byAge.last_week.push(email);
  }

  // Classify
  const category = classifyEmail(email);
  stats.byCategory[category].push({
    from: email.from,
    subject: email.subject.substring(0, 80),
    date: email.date.toISOString().split('T')[0],
    folder: email.folder,
  });

  // Recommendation
  const rec = getRecommendation(email, category);
  stats.recommendations[rec].push({
    from: email.from,
    subject: email.subject.substring(0, 60),
    date: email.date.toISOString().split('T')[0],
    category,
    folder: email.folder,
  });
}

/**
 * Generate report
 */
function generateReport() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const reportPath = path.join(CONFIG.outputDir, `email-report-${timestamp}.md`);

  // Ensure output dir exists
  if (!fs.existsSync(CONFIG.outputDir)) {
    fs.mkdirSync(CONFIG.outputDir, { recursive: true });
  }

  // Sort senders by count
  const topSenders = Object.entries(stats.bySender)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 30);

  // Sort domains by count
  const topDomains = Object.entries(stats.byDomain)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20);

  let report = `# Email Inbox Report

**Generated**: ${new Date().toISOString()}
**Account**: ${CONFIG.email}
**Scan Range**: Last ${CONFIG.yearsBack} years

## Summary

| Metric | Count |
|--------|-------|
| Total Scanned | ${stats.total} |
| Safe to Delete | ${stats.recommendations.safe_to_delete.length} |
| Review Needed | ${stats.recommendations.review_needed.length} |
| Keep | ${stats.recommendations.keep.length} |

### Potential Cleanup

**${stats.recommendations.safe_to_delete.length}** emails (${Math.round(stats.recommendations.safe_to_delete.length / stats.total * 100)}%) identified as safe to delete.

---

## By Folder

| Folder | Total | Scanned |
|--------|-------|---------|
${Object.entries(stats.byFolder).map(([f, s]) => `| ${f} | ${s.total} | ${s.scanned} |`).join('\n')}

---

## By Category

| Category | Count | % |
|----------|-------|---|
| Newsletter | ${stats.byCategory.newsletter.length} | ${Math.round(stats.byCategory.newsletter.length / stats.total * 100)}% |
| Promotion | ${stats.byCategory.promotion.length} | ${Math.round(stats.byCategory.promotion.length / stats.total * 100)}% |
| Notification | ${stats.byCategory.notification.length} | ${Math.round(stats.byCategory.notification.length / stats.total * 100)}% |
| Transactional | ${stats.byCategory.transactional.length} | ${Math.round(stats.byCategory.transactional.length / stats.total * 100)}% |
| Personal | ${stats.byCategory.personal.length} | ${Math.round(stats.byCategory.personal.length / stats.total * 100)}% |
| Unknown | ${stats.byCategory.unknown.length} | ${Math.round(stats.byCategory.unknown.length / stats.total * 100)}% |

---

## By Age

| Period | Count |
|--------|-------|
| Older than 5 years | ${stats.byAge.older_than_5_years.length} |
| 1-5 years | ${stats.byAge.last_5_years.length} |
| 1-12 months | ${stats.byAge.last_year.length} |
| 1-4 weeks | ${stats.byAge.last_month.length} |
| Last week | ${stats.byAge.last_week.length} |

---

## Top 30 Senders (by volume)

| Sender | Count | Sample Subjects |
|--------|-------|-----------------|
${topSenders.map(([sender, data]) => {
  const shortSender = sender.length > 50 ? sender.substring(0, 47) + '...' : sender;
  return `| ${shortSender} | ${data.count} | ${data.subjects[0] || ''} |`;
}).join('\n')}

---

## Top 20 Domains (by volume)

| Domain | Count |
|--------|-------|
${topDomains.map(([domain, count]) => `| ${domain} | ${count} |`).join('\n')}

---

## Recommendations

### Safe to Delete (sample of first 50)

| From | Subject | Date | Category |
|------|---------|------|----------|
${stats.recommendations.safe_to_delete.slice(0, 50).map(e =>
  `| ${e.from.substring(0, 40)} | ${e.subject} | ${e.date} | ${e.category} |`
).join('\n')}

### Review Needed (sample of first 50)

| From | Subject | Date | Category |
|------|---------|------|----------|
${stats.recommendations.review_needed.slice(0, 50).map(e =>
  `| ${e.from.substring(0, 40)} | ${e.subject} | ${e.date} | ${e.category} |`
).join('\n')}

---

## Next Steps

1. Review the "Safe to Delete" list above
2. Check "Review Needed" for false positives
3. When satisfied, proceed to Phase 2 (with delete permissions)

**This report was generated in READ-ONLY mode. No emails were modified.**
`;

  fs.writeFileSync(reportPath, report);
  console.log(`\n📄 Report saved to: ${reportPath}`);

  // Also output summary to console
  console.log('\n========== SUMMARY ==========');
  console.log(`Total scanned: ${stats.total}`);
  console.log(`Safe to delete: ${stats.recommendations.safe_to_delete.length} (${Math.round(stats.recommendations.safe_to_delete.length / stats.total * 100)}%)`);
  console.log(`Review needed: ${stats.recommendations.review_needed.length}`);
  console.log(`Keep: ${stats.recommendations.keep.length}`);
  console.log('=============================\n');

  return reportPath;
}

// Main
async function main() {
  try {
    await scanEmails();
    generateReport();
    console.log('✅ Scan complete (read-only mode)');
  } catch (err) {
    console.error('❌ Scan failed:', err.message);
    process.exit(1);
  }
}

main();
