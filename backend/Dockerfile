FROM python:3.12-slim

WORKDIR /app

# Install build dependencies for argon2-cffi (requires C compiler)
# and clean up in the same layer to minimize image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code and scripts
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY run.py ./

CMD ["uv", "run", "python", "run.py"]
