# LiteLLM Proxy - Built from pip
# Avoids registry authentication issues

FROM python:3.11-slim

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install LiteLLM
RUN pip install --no-cache-dir 'litellm[proxy]'

WORKDIR /app

# Default port
EXPOSE 4000

# Run litellm proxy
ENTRYPOINT ["litellm"]
CMD ["--port", "4000"]
