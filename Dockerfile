"""Docker configuration for development."""

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY .env.example ./.env

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev,db]"

# Create non-root user
RUN useradd -m -u 1000 bot && chown -R bot:bot /app
USER bot

# Run bot
CMD ["python", "-m", "src.bot"]
