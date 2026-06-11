FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8420

# --workers 1 is REQUIRED: in-process WebSocket registry is not multi-worker safe.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8420", "--workers", "1"]
