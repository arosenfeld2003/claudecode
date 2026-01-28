#!/bin/bash
# Setup script for Ollama + open source models for Ralph workflow
# Requires: macOS with Apple Silicon, Homebrew (optional)
#
# Usage: ./scripts/setup-ollama.sh [--minimal|--full]
#   --minimal: Only Qwen 7B (recommended starting point, fast)
#   --full:    All recommended models including Qwen 32B

set -euo pipefail

MINIMAL=false
FULL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --minimal) MINIMAL=true; shift ;;
        --full) FULL=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Default to minimal if no option specified
if [ "$MINIMAL" = false ] && [ "$FULL" = false ]; then
    MINIMAL=true
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Ollama Setup for Ralph Workflow"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo ""
    echo "Ollama not found. Installing via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install ollama
    else
        echo "Homebrew not found. Please install Ollama manually:"
        echo "  https://ollama.ai/download"
        exit 1
    fi
fi

# Check Ollama version (need v0.14.0+ for Anthropic API compatibility)
OLLAMA_VERSION=$(ollama --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "0.0.0")
REQUIRED_VERSION="0.14.0"

version_compare() {
    printf '%s\n' "$1" "$2" | sort -V | head -n1
}

if [ "$(version_compare "$OLLAMA_VERSION" "$REQUIRED_VERSION")" != "$REQUIRED_VERSION" ]; then
    echo ""
    echo "Warning: Ollama version $OLLAMA_VERSION found."
    echo "Version $REQUIRED_VERSION+ recommended for Anthropic API compatibility."
    echo "Run 'brew upgrade ollama' to update."
    echo ""
fi

echo ""
echo "Ollama version: $OLLAMA_VERSION"

# Check if Ollama server is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo ""
    echo "Starting Ollama server..."
    ollama serve &> /dev/null &
    sleep 3
fi

echo ""
echo "Pulling models..."

# Tier 1: Best for 48GB M4 (truly local models only)
MODELS_MINIMAL=(
    "qwen2.5-coder:7b"      # ~4GB, fast iterations
)

MODELS_ADDITIONAL=(
    "qwen2.5-coder:32b"     # ~20GB, max coding power
    "deepseek-coder-v2"     # ~15GB, multi-language support
)

# Pull minimal models
for model in "${MODELS_MINIMAL[@]}"; do
    echo ""
    echo "Pulling $model..."
    ollama pull "$model" || {
        echo "Warning: Failed to pull $model"
    }
done

# Pull additional models if --full specified
if [ "$FULL" = true ]; then
    for model in "${MODELS_ADDITIONAL[@]}"; do
        echo ""
        echo "Pulling $model..."
        ollama pull "$model" || echo "Warning: Failed to pull $model"
    done
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Installed models:"
ollama list
echo ""
echo "To use with Ralph loop:"
echo "  ./templates/loop.sh --local qwen2.5-coder:7b"
echo "  ./templates/loop.sh --local qwen2.5-coder:32b"
echo ""
echo "To use with Claude Code directly:"
echo "  export ANTHROPIC_AUTH_TOKEN=ollama"
echo "  export ANTHROPIC_BASE_URL=http://localhost:11434"
echo "  claude --model qwen2.5-coder:32b"
echo ""
echo "See docs/open-source-models.md for full documentation."
