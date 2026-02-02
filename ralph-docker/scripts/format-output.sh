#!/bin/bash
# Format stream-json output to human-readable format
# Filters Claude's verbose JSON output into colored, readable text

# Colors
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# Maximum length for tool inputs/outputs before truncation
MAX_CONTENT_LENGTH=500

truncate_text() {
    local text="$1"
    local max_len="${2:-$MAX_CONTENT_LENGTH}"
    if [ ${#text} -gt $max_len ]; then
        echo "${text:0:$max_len}... (truncated)"
    else
        echo "$text"
    fi
}

# Process each line of JSON
while IFS= read -r line; do
    # Skip empty lines
    [ -z "$line" ] && continue

    # Try to parse as JSON
    if ! echo "$line" | jq -e . >/dev/null 2>&1; then
        # Not JSON, output as-is
        echo "$line"
        continue
    fi

    # Extract message type
    msg_type=$(echo "$line" | jq -r '.type // empty' 2>/dev/null)

    case "$msg_type" in
        assistant)
            # Assistant text output
            content=$(echo "$line" | jq -r '.message.content // empty' 2>/dev/null)
            if [ -n "$content" ] && [ "$content" != "null" ]; then
                # Handle array of content blocks
                if echo "$content" | jq -e 'type == "array"' >/dev/null 2>&1; then
                    echo "$content" | jq -r '.[] | select(.type == "text") | .text // empty' 2>/dev/null | while IFS= read -r text; do
                        [ -n "$text" ] && echo -e "${CYAN}$text${NC}"
                    done
                else
                    echo -e "${CYAN}$content${NC}"
                fi
            fi
            ;;

        content_block_start)
            # Start of a content block (tool use, etc.)
            block_type=$(echo "$line" | jq -r '.content_block.type // empty' 2>/dev/null)
            if [ "$block_type" = "tool_use" ]; then
                tool_name=$(echo "$line" | jq -r '.content_block.name // "unknown"' 2>/dev/null)
                echo -e "${YELLOW}[tool]${NC} ${BOLD}$tool_name${NC}"
            fi
            ;;

        content_block_delta)
            # Incremental content (streaming text)
            delta_type=$(echo "$line" | jq -r '.delta.type // empty' 2>/dev/null)
            if [ "$delta_type" = "text_delta" ]; then
                text=$(echo "$line" | jq -r '.delta.text // empty' 2>/dev/null)
                [ -n "$text" ] && echo -ne "${CYAN}$text${NC}"
            elif [ "$delta_type" = "input_json_delta" ]; then
                # Tool input streaming - collect but don't spam output
                :
            fi
            ;;

        tool_use)
            # Tool invocation
            tool_name=$(echo "$line" | jq -r '.name // "unknown"' 2>/dev/null)
            tool_input=$(echo "$line" | jq -r '.input // {} | tostring' 2>/dev/null)
            echo -e "${YELLOW}[tool]${NC} ${BOLD}$tool_name${NC}"
            truncated=$(truncate_text "$tool_input" 200)
            echo -e "${DIM}  input: $truncated${NC}"
            ;;

        tool_result)
            # Tool execution result
            tool_id=$(echo "$line" | jq -r '.tool_use_id // "?"' 2>/dev/null)
            is_error=$(echo "$line" | jq -r '.is_error // false' 2>/dev/null)
            content=$(echo "$line" | jq -r '.content // empty' 2>/dev/null)

            if [ "$is_error" = "true" ]; then
                echo -e "${RED}[error]${NC} Tool failed"
                [ -n "$content" ] && echo -e "${RED}  $(truncate_text "$content" 300)${NC}"
            else
                echo -e "${GREEN}[done]${NC} Tool completed"
            fi
            ;;

        error)
            # Error message
            error_msg=$(echo "$line" | jq -r '.error.message // .message // "Unknown error"' 2>/dev/null)
            echo -e "${RED}[ERROR]${NC} $error_msg"
            ;;

        message_start)
            # New message starting
            model=$(echo "$line" | jq -r '.message.model // empty' 2>/dev/null)
            [ -n "$model" ] && echo -e "${DIM}[model: $model]${NC}"
            ;;

        message_stop)
            # Message complete
            echo ""
            ;;

        system)
            # System message
            text=$(echo "$line" | jq -r '.message // empty' 2>/dev/null)
            [ -n "$text" ] && echo -e "${MAGENTA}[system]${NC} $text"
            ;;

        result)
            # Final result
            cost=$(echo "$line" | jq -r '.cost_usd // empty' 2>/dev/null)
            duration=$(echo "$line" | jq -r '.duration_ms // empty' 2>/dev/null)
            if [ -n "$cost" ] || [ -n "$duration" ]; then
                echo -e "${DIM}[stats] cost: \$$cost, duration: ${duration}ms${NC}"
            fi
            ;;

        *)
            # Unknown type - check for common patterns
            if echo "$line" | jq -e '.subagent' >/dev/null 2>&1; then
                subagent=$(echo "$line" | jq -r '.subagent // empty' 2>/dev/null)
                echo -e "${MAGENTA}[subagent]${NC} $subagent"
            fi
            ;;
    esac
done
