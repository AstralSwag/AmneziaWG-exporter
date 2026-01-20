import subprocess
import time
import json
import os
from prometheus_client import start_http_server, Gauge

# Метрики Prometheus
received_bytes = Gauge(
    'awg_received_bytes',
    'Общее количество полученных байт от пира',
    ['interface', 'public_key', 'client_name']
)

sent_bytes = Gauge(
    'awg_sent_bytes',
    'Общее количество отправленных байт пиру',
    ['interface', 'public_key', 'client_name']
)

latest_handshake = Gauge(
    'awg_latest_handshake_seconds',
    'Время последнего handshake в секундах с эпохи (0 если не было)',
    ['interface', 'public_key', 'client_name']
)

def load_peer_names(config_file='peer_names.json'):
    """Загружает маппинг публичных ключей на имена пиров"""
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки конфигурации имен пиров: {e}")
            return {}
    return {}

def get_client_name(public_key, peer_names):
    """Возвращает имя клиента по публичному ключу или сокращенный ключ"""
    if public_key in peer_names:
        return peer_names[public_key]
    # Если имя не задано, возвращаем первые 8 символов ключа
    return public_key[:8] if len(public_key) > 8 else public_key

def collect_metrics():
    peer_names = load_peer_names()
    
    try:
        # Выполняем команду внутри контейнера
        print("Выполняем команду: docker exec amnezia-awg wg show all dump")
        output = subprocess.check_output(
            ['docker', 'exec', 'amnezia-awg', 'wg', 'show', 'all', 'dump'],
            stderr=subprocess.STDOUT
        ).decode('utf-8').strip()

        print(f"Получен вывод ({len(output)} символов)")
        lines = output.splitlines()
        print(f"Количество строк: {len(lines)}")

        current_interface = None
        peers_found = 0

        for line in lines:
            if not line.strip():
                continue

            fields = line.split('\t')

            # Первая строка — описание интерфейса
            if len(fields) > 8 and current_interface is None:
                current_interface = fields[0]
                continue

            # Строки пиров — ожидаем минимум 8 полей
            if len(fields) < 8:
                continue

            try:
                interface    = fields[0]                     # wg0
                public_key   = fields[1]                     # публичный ключ пира
                latest_hs    = fields[5]                     # unix timestamp последнего handshake
                rx_bytes     = int(fields[6])                # получено байт
                tx_bytes     = int(fields[7])                # отправлено байт

                # Получаем имя клиента
                client_name = get_client_name(public_key, peer_names)

                print(f"Обработка пира: {client_name} (interface={interface}, rx={rx_bytes}, tx={tx_bytes})")

                # Устанавливаем метрики
                received_bytes.labels(
                    interface=interface,
                    public_key=public_key,
                    client_name=client_name
                ).set(rx_bytes)

                sent_bytes.labels(
                    interface=interface,
                    public_key=public_key,
                    client_name=client_name
                ).set(tx_bytes)

                # latest handshake: если 0 — значит handshake не происходил
                handshake_time = int(latest_hs) if latest_hs != '0' else 0
                latest_handshake.labels(
                    interface=interface,
                    public_key=public_key,
                    client_name=client_name
                ).set(handshake_time)

                peers_found += 1

            except (IndexError, ValueError) as e:
                print(f"Ошибка парсинга строки: {line.strip()}")
                print(f"Причина: {e}")
                continue

        print(f"Обработано пиров: {peers_found}")

    except subprocess.CalledProcessError as e:
        print(f"Ошибка выполнения команды docker exec: {e}")
        if e.output:
            print(e.output.decode('utf-8', errors='replace'))
    except Exception as e:
        print(f"Неожиданная ошибка при сборе метрик: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("Запуск AmneziaWG экспортёра для Prometheus...")
    print("Метрики доступны на :9586/metrics")
    
    start_http_server(9586)
    
    while True:
        collect_metrics()
        time.sleep(30)          # частота обновления — раз в 30 секунд
