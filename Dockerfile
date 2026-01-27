FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/
COPY .env.example ./.env

# Install Python dependencies from pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Create data and backups directories with proper permissions
RUN mkdir -p /app/data /app/backups

# Create non-root user and set ownership
RUN useradd -m -u 1000 bot && \
    chown -R bot:bot /app
USER bot

# Run bot
CMD ["python", "-m", "src.bot"]
