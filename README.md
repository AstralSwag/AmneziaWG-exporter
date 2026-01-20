# AmneziaWG Prometheus Exporter

Экспортер метрик AmneziaWG для Prometheus с поддержкой пользовательских имен клиентов.

## Установка

### Автоматическая установка

```bash
chmod +x install.sh
sudo ./install.sh
```

### Ручная установка

1. Установите зависимости:
```bash
pip3 install prometheus-client
```

2. Создайте директорию и скопируйте файлы:
```bash
sudo mkdir -p /opt/awg-exporter
sudo cp exporter.py /opt/awg-exporter/
sudo cp peer_names.json /opt/awg-exporter/
```

3. Установите systemd сервис:
```bash
sudo cp awg-exporter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable awg-exporter.service
sudo systemctl start awg-exporter.service
```

## Настройка имен клиентов

Отредактируйте файл `/opt/awg-exporter/peer_names.json`:

```json
{
  "PUBLIC_KEY_CLIENT_1": "Laptop_John",
  "PUBLIC_KEY_CLIENT_2": "Phone_Mary",
  "PUBLIC_KEY_CLIENT_3": "Office_PC"
}
```

Где `PUBLIC_KEY_CLIENT_X` - это публичный ключ пира из WireGuard.

После изменения файла перезапустите сервис:
```bash
sudo systemctl restart awg-exporter
```

## Метрики

Экспортер предоставляет следующие метрики:

- `awg_received_bytes` - количество полученных байт от пира
- `awg_sent_bytes` - количество отправленных байт пиру
- `awg_latest_handshake_seconds` - время последнего handshake (unix timestamp)

Все метрики имеют лейблы:
- `interface` - имя интерфейса (например, wg0)
- `public_key` - публичный ключ пира
- `client_name` - имя клиента (из peer_names.json или первые 8 символов ключа)

## Управление сервисом

```bash
# Проверить статус
sudo systemctl status awg-exporter

# Перезапустить
sudo systemctl restart awg-exporter

# Остановить
sudo systemctl stop awg-exporter

# Запустить
sudo systemctl start awg-exporter

# Посмотреть логи
sudo journalctl -u awg-exporter -f
```

## Диагностика проблем

### 1. Проверьте что экспортер отдает метрики

```bash
curl http://localhost:9586/metrics | grep awg_
```

Должны быть строки вида:
```
awg_sent_bytes{client_name="Client1",interface="awg0",public_key="..."} 12345.0
awg_received_bytes{client_name="Client1",interface="awg0",public_key="..."} 67890.0
```

### 2. Проверьте логи экспортера

```bash
sudo journalctl -u awg-exporter -f
```

Должны быть сообщения:
```
Выполняем команду: docker exec amnezia-awg wg show all dump
Получен вывод (XXX символов)
Количество строк: X
Обработка пира: Client_Name (interface=awg0, rx=..., tx=...)
Обработано пиров: X
```

### 3. Проверьте имя контейнера

```bash
docker ps | grep amnezia
```

Если контейнер называется по-другому (например `amnezia-wg` вместо `amnezia-awg`), отредактируйте `/opt/awg-exporter/exporter.py`:

```python
['docker', 'exec', 'ваше_имя_контейнера', 'wg', 'show', 'all', 'dump'],
```

### 4. Проверьте команду wg внутри контейнера

```bash
docker exec amnezia-awg wg show all dump
```

Должен быть вывод с табуляцией между полями.

### 5. Если используется awg вместо wg

Некоторые версии AmneziaWG используют команду `awg` вместо `wg`. Отредактируйте `/opt/awg-exporter/exporter.py`:

```python
['docker', 'exec', 'amnezia-awg', 'awg', 'show', 'all', 'dump'],
```

### 6. Проверьте что Prometheus собирает метрики

В Prometheus UI (обычно http://localhost:9090):
- Status → Targets — должен быть target `amneziawg` со статусом UP
- Graph → введите `awg_sent_bytes` — должны появиться метрики

## Prometheus конфигурация

Добавьте в `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'amneziawg'
    static_configs:
      - targets: ['localhost:9586']
```

## Grafana Dashboard

Импортируйте дашборд из файла `grafana.json` в Grafana.

## Порт

По умолчанию экспортер слушает на порту `9586`.
