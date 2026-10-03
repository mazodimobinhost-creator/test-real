# MLP — دیپلوی از «ریشه‌ی ریپو» (وقتی Root Directory ست نشده باشد) → سرویس پنل
# برای هر نود، Root Directory را روی `node` بگذار (فایل node/Dockerfile استفاده می‌شود).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    MLP_DATA_DIR=/data

WORKDIR /app
COPY panel/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY panel/app ./app
COPY panel/setup_files.json ./setup_files.json
RUN mkdir -p /data

# پورت پنل: Railway متغیر PORT را می‌دهد؛ در نبودش 8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips '*' --loop uvloop --log-level info || uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips '*' --log-level info"]
