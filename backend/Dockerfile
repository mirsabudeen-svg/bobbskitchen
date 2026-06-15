FROM python:3.11-slim

WORKDIR /app

# Install deps first (layer cached separately from app code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8420

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8420/health')"

# --workers 1 is REQUIRED: in-process WebSocket registry is not multi-worker safe.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8420", "--workers", "1"]
