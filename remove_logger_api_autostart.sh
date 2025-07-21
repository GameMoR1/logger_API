#!/bin/bash
# remove_logger_api_autostart.sh
# Отключает автозапуск Logger API и останавливает сервис

set -e

SERVICE_NAME=logger_api

sudo systemctl disable ${SERVICE_NAME}
sudo systemctl stop ${SERVICE_NAME}
sudo rm -f /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload

echo "Автозапуск Logger API отключён и сервис остановлен."
