#!/bin/bash

echo "=== Диагностика AmneziaWG Exporter ==="
echo ""

echo "1. Проверка контейнера AmneziaWG:"
docker ps | grep -i amnezia || echo "❌ Контейнер не найден!"
echo ""

echo "2. Проверка команды wg внутри контейнера:"
docker exec amnezia-awg wg show all dump 2>&1 | head -5 || {
    echo "❌ Ошибка выполнения 'wg'. Пробуем 'awg'..."
    docker exec amnezia-awg awg show all dump 2>&1 | head -5 || echo "❌ Обе команды не работают!"
}
echo ""

echo "3. Проверка статуса сервиса экспортера:"
systemctl is-active awg-exporter 2>/dev/null || echo "❌ Сервис не запущен или не установлен"
echo ""

echo "4. Проверка метрик на порту 9586:"
curl -s http://localhost:9586/metrics | grep -E "awg_(sent|received|latest)" | head -5 || {
    echo "❌ Метрики awg_* не найдены!"
    echo ""
    echo "Проверяем что экспортер вообще работает:"
    curl -s http://localhost:9586/metrics | grep python_info || echo "❌ Экспортер не отвечает на порту 9586"
}
echo ""

echo "5. Последние логи экспортера:"
journalctl -u awg-exporter -n 20 --no-pager 2>/dev/null || {
    echo "❌ Не удалось получить логи. Запустите: sudo journalctl -u awg-exporter -f"
}
echo ""

echo "=== Рекомендации ==="
echo "Если метрик нет, проверьте логи: sudo journalctl -u awg-exporter -f"
echo "Если контейнер называется по-другому, измените имя в exporter.py"
echo "Если используется команда 'awg' вместо 'wg', измените команду в exporter.py"
