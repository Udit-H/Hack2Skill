# ── Sahayak Backend ──────────────────────────────────────
# Image-based deployment for AWS App Runner.
# Minimal system deps: only libcairo2 for xhtml2pdf.
# ─────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── 1. Minimal system dep: cairo for pycairo (xhtml2pdf dependency) ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2-dev \
    pkg-config \
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
