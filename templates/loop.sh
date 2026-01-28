#!/bin/bash
# Ralph Loop Script - Enhanced version with mode selection, iteration limits, and local model support
#
# Usage: ./loop.sh [plan|plan-work] [max_iterations] [--local <model>]
#
# Examples:
#   ./loop.sh                           # Build mode, unlimited, Claude Code (cloud)
#   ./loop.sh 20                         # Build mode, max 20 iterations
#   ./loop.sh plan                       # Plan mode, unlimited iterations
#   ./loop.sh plan 5                     # Plan mode, max 5 iterations
#   ./loop.sh plan-work "user auth"      # Scoped planning for work branch
#   ./loop.sh --local qwen2.5-coder:32b  # Build mode with local Qwen 32B model
#   ./loop.sh plan --local qwen2.5-coder:7b  # Plan mode with local Qwen 7B model
#   ./loop.sh plan 5 --local qwen2.5-coder:32b   # Plan mode, 5 iterations, local model

set -euo pipefail

# Parse arguments
MODE="build"
PROMPT_FILE="PROMPT_build.md"
MAX_ITERATIONS=0
WORK_DESCRIPTION=""
LOCAL_MODEL=""
USE_LOCAL=false

# Process all arguments
POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            USE_LOCAL=true
            LOCAL_MODEL="${2:-}"
            if [ -z "$LOCAL_MODEL" ]; then
                echo "Error: --local requires a model name"
                echo "Example: ./loop.sh --local qwen2.5-coder:32b"
                exit 1
            fi
            shift 2
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Restore positional arguments
set -- "${POSITIONAL_ARGS[@]:-}"

# Parse mode and iterations from positional arguments
if [ "${1:-}" = "plan" ]; then
    MODE="plan"
    PROMPT_FILE="PROMPT_plan.md"
    MAX_ITERATIONS=${2:-0}
elif [ "${1:-}" = "plan-work" ]; then
    if [ -z "${2:-}" ]; then
        echo "Error: plan-work requires a work description"
        echo "Usage: ./loop.sh plan-work \"description of the work\""
        exit 1
    fi
    MODE="plan-work"
    WORK_DESCRIPTION="$2"
    PROMPT_FILE="PROMPT_plan_work.md"
    MAX_ITERATIONS=${3:-5}
elif [[ "${1:-}" =~ ^[0-9]+$ ]]; then
    MAX_ITERATIONS=$1
fi

ITERATION=0
CURRENT_BRANCH=$(git branch --show-current)

# Validate branch for plan-work mode
if [ "$MODE" = "plan-work" ]; then
    if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
        echo "Error: plan-work should be run on a work branch, not main/master"
        echo "Create a work branch first: git checkout -b ralph/your-work"
        exit 1
    fi
fi

# Configure model settings
if [ "$USE_LOCAL" = true ]; then
    # Set Ollama environment for Anthropic API compatibility
    export ANTHROPIC_AUTH_TOKEN=ollama
    export ANTHROPIC_BASE_URL=http://localhost:11434
    MODEL_ARG="--model $LOCAL_MODEL"
    MODEL_DISPLAY="$LOCAL_MODEL (local/Ollama)"

    # Verify Ollama is running
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo "Error: Ollama server not responding at localhost:11434"
        echo "Start it with: ollama serve"
        exit 1
    fi
else
    MODEL_ARG="--model opus"
    MODEL_DISPLAY="opus (Claude Code)"
fi

# Display configuration
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Mode:   $MODE"
echo "Model:  $MODEL_DISPLAY"
echo "Prompt: $PROMPT_FILE"
echo "Branch: $CURRENT_BRANCH"
[ "$MAX_ITERATIONS" -gt 0 ] && echo "Max:    $MAX_ITERATIONS iterations"
[ -n "$WORK_DESCRIPTION" ] && echo "Work:   $WORK_DESCRIPTION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verify prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    echo "Error: $PROMPT_FILE not found"
    echo "Make sure you have the prompt files in the current directory."
    exit 1
fi

# Export work description for plan-work mode (used by envsubst)
export WORK_SCOPE="$WORK_DESCRIPTION"

# Main loop
while true; do
    if [ "$MAX_ITERATIONS" -gt 0 ] && [ "$ITERATION" -ge "$MAX_ITERATIONS" ]; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Reached max iterations: $MAX_ITERATIONS"
        if [ "$MODE" = "plan-work" ]; then
            echo ""
            echo "Scoped plan created for: $WORK_DESCRIPTION"
            echo "To build, run: ./loop.sh 20"
        fi
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        break
    fi

    # Run Ralph iteration with selected prompt
    # -p: Headless mode (non-interactive, reads from stdin)
    # --dangerously-skip-permissions: Auto-approve all tool calls (YOLO mode)
    # --output-format=stream-json: Structured output for logging/monitoring
    # --model: Primary agent model (opus for cloud, local model for Ollama)
    # --verbose: Detailed execution logging
    #
    # Note: Can switch to --model sonnet for faster builds if plan is clear
    # Note: For local models, ANTHROPIC_BASE_URL points to Ollama

    if [ "$MODE" = "plan-work" ]; then
        # Substitute ${WORK_SCOPE} in prompt
        envsubst < "$PROMPT_FILE" | claude -p \
            --dangerously-skip-permissions \
            --output-format=stream-json \
            $MODEL_ARG \
            --verbose
    else
        cat "$PROMPT_FILE" | claude -p \
            --dangerously-skip-permissions \
            --output-format=stream-json \
            $MODEL_ARG \
            --verbose
    fi

    # Push changes after each iteration
    CURRENT_BRANCH=$(git branch --show-current)
    git push origin "$CURRENT_BRANCH" 2>/dev/null || {
        echo "Creating remote branch..."
        git push -u origin "$CURRENT_BRANCH"
    }

    ITERATION=$((ITERATION + 1))
    echo ""
    echo "======================== LOOP $ITERATION COMPLETE ========================"
    echo ""
done
