# Clawdbot Docker container
# Isolates the agent from the host system

FROM node:22-slim

# Install clawdbot globally
RUN npm install -g clawdbot

# Create non-root user for security
RUN useradd -m -s /bin/bash clawdbot
USER clawdbot
WORKDIR /home/clawdbot

# Config directory will be mounted as volume
RUN mkdir -p /home/clawdbot/.clawdbot

# Default command - can be overridden
CMD ["clawdbot", "--help"]
