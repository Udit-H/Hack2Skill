# ── Sahayak Backend ──────────────────────────────────────
# Image-based deployment for AWS App Runner.
# Uses python:3.11-slim + WeasyPrint system dependencies.
# ─────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── 1. System deps for WeasyPrint (pango/cairo/gdk-pixbuf) ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libffi-dev \
    libglib2.0-0 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# ── 2. Working directory ──
WORKDIR /app

# ── 3. Install Python dependencies (cached layer) ──
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── 4. Copy application code ──
COPY . .

# ── 5. Expose port (App Runner uses 8080 by default) ──
EXPOSE 8080

# ── 6. Health check ──
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# ── 7. Run ──
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
