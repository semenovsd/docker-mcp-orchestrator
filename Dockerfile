FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Configure Poetry: Don't create virtual environment, install to system
RUN poetry config virtualenvs.create false

# Copy Poetry configuration files
COPY pyproject.toml ./

# Install dependencies (poetry.lock will be generated if not present)
# Use --no-root to skip installing the project itself (we'll copy files later)
RUN poetry install --only=main --no-root --no-interaction --no-ansi || \
    (poetry lock && poetry install --only=main --no-root --no-interaction --no-ansi)

# Copy project files
COPY src/ ./src/
COPY config/ ./config/

# Set Python path
ENV PYTHONPATH=/app/src:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-m", "orchestrator"]
