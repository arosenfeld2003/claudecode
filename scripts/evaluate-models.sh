#!/bin/bash
# Model comparison runner for Ralph workflow evaluation
# Compares local models against Claude Code baseline
#
# Usage: ./scripts/evaluate-models.sh [task_type]
#   task_type: plan | build (default: plan)
#
# Output: results/<model>-<timestamp>.log

set -euo pipefail

TASK_TYPE="${1:-plan}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_DIR="results"

# Models to evaluate
# Cloud baseline + local models
MODELS=(
    "cloud:opus"           # Claude Code baseline (Opus)
    "local:minimax-m2.1"   # Best for agentic tasks
    "local:qwen2.5-coder:7b"  # Fast iterations
)

# Create results directory
mkdir -p "$RESULTS_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Model Evaluation Runner"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Task type: $TASK_TYPE"
echo "Results:   $RESULTS_DIR/"
echo "Models:    ${#MODELS[@]}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if loop.sh exists
LOOP_SCRIPT="./templates/loop.sh"
if [ ! -f "$LOOP_SCRIPT" ]; then
    echo "Error: $LOOP_SCRIPT not found"
    echo "Run this script from the repository root."
    exit 1
fi

# Run evaluation for each model
for model_spec in "${MODELS[@]}"; do
    # Parse model type and name
    MODEL_TYPE="${model_spec%%:*}"
    MODEL_NAME="${model_spec#*:}"

    # Create safe filename
    SAFE_NAME=$(echo "$MODEL_NAME" | tr ':/' '-')
    LOG_FILE="$RESULTS_DIR/${SAFE_NAME}-${TIMESTAMP}.log"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: $MODEL_NAME ($MODEL_TYPE)"
    echo "Output:  $LOG_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Record start time
    START_TIME=$(date +%s)

    # Run the appropriate command
    if [ "$MODEL_TYPE" = "cloud" ]; then
        # Cloud model (Claude Code default)
        $LOOP_SCRIPT "$TASK_TYPE" 1 2>&1 | tee "$LOG_FILE"
    else
        # Local model via Ollama
        $LOOP_SCRIPT "$TASK_TYPE" 1 --local "$MODEL_NAME" 2>&1 | tee "$LOG_FILE"
    fi

    # Record end time and calculate duration
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Append summary to log
    echo "" >> "$LOG_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$LOG_FILE"
    echo "Model: $MODEL_NAME" >> "$LOG_FILE"
    echo "Type: $MODEL_TYPE" >> "$LOG_FILE"
    echo "Task: $TASK_TYPE" >> "$LOG_FILE"
    echo "Duration: ${DURATION}s" >> "$LOG_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$LOG_FILE"

    echo ""
    echo "Completed in ${DURATION}s"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Evaluation Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Results saved to: $RESULTS_DIR/"
echo ""
echo "To compare results:"
echo "  ls -la $RESULTS_DIR/"
echo ""
echo "Evaluation criteria to check:"
echo "  - Task completion (did it finish?)"
echo "  - Plan/code quality (manual review)"
echo "  - Execution time (logged above)"
echo "  - Error handling (check logs)"
