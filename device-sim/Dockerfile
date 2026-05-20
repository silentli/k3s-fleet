FROM python:3.11-slim

# Install uv from the official image for blazing-fast dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy modern dependency configuration
COPY pyproject.toml uv.lock ./

# Install dependencies deterministically from uv.lock
# Uses BuildKit cache mount to drastically speed up re-builds if dependencies change
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy your application code
COPY . .

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Run the application directly from the virtual environment
CMD ["python", "-u", "src/main.py"]
