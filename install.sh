#!/bin/bash

# Скрипт установки AmneziaWG Exporter как systemd сервиса

set -e

echo "Установка AmneziaWG Exporter..."

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo)"
    exit 1
fi

# Установка зависимостей
echo "Установка зависимостей Python..."
pip3 install prometheus-client

# Создание директории
echo "Создание директории /opt/awg-exporter..."
mkdir -p /opt/awg-exporter

# Копирование файлов
echo "Копирование файлов..."
cp exporter.py /opt/awg-exporter/
cp peer_names.json /opt/awg-exporter/

# Установка прав
chmod +x /opt/awg-exporter/exporter.py

# Копирование systemd unit файла
echo "Установка systemd сервиса..."
cp awg-exporter.service /etc/systemd/system/

# Перезагрузка systemd
systemctl daemon-reload

# Включение и запуск сервиса
echo "Запуск сервиса..."
systemctl enable awg-exporter.service
systemctl start awg-exporter.service

# Проверка статуса
echo ""
echo "Статус сервиса:"
systemctl status awg-exporter.service --no-pager

echo ""
echo "Установка завершена!"
echo "Метрики доступны на http://localhost:9586/metrics"
echo ""
echo "Полезные команды:"
echo "  systemctl status awg-exporter   - проверить статус"
echo "  systemctl restart awg-exporter  - перезапустить"
echo "  systemctl stop awg-exporter     - остановить"
echo "  journalctl -u awg-exporter -f   - смотреть логи"
echo ""
echo "Не забудьте отредактировать /opt/awg-exporter/peer_names.json"
echo "для добавления имен ваших пиров!"
