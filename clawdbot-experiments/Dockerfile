# Clawdbot Docker container
# Isolates the agent from the host system

FROM node:22-slim

# Install git for cloning repos if needed
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install clawdbot globally with verbose output for debugging
RUN npm install -g clawdbot --loglevel verbose || \
    (echo "npm install failed, trying with legacy peer deps..." && \
     npm install -g clawdbot --legacy-peer-deps)

# Create non-root user for security
RUN useradd -m -s /bin/bash clawdbot
USER clawdbot
WORKDIR /home/clawdbot

# Config directory will be mounted as volume
RUN mkdir -p /home/clawdbot/.clawdbot

# Default command - can be overridden
CMD ["clawdbot", "--help"]
