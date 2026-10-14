FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GROWTHPILOT_DB_PATH=/var/lib/growthpilot/growthpilot.db

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /var/lib/growthpilot \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /var/lib/growthpilot /app

COPY app ./app
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
