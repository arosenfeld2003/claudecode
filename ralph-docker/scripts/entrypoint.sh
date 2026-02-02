#!/bin/bash
# Ralph Docker Entrypoint
# Handles auth detection, command routing, and environment setup

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${CYAN}[ralph]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[ralph]${NC} $1"
}

log_error() {
    echo -e "${RED}[ralph]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[ralph]${NC} $1"
}

# Detect authentication mode
detect_auth() {
    local base_url="${ANTHROPIC_BASE_URL:-}"
    local api_key="${ANTHROPIC_API_KEY:-}"

    # Check if using LiteLLM proxy (Ollama mode) - check both URL patterns and API key
    if [[ "$base_url" == *"litellm"* ]] || [[ "$base_url" == *":4000"* ]]; then
        log_info "Auth mode: LiteLLM proxy -> Ollama (local)"
        return 0
    elif [ -n "$api_key" ] && [ -n "$base_url" ]; then
        log_info "Auth mode: API Key with custom base URL"
        return 0
    elif [ -f "$HOME/.claude/.credentials.json" ]; then
        log_info "Auth mode: OAuth credentials file (Max subscription)"
        return 0
    elif [ -f "$HOME/.claude/credentials.json" ]; then
        log_info "Auth mode: OAuth (Max subscription)"
        return 0
    elif [ -n "$api_key" ]; then
        log_info "Auth mode: API Key"
        return 0
    else
        log_error "No authentication found!"
        log_error "For OAuth on macOS: Use ./scripts/run-with-keychain.sh"
        log_error "For Ollama: Use --profile ollama with docker compose"
        return 1
    fi
}

# Wait for LiteLLM proxy to be ready
wait_for_litellm() {
    local base_url="${ANTHROPIC_BASE_URL:-}"
    local api_key="${ANTHROPIC_API_KEY:-}"

    # Only wait if using LiteLLM
    if [[ "$base_url" != *"litellm"* ]] && [[ "$base_url" != *":4000"* ]]; then
        return 0
    fi

    log_info "Waiting for LiteLLM proxy..."

    local max_attempts=30
    local attempt=1
    local auth_header=""

    # Add auth header if API key is set
    if [ -n "$api_key" ]; then
        auth_header="-H \"Authorization: Bearer $api_key\""
    fi

    while [ $attempt -le $max_attempts ]; do
        # Try health endpoint with auth
        if curl -sf -H "Authorization: Bearer $api_key" "${base_url}/health" &> /dev/null; then
            echo ""
            log_success "LiteLLM proxy is ready"
            return 0
        fi

        echo -ne "\r${CYAN}[ralph]${NC} Waiting for LiteLLM... attempt $attempt/$max_attempts"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo ""
    log_error "LiteLLM proxy did not become ready"
    log_error "Check if Ollama is running on the host: ollama serve"
    return 1
}

# Verify workspace is mounted
verify_workspace() {
    if [ ! -d "/home/ralph/workspace" ] || [ -z "$(ls -A /home/ralph/workspace 2>/dev/null)" ]; then
        log_warn "Workspace appears empty"
        log_warn "Mount your project: -v /path/to/project:/home/ralph/workspace"
    fi
}

# Display configuration
show_config() {
    local base_url="${ANTHROPIC_BASE_URL:-}"
    local backend="Claude API (cloud)"

    if [[ "$base_url" == *"litellm"* ]] || [[ "$base_url" == *":4000"* ]]; then
        backend="LiteLLM -> Ollama (local)"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Ralph Loop - Containerized"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Mode:       ${RALPH_MODE:-build}"
    echo "  Model:      ${RALPH_MODEL:-opus}"
    echo "  Format:     ${RALPH_OUTPUT_FORMAT:-pretty}"
    echo "  Max Iter:   ${RALPH_MAX_ITERATIONS:-0} (0=unlimited)"
    echo "  Push:       ${RALPH_PUSH_AFTER_COMMIT:-true}"
    echo "  Backend:    $backend"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Main command routing
main() {
    local cmd="${1:-loop}"
    shift || true

    case "$cmd" in
        loop)
            detect_auth || exit 1
            wait_for_litellm || exit 1
            verify_workspace
            show_config
            exec /home/ralph/scripts/loop.sh "$@"
            ;;
        shell)
            log_info "Starting interactive shell..."
            exec /bin/bash
            ;;
        version)
            claude --version
            ;;
        test)
            detect_auth || exit 1
            wait_for_litellm || exit 1
            log_success "All checks passed!"
            claude --version
            ;;
        help|--help|-h)
            cat << 'EOF'
Ralph Docker - Containerized Ralph Loop

COMMANDS:
  loop      Run the Ralph loop (default)
  shell     Start an interactive bash shell
  version   Show Claude CLI version
  test      Run connectivity tests
  help      Show this help message

ENVIRONMENT VARIABLES:
  RALPH_MODE              build|plan (default: build)
  RALPH_MAX_ITERATIONS    Max iterations, 0=unlimited (default: 0)
  RALPH_MODEL             Model name (default: opus, or ollama/model for local)
  RALPH_OUTPUT_FORMAT     pretty|json (default: pretty)
  RALPH_PUSH_AFTER_COMMIT Push to git after commits (default: true)

VOLUMES:
  /home/ralph/workspace   Your project directory
  /home/ralph/.claude     Claude credentials (read-only)

EXAMPLES:
  # OAuth mode (Max subscription)
  docker compose up ralph

  # Ollama mode (local models via LiteLLM proxy)
  docker compose --profile ollama up ralph-ollama

  # Plan mode with 5 iterations
  RALPH_MODE=plan RALPH_MAX_ITERATIONS=5 docker compose up ralph

  # Use a different Ollama model
  RALPH_MODEL=ollama/qwen2.5-coder:7b docker compose --profile ollama up ralph-ollama

  # Interactive shell for debugging
  docker compose run --rm ralph shell
EOF
            ;;
        *)
            log_error "Unknown command: $cmd"
            log_info "Run 'help' for usage information"
            exit 1
            ;;
    esac
}

main "$@"
