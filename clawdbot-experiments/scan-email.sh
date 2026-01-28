#!/bin/bash
# Run the email scanner in Docker (read-only mode)
#
# Usage:
#   ./scan-email.sh
#
# Requires:
#   - ICLOUD_APP_PASSWORD in .env file
#   - Or pass it directly: ICLOUD_APP_PASSWORD=xxxx ./scan-email.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for password
if [ -z "$ICLOUD_APP_PASSWORD" ] && ! grep -q ICLOUD_APP_PASSWORD .env 2>/dev/null; then
    echo "ERROR: ICLOUD_APP_PASSWORD not set"
    echo ""
    echo "Option 1: Add to .env file:"
    echo "  echo 'ICLOUD_APP_PASSWORD=your-app-password' >> .env"
    echo ""
    echo "Option 2: Pass directly:"
    echo "  ICLOUD_APP_PASSWORD=your-app-password ./scan-email.sh"
    echo ""
    echo "Generate an app-specific password at:"
    echo "  https://appleid.apple.com → Security → App-Specific Passwords"
    exit 1
fi

# Load .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "📧 Starting email scanner (read-only mode)..."
echo ""

# Run in Docker with mounted scripts and output directory
docker run --rm \
    -e ICLOUD_EMAIL="${ICLOUD_EMAIL:-arosenfeld2003@mac.com}" \
    -e ICLOUD_APP_PASSWORD="$ICLOUD_APP_PASSWORD" \
    -e OUTPUT_DIR="/reports" \
    -v "$SCRIPT_DIR/scripts:/scripts:ro" \
    -v "$SCRIPT_DIR/reports:/reports" \
    -w /scripts \
    node:22-slim \
    sh -c "npm install --silent && node email-scanner.js"

echo ""
echo "📄 Reports saved to: $SCRIPT_DIR/reports/"
ls -la "$SCRIPT_DIR/reports/"
