#!/usr/bin/env bash
# نصب نود MLP روی یک VPS لینوکسی (systemd)
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "با root اجرا کن: sudo bash node/install-vps.sh"; exit 1; }

APP_DIR="${MLP_DIR:-/opt/mlp-node}"
PORT_DEFAULT="${MLP_PORT:-8080}"
PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "python3 نصب نیست (apt install python3 python3-venv)"; exit 1; }

read -rp "دامنه‌ی پنل (مثل https://panel.up.railway.app): " PANEL_URL
read -rp "توکن این نود (از پنل، بخش لوکیشن‌ها): " NODE_TOKEN
read -rp "نام لوکیشن [Node]: " NODE_NAME; NODE_NAME="${NODE_NAME:-Node}"
read -rp "فلگ [🌍]: " NODE_FLAG; NODE_FLAG="${NODE_FLAG:-🌍}"
read -rp "پورت شنود [$PORT_DEFAULT]: " NODE_PORT; NODE_PORT="${NODE_PORT:-$PORT_DEFAULT}"

mkdir -p "$APP_DIR"
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cp -r "$SRC_DIR/node/app" "$APP_DIR/"
cp "$SRC_DIR/node/requirements.txt" "$APP_DIR/"

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

cat > /etc/systemd/system/mlp-node.service <<SERVICE
[Unit]
Description=MLP Node
After=network.target

[Service]
WorkingDirectory=$APP_DIR
Environment=MLP_PANEL_URL=$PANEL_URL
Environment=MLP_NODE_TOKEN=$NODE_TOKEN
Environment=MLP_NODE_NAME=$NODE_NAME
Environment=MLP_NODE_FLAG=$NODE_FLAG
Environment=PORT=$NODE_PORT
Environment=MLP_NODE_DATA_DIR=$APP_DIR/data
ExecStart=$APP_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $NODE_PORT --proxy-headers --forwarded-allow-ips '*'
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now mlp-node
sleep 2
systemctl --no-pager --full status mlp-node | head -n 12
echo
echo "✅ نود روی پورت $NODE_PORT اجرا شد. تست:  curl -s http://127.0.0.1:$NODE_PORT/healthz"
echo "یادت نباشد در پنل، دامنه‌ی این سرور را در همان لوکیشن ثبت کنی."
