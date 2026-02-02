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
    if [ "${ANTHROPIC_AUTH_TOKEN:-}" = "ollama" ]; then
        log_info "Auth mode: Ollama (local)"
        return 0
    elif [ -f "$HOME/.claude/credentials.json" ] || [ -f "$HOME/.claude/.credentials.json" ]; then
        log_info "Auth mode: OAuth (Max subscription)"
        return 0
    else
        log_error "No authentication found!"
        log_error "For OAuth: Mount ~/.claude to /home/ralph/.claude"
        log_error "For Ollama: Set ANTHROPIC_AUTH_TOKEN=ollama and ANTHROPIC_BASE_URL"
        return 1
    fi
}

# Verify Ollama connectivity (if using Ollama mode)
verify_ollama() {
    if [ "${ANTHROPIC_AUTH_TOKEN:-}" = "ollama" ]; then
        local ollama_url="${ANTHROPIC_BASE_URL:-http://host.docker.internal:11434}"
        log_info "Checking Ollama at $ollama_url..."

        if ! curl -sf "${ollama_url}/api/tags" &> /dev/null; then
            log_error "Cannot connect to Ollama at $ollama_url"
            log_error "Make sure Ollama is running on the host: ollama serve"
            return 1
        fi

        log_success "Ollama connection verified"
    fi
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
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Ralph Loop - Containerized"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Mode:       ${RALPH_MODE:-build}"
    echo "  Model:      ${RALPH_MODEL:-opus}"
    echo "  Format:     ${RALPH_OUTPUT_FORMAT:-pretty}"
    echo "  Max Iter:   ${RALPH_MAX_ITERATIONS:-0} (0=unlimited)"
    echo "  Push:       ${RALPH_PUSH_AFTER_COMMIT:-true}"
    if [ "${ANTHROPIC_AUTH_TOKEN:-}" = "ollama" ]; then
        echo "  Backend:    Ollama (local)"
    else
        echo "  Backend:    Claude API (cloud)"
    fi
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
            verify_ollama || exit 1
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
            verify_ollama || exit 1
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
  RALPH_MODEL             Model name (default: opus)
  RALPH_OUTPUT_FORMAT     pretty|json (default: pretty)
  RALPH_PUSH_AFTER_COMMIT Push to git after commits (default: true)

VOLUMES:
  /home/ralph/workspace   Your project directory
  /home/ralph/.claude     Claude credentials (read-only)

EXAMPLES:
  # OAuth mode (Max subscription)
  docker compose up ralph

  # Ollama mode (local models)
  docker compose --profile ollama up ralph-ollama

  # Plan mode with 5 iterations
  RALPH_MODE=plan RALPH_MAX_ITERATIONS=5 docker compose up ralph

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
