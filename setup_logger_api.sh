#!/bin/bash
# setup_logger_api.sh
# Открывает порт 7998, настраивает автозапуск и запускает сервер

set -e

PORT=7998
SERVICE_NAME=logger_api
USER=$(whoami)
WORKDIR=$(cd "$(dirname "$0")" && pwd)

# Получить внешний IP
EXT_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')

# 1. Открыть порт через UFW
sudo ufw allow ${PORT}/tcp
sudo ufw reload

# 2. Создать systemd unit-файл
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
echo "[Unit]
Description=Logger API FastAPI Service
After=network.target

[Service]
User=${USER}
WorkingDirectory=${WORKDIR}
ExecStart=$(which uvicorn) main:app --host ${EXT_IP} --port ${PORT}
Restart=always

[Install]
WantedBy=multi-user.target
" | sudo tee $SERVICE_FILE > /dev/null

# 3. Включить автозапуск и запустить сервис
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

API_URL="http://${EXT_IP}:${PORT}/"

echo "ip: ${EXT_IP}"
echo "Logger API теперь доступен на порту ${PORT} и будет запускаться автоматически при старте системы."
echo "Откройте в браузере: $API_URL"