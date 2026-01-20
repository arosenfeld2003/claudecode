# Project Operations Guide

This file is loaded every iteration. Keep it brief (~60 lines max).
Status updates and progress notes belong in `IMPLEMENTATION_PLAN.md`, not here.

## Build & Run

<!-- How to build the project -->
```bash
# Install dependencies
npm install

# Build
npm run build

# Run development server
npm run dev
```

## Validation

Run these after implementing to get immediate feedback:

- **Tests**: `npm test`
- **Typecheck**: `npm run typecheck`
- **Lint**: `npm run lint`
- **Build**: `npm run build`

<!-- Add all validation commands that provide backpressure -->

## Operational Notes

<!-- Learnings about how to run the project - discovered through iteration -->

- Example: Use `npm run dev -- --port 3001` if port 3000 is in use
- Example: Set `DEBUG=app:*` for verbose logging

## Codebase Patterns

<!-- Patterns Ralph should follow - add when you see wrong patterns being generated -->

- API routes follow REST conventions in `src/api/`
- Use the ErrorHandler utility for consistent error responses
- Database operations go through the Repository pattern
- Components use [pattern] for state management

## Directory Structure

```
src/
├── api/        # API endpoints
├── lib/        # Shared utilities and components
├── models/     # Data models
└── __tests__/  # Test files
```

<!--
CUSTOMIZATION NOTES:
- Replace npm commands with your actual build/test commands
- Add validation commands that provide backpressure
- Document patterns as you observe Ralph generating wrong ones
- Keep this file operational only - no status updates
- Target ~60 lines to preserve context budget
-->
