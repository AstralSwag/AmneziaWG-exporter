#!/bin/bash

# Скрипт для генерации шаблона peer_names.json из текущих пиров

echo "Получение списка пиров из контейнера amnezia-awg..."
echo ""

# Получаем вывод wg show
output=$(docker exec amnezia-awg wg show all dump 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "Ошибка: не удалось выполнить команду в контейнере"
    echo "Проверьте что контейнер запущен: docker ps | grep amnezia"
    exit 1
fi

# Парсим публичные ключи пиров (пропускаем первую строку с интерфейсом)
echo "{"
first=true

echo "$output" | tail -n +2 | while IFS=$'\t' read -r interface pubkey rest; do
    if [ -n "$pubkey" ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo ","
        fi
        # Берем первые 8 символов ключа как имя по умолчанию
        short_key="${pubkey:0:8}"
        echo -n "  \"$pubkey\": \"Client_${short_key}\""
    fi
done

echo ""
echo "}"
echo ""
echo "Скопируйте вывод выше в файл /opt/awg-exporter/peer_names.json"
echo "и замените имена клиентов на понятные вам."
echo ""
echo "После изменения перезапустите сервис:"
echo "  sudo systemctl restart awg-exporter"
