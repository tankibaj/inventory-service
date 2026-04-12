FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml .

# Install production dependencies
RUN uv pip install --system --no-cache -e .

# Copy source
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
