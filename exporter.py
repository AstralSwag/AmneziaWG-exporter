import subprocess
import time
import json
import os
from prometheus_client import start_http_server, Gauge

# Метрики Prometheus - используем Gauge для простоты
received_bytes = Gauge(
    'awg_received_bytes_total',
    'Общее количество полученных байт от пира',
    ['interface', 'public_key', 'client_name']
)

sent_bytes = Gauge(
    'awg_sent_bytes_total',
    'Общее количество отправленных байт пиру',
    ['interface', 'public_key', 'client_name']
)

# Метрики скорости (байт/сек)
received_rate = Gauge(
    'awg_received_rate_bytes_per_sec',
    'Скорость получения данных в байтах в секунду',
    ['interface', 'public_key', 'client_name']
)

sent_rate = Gauge(
    'awg_sent_rate_bytes_per_sec',
    'Скорость отправки данных в байтах в секунду',
    ['interface', 'public_key', 'client_name']
)

latest_handshake = Gauge(
    'awg_latest_handshake_seconds',
    'Время последнего handshake в секундах с эпохи (0 если не было)',
    ['interface', 'public_key', 'client_name']
)

# Словарь для хранения предыдущих значений и времени
previous_data = {}

def load_peer_names(config_file='peer_names.json'):
    """Загружает маппинг публичных ключей на имена пиров"""
    # Если путь относительный, ищем в директории скрипта
    if not os.path.isabs(config_file):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, config_file)
    
    print(f"Загрузка конфигурации из: {config_file}")
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                peer_names = json.load(f)
                print(f"Загружено имен пиров: {len(peer_names)}")
                for key, name in peer_names.items():
                    print(f"  {key[:16]}... -> {name}")
                return peer_names
        except Exception as e:
            print(f"Ошибка загрузки конфигурации имен пиров: {e}")
            return {}
    else:
        print(f"Файл {config_file} не найден, используются дефолтные имена")
    return {}

def get_client_name(public_key, peer_names):
    """Возвращает имя клиента по публичному ключу или сокращенный ключ"""
    if public_key in peer_names:
        name = peer_names[public_key]
        print(f"  Найдено имя для ключа {public_key[:16]}...: {name}")
        return name
    # Если имя не задано, возвращаем первые 8 символов ключа
    short_name = public_key[:8] if len(public_key) > 8 else public_key
    print(f"  Имя не найдено для ключа {public_key[:16]}..., используем: {short_name}")
    return short_name

def collect_metrics():
    global previous_data
    peer_names = load_peer_names()
    current_time = time.time()
    
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

                # Ключ для хранения предыдущих данных
                peer_key = f"{interface}:{public_key}"

                # Устанавливаем метрики общих байт
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

                # Рассчитываем скорость
                if peer_key in previous_data:
                    prev_time = previous_data[peer_key]['time']
                    prev_rx = previous_data[peer_key]['rx_bytes']
                    prev_tx = previous_data[peer_key]['tx_bytes']
                    
                    time_diff = current_time - prev_time
                    
                    if time_diff > 0:
                        rx_rate = max(0, (rx_bytes - prev_rx) / time_diff)
                        tx_rate = max(0, (tx_bytes - prev_tx) / time_diff)
                        
                        received_rate.labels(
                            interface=interface,
                            public_key=public_key,
                            client_name=client_name
                        ).set(rx_rate)
                        
                        sent_rate.labels(
                            interface=interface,
                            public_key=public_key,
                            client_name=client_name
                        ).set(tx_rate)
                        
                        print(f"  Скорость: RX={rx_rate:.2f} B/s, TX={tx_rate:.2f} B/s")
                else:
                    # Первый запуск - устанавливаем скорость в 0
                    received_rate.labels(
                        interface=interface,
                        public_key=public_key,
                        client_name=client_name
                    ).set(0)
                    
                    sent_rate.labels(
                        interface=interface,
                        public_key=public_key,
                        client_name=client_name
                    ).set(0)

                # Сохраняем текущие данные для следующего расчета
                previous_data[peer_key] = {
                    'time': current_time,
                    'rx_bytes': rx_bytes,
                    'tx_bytes': tx_bytes
                }

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
