#!/bin/sh
# حالت Xray: nginx روی پورت عمومی، Xray برای پروکسی، FastAPI برای سایت پوششی
set -e

NGINX_PORT="${PORT:-8080}"
INTERNAL_PORT="${MLP_INTERNAL_PORT:-8090}"
XRAY_WS_PORT="${MLP_XRAY_WS_PORT:-18080}"
XRAY_XHTTP_PORT="${MLP_XRAY_XHTTP_PORT:-18081}"
export MLP_INTERNAL_PORT="$INTERNAL_PORT"

mkdir -p /var/log/nginx /var/lib/nginx /tmp/nginx

envsubst '${NGINX_PORT} ${WS_PATH} ${XHTTP_PATH} ${XRAY_WS_PORT} ${XRAY_XHTTP_PORT} ${INTERNAL_PORT}' \
  < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

echo ">> nginx:${NGINX_PORT}  xray ws:${XRAY_WS_PORT} xhttp:${XRAY_XHTTP_PORT}  app:${INTERNAL_PORT}"

# کنترل‌پلین + سایت پوششی
uvicorn app.main:app --host 127.0.0.1 --port "$INTERNAL_PORT" --proxy-headers --forwarded-allow-ips '*' --log-level info &

sleep 1
exec nginx -g "daemon off;"
