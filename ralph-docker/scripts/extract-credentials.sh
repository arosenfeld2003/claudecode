#!/bin/bash
# Extract Claude credentials from macOS Keychain for Docker usage
# This script retrieves OAuth tokens and writes them to a file that Docker can mount

set -euo pipefail

CREDS_FILE="${1:-$HOME/.claude/.docker-credentials.json}"

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "This script only works on macOS (uses Keychain)"
    exit 1
fi

# Extract credentials from Keychain
CREDS=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null || echo "")

if [[ -z "$CREDS" ]]; then
    echo "Error: Could not find Claude credentials in Keychain"
    echo "Make sure you're logged in with: claude auth login"
    exit 1
fi

# Write to file
echo "$CREDS" > "$CREDS_FILE"
chmod 600 "$CREDS_FILE"

echo "Credentials extracted to: $CREDS_FILE"
