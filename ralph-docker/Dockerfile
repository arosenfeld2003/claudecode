FROM node:22-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    jq \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user for security
RUN useradd -m -s /bin/bash ralph
USER ralph
WORKDIR /home/ralph

# Create directory structure
RUN mkdir -p .claude workspace prompts

# Copy scripts and libraries
COPY --chown=ralph:ralph scripts/ scripts/
COPY --chown=ralph:ralph lib/ lib/
COPY --chown=ralph:ralph prompts/ prompts/

# Make scripts executable
RUN chmod +x scripts/*.sh

# Environment configuration
ENV RALPH_MODE=build \
    RALPH_MAX_ITERATIONS=0 \
    RALPH_MODEL=opus \
    RALPH_OUTPUT_FORMAT=pretty \
    RALPH_PUSH_AFTER_COMMIT=true

# Working directory for mounted projects
WORKDIR /home/ralph/workspace

ENTRYPOINT ["/home/ralph/scripts/entrypoint.sh"]
CMD ["loop"]
