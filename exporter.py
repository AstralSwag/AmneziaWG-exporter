import subprocess
import time
import json
import os
from prometheus_client import start_http_server, Gauge

# Prometheus metrics - using Gauge for simplicity
received_bytes = Gauge(
    'awg_received_bytes_total',
    'Total bytes received from peer',
    ['interface', 'public_key', 'client_name']
)

sent_bytes = Gauge(
    'awg_sent_bytes_total',
    'Total bytes sent to peer',
    ['interface', 'public_key', 'client_name']
)

# Rate metrics (bytes/sec)
received_rate = Gauge(
    'awg_received_rate_bytes_per_sec',
    'Data receive rate in bytes per second',
    ['interface', 'public_key', 'client_name']
)

sent_rate = Gauge(
    'awg_sent_rate_bytes_per_sec',
    'Data send rate in bytes per second',
    ['interface', 'public_key', 'client_name']
)

latest_handshake = Gauge(
    'awg_latest_handshake_seconds',
    'Time of last handshake in seconds since epoch (0 if never)',
    ['interface', 'public_key', 'client_name']
)

# Dictionary for storing previous values and time
previous_data = {}

def load_peer_names_from_container():
    """Loads mapping of public keys to peer names from amnezia-awg container"""
    try:
        print("Loading client names from amnezia-awg container...")
        output = subprocess.check_output(
            ['docker', 'exec', 'amnezia-awg', 'cat', '/opt/amnezia/awg/clientsTable'],
            stderr=subprocess.STDOUT
        ).decode('utf-8').strip()
        
        clients_data = json.loads(output)
        peer_names = {}
        
        for client in clients_data:
            client_id = client.get('clientId', '')
            user_data = client.get('userData', {})
            client_name = user_data.get('clientName', '')
            
            if client_id and client_name:
                peer_names[client_id] = client_name
                print(f"  {client_id[:16]}... -> {client_name}")
        
        print(f"Loaded {len(peer_names)} client names from container")
        return peer_names
        
    except subprocess.CalledProcessError as e:
        print(f"Error reading clientsTable from container: {e}")
        if e.output:
            print(e.output.decode('utf-8', errors='replace'))
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing clientsTable JSON: {e}")
        return {}
    except Exception as e:
        print(f"Unexpected error loading client names from container: {e}")
        return {}

def load_peer_names_from_file(config_file='peer_names.json'):
    """Loads mapping of public keys to peer names from local file (fallback)"""
    # If path is relative, look in script directory
    if not os.path.isabs(config_file):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, config_file)
    
    print(f"Loading fallback configuration from: {config_file}")
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                peer_names = json.load(f)
                print(f"Loaded fallback peer names: {len(peer_names)}")
                for key, name in peer_names.items():
                    print(f"  {key[:16]}... -> {name}")
                return peer_names
        except Exception as e:
            print(f"Error loading peer names configuration: {e}")
            return {}
    else:
        print(f"Fallback file {config_file} not found")
    return {}

def load_peer_names():
    """Loads peer names, first trying container, then fallback to local file"""
    # Try to load from container first
    peer_names = load_peer_names_from_container()
    
    # If container method failed or returned empty, try fallback file
    if not peer_names:
        print("Container method failed, trying fallback file...")
        peer_names = load_peer_names_from_file()
    
    return peer_names

def get_client_name(public_key, peer_names):
    """Returns client name by public key or shortened key"""
    if public_key in peer_names:
        name = peer_names[public_key]
        print(f"  Found name for key {public_key[:16]}...: {name}")
        return name
    # If name is not set, return first 8 characters of key
    short_name = public_key[:8] if len(public_key) > 8 else public_key
    print(f"  Name not found for key {public_key[:16]}..., using: {short_name}")
    return short_name

def collect_metrics():
    global previous_data
    peer_names = load_peer_names()
    current_time = time.time()
    
    try:
        # Execute command inside container
        print("Executing command: docker exec amnezia-awg wg show all dump")
        output = subprocess.check_output(
            ['docker', 'exec', 'amnezia-awg', 'wg', 'show', 'all', 'dump'],
            stderr=subprocess.STDOUT
        ).decode('utf-8').strip()

        print(f"Received output ({len(output)} characters)")
        lines = output.splitlines()
        print(f"Number of lines: {len(lines)}")

        current_interface = None
        peers_found = 0

        for line in lines:
            if not line.strip():
                continue

            fields = line.split('\t')

            # First line — interface description
            if len(fields) > 8 and current_interface is None:
                current_interface = fields[0]
                continue

            # Peer lines — expect at least 8 fields
            if len(fields) < 8:
                continue

            try:
                interface    = fields[0]                     # wg0
                public_key   = fields[1]                     # peer public key
                latest_hs    = fields[5]                     # unix timestamp of last handshake
                rx_bytes     = int(fields[6])                # received bytes
                tx_bytes     = int(fields[7])                # sent bytes

                # Get client name
                client_name = get_client_name(public_key, peer_names)

                print(f"Processing peer: {client_name} (interface={interface}, rx={rx_bytes}, tx={tx_bytes})")

                # Key for storing previous data
                peer_key = f"{interface}:{public_key}"

                # Set total bytes metrics
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

                # Calculate rate
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
                        
                        print(f"  Rate: RX={rx_rate:.2f} B/s, TX={tx_rate:.2f} B/s")
                else:
                    # First run - set rate to 0
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

                # Save current data for next calculation
                previous_data[peer_key] = {
                    'time': current_time,
                    'rx_bytes': rx_bytes,
                    'tx_bytes': tx_bytes
                }

                # latest handshake: if 0 — means handshake never happened
                handshake_time = int(latest_hs) if latest_hs != '0' else 0
                latest_handshake.labels(
                    interface=interface,
                    public_key=public_key,
                    client_name=client_name
                ).set(handshake_time)

                peers_found += 1

            except (IndexError, ValueError) as e:
                print(f"Error parsing line: {line.strip()}")
                print(f"Reason: {e}")
                continue

        print(f"Processed peers: {peers_found}")

    except subprocess.CalledProcessError as e:
        print(f"Error executing docker exec command: {e}")
        if e.output:
            print(e.output.decode('utf-8', errors='replace'))
    except Exception as e:
        print(f"Unexpected error during metrics collection: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("Starting AmneziaWG exporter for Prometheus...")
    print("Metrics available at :9586/metrics")
    
    start_http_server(9586)
    
    while True:
        collect_metrics()
        time.sleep(30)          # update frequency — every 30 seconds
