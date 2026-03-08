# ── Sahayak Backend ──────────────────────────────────────
# Image-based deployment for AWS App Runner.
# Pure Python — zero native system dependencies.
# ─────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── 1. Working directory ──
WORKDIR /app

# ── 2. Install Python dependencies (cached layer) ──
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── 3. Copy application code ──
COPY . .

# ── 4. Expose port (App Runner uses 8080 by default) ──
EXPOSE 8080

# ── 5. Health check ──
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# ── 6. Run ──
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
