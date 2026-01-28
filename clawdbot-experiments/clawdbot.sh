#!/bin/bash
# Wrapper script to run clawdbot commands in Docker
# Usage: ./clawdbot.sh <command> [args...]
# Examples:
#   ./clawdbot.sh onboard
#   ./clawdbot.sh gateway
#   ./clawdbot.sh --help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for .env file
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copy .env.example to .env and add your API key."
fi

# Build image if it doesn't exist
if ! docker images | grep -q clawdbot-experiments-clawdbot; then
    echo "Building clawdbot Docker image..."
    docker compose build
fi

# Run clawdbot with provided arguments
docker compose run --rm clawdbot clawdbot "$@"
