# ---------------------------------------------------------------------------
# Miss Universe Nail Art Studio — container image
# All Python dependencies ship pre-built wheels for CPython 3.13, so no
# compiler or system libraries are required.
# ---------------------------------------------------------------------------
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching).
COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application.
COPY . .

# Create writable data dirs and a non-root user, then hand ownership over.
# Pre-creating (and chowning) the volume mount points means the named volumes
# inherit the correct ownership on first use, so the app can write to them.
RUN mkdir -p /app/storage/uploads /app/data \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').getcode()==200 else 1)"

# Run from the backend/ folder so `app.main:app` imports cleanly. The app finds
# the frontend/ assets and the data folders via absolute paths (see config.py).
WORKDIR /app/backend

# The app creates tables and the first admin automatically on startup.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
