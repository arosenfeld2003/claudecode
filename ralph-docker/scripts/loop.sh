#!/bin/bash
# Ralph Loop - Main loop script with output formatting
# Runs inside the Docker container

set -euo pipefail

# Configuration from environment
MODE="${RALPH_MODE:-build}"
MAX_ITERATIONS="${RALPH_MAX_ITERATIONS:-0}"
MODEL="${RALPH_MODEL:-opus}"
OUTPUT_FORMAT="${RALPH_OUTPUT_FORMAT:-pretty}"
PUSH_AFTER_COMMIT="${RALPH_PUSH_AFTER_COMMIT:-true}"

# Determine prompt file
case "$MODE" in
    plan)
        PROMPT_FILE="/home/ralph/prompts/PROMPT_plan.md"
        ;;
    build|*)
        PROMPT_FILE="/home/ralph/prompts/PROMPT_build.md"
        ;;
esac

# Check for project-specific prompts
if [ -f "PROMPT_${MODE}.md" ]; then
    PROMPT_FILE="PROMPT_${MODE}.md"
    echo "[ralph] Using project prompt: $PROMPT_FILE"
fi

# Verify prompt exists
if [ ! -f "$PROMPT_FILE" ]; then
    echo "[ralph] Error: Prompt file not found: $PROMPT_FILE"
    exit 1
fi

# Build model argument
if [ "${ANTHROPIC_AUTH_TOKEN:-}" = "ollama" ]; then
    MODEL_ARG="--model $MODEL"
else
    MODEL_ARG="--model $MODEL"
fi

# Iteration counter
ITERATION=0

# Get current branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

echo "[ralph] Starting loop..."
echo "[ralph] Prompt: $PROMPT_FILE"
echo "[ralph] Branch: $CURRENT_BRANCH"
echo ""

# Output formatting command
format_output() {
    if [ "$OUTPUT_FORMAT" = "pretty" ]; then
        /home/ralph/scripts/format-output.sh
    else
        cat
    fi
}

# Main loop
while true; do
    # Check iteration limit
    if [ "$MAX_ITERATIONS" -gt 0 ] && [ "$ITERATION" -ge "$MAX_ITERATIONS" ]; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  Reached max iterations: $MAX_ITERATIONS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        break
    fi

    ITERATION=$((ITERATION + 1))
    echo ""
    echo "┌─────────────────────────────────────────────┐"
    echo "│  ITERATION $ITERATION                                  │"
    echo "└─────────────────────────────────────────────┘"
    echo ""

    # Run Claude with the prompt
    # -p: Headless mode (non-interactive)
    # --dangerously-skip-permissions: Auto-approve tool calls
    # --output-format=stream-json: Structured output for filtering
    cat "$PROMPT_FILE" | claude -p \
        --dangerously-skip-permissions \
        --output-format=stream-json \
        $MODEL_ARG \
        --verbose 2>&1 | format_output

    CLAUDE_EXIT=$?

    if [ $CLAUDE_EXIT -ne 0 ]; then
        echo "[ralph] Claude exited with code $CLAUDE_EXIT"
        # Continue loop anyway - Ralph should be resilient
    fi

    # Push changes if configured
    if [ "$PUSH_AFTER_COMMIT" = "true" ]; then
        CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
        if [ -n "$CURRENT_BRANCH" ]; then
            echo "[ralph] Pushing to origin/$CURRENT_BRANCH..."
            git push origin "$CURRENT_BRANCH" 2>/dev/null || \
                git push -u origin "$CURRENT_BRANCH" 2>/dev/null || \
                echo "[ralph] Push failed (no remote or no changes)"
        fi
    fi

    echo ""
    echo "════════════════════════════════════════════════"
    echo "  ITERATION $ITERATION COMPLETE"
    echo "════════════════════════════════════════════════"
    echo ""

    # Small delay between iterations
    sleep 1
done

echo ""
echo "[ralph] Loop finished after $ITERATION iterations"
