# MLP Panel — پنل مرکزی (نقش: panel)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MLP_DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY setup_files.json ./setup_files.json
RUN mkdir -p /data

# پورت پنل: Railway متغیر PORT را خودش می‌دهد؛ اگر نبود 8080
EXPOSE 8080
ENV PORT=8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips '*' --loop uvloop --log-level info || uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips '*' --log-level info"]
