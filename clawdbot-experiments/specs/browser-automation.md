# Feature: Browser Automation

## Overview

Use Clawdbot's browser automation capabilities to fill forms, extract data, and automate web workflows via chat commands.

## Jobs To Be Done

1. User can instruct bot to navigate to a URL
2. User can have bot fill out web forms with provided data
3. User can have bot extract specific data from web pages
4. User can have bot take screenshots of pages
5. User can have bot perform multi-step web workflows

## Acceptance Criteria

- [ ] Bot opens browser and navigates to specified URL
- [ ] Bot correctly identifies and fills form fields
- [ ] Bot extracts requested data and returns it in chat
- [ ] Screenshots are captured and accessible
- [ ] Multi-step workflows execute without manual intervention

## Constraints

- No credential storage in plaintext
- User must confirm before submitting sensitive forms
- Rate limit requests to avoid triggering anti-bot measures
- Respect robots.txt and site ToS

## Out of Scope

- CAPTCHA solving
- Session persistence across bot restarts
- Parallel browser instances

## Experiment Ideas

1. **Price checker**: Monitor a product page, alert on price drops
2. **Form pre-filler**: Populate job applications with saved profile data
3. **Data scraper**: Extract structured data from tables/lists
4. **Screenshot reporter**: Daily screenshots of dashboards for review

## Safety Considerations

- Always confirm before form submission
- Never automate login to financial/sensitive sites without explicit approval
- Log all browser actions for audit trail

## References

- Browser automation docs: Check Clawdbot documentation
- Consider Playwright/Puppeteer patterns for complex workflows
