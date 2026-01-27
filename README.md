# AmneziaWG Prometheus Exporter
<img width="1717" height="690" alt="image" src="https://github.com/user-attachments/assets/6f1b801e-6109-4208-a1a8-dbd9877ef5a4" />

AmneziaWG metrics exporter for Prometheus with support for custom client names.
Works with AmneziaVPN deployed on a server in a container using the official client application. The exporter connects to the amnezia-awg container, executes the command
```bash
wg show all dump
```
and generates metrics.

The repository also includes a ready-to-use docker-compose file for running Prometheus and Grafana locally. Start it with docker compose up -d if needed

## Installation

### Automatic Installation

```bash
chmod +x install.sh
sudo ./install.sh
```

### Manual Installation

1. Install dependencies:
```bash
pip3 install prometheus-client
```
May complain about missing virtual environment. In this case, either activate venv or run installation with --break-system-packages flag. Automatic installation runs with this flag.

2. Create directory and copy files:
```bash
sudo mkdir -p /opt/awg-exporter
sudo cp exporter.py /opt/awg-exporter/
sudo cp peer_names.json /opt/awg-exporter/
```

3. Install systemd service:
```bash
sudo cp awg-exporter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable awg-exporter.service
sudo systemctl start awg-exporter.service
```
The service runs from /opt/awg-exporter, so the directory name is important. Alternatively, change the directory in the service file

## Client Names Configuration

Edit the file `/opt/awg-exporter/peer_names.json`:

```json
{
  "PUBLIC_KEY_CLIENT_1": "Laptop_John",
  "PUBLIC_KEY_CLIENT_2": "Phone_Mary",
  "PUBLIC_KEY_CLIENT_3": "Office_PC"
}
```

Where `PUBLIC_KEY_CLIENT_X` is the peer's public key from WireGuard.

After changing the file, restart the service:
```bash
sudo systemctl restart awg-exporter
```

## Metrics

The exporter provides the following metrics:

- `awg_received_bytes` - number of bytes received from peer
- `awg_sent_bytes` - number of bytes sent to peer
- `awg_latest_handshake_seconds` - time of last handshake (unix timestamp)

All metrics have labels:
- `interface` - interface name (e.g., wg0)
- `public_key` - peer's public key
- `client_name` - client name (from peer_names.json or first 8 characters of key)

## Service Management

```bash
# Check status
sudo systemctl status awg-exporter

# Restart
sudo systemctl restart awg-exporter

# Stop
sudo systemctl stop awg-exporter

# Start
sudo systemctl start awg-exporter

# View logs
sudo journalctl -u awg-exporter -f
```

## Troubleshooting

### 1. Check that the exporter provides metrics

```bash
curl http://localhost:9586/metrics | grep awg_
```

You should see lines like:
```
awg_sent_bytes{client_name="Client1",interface="awg0",public_key="..."} 12345.0
awg_received_bytes{client_name="Client1",interface="awg0",public_key="..."} 67890.0
```

### 2. Check exporter logs

```bash
sudo journalctl -u awg-exporter -f
```

You should see messages like:
```
Executing command: docker exec amnezia-awg wg show all dump
Received output (XXX characters)
Number of lines: X
Processing peer: Client_Name (interface=awg0, rx=..., tx=...)
Processed peers: X
```

### 3. Check container name

```bash
docker ps | grep amnezia
```

If the container has a different name (e.g., `amnezia-wg` instead of `amnezia-awg`), edit `/opt/awg-exporter/exporter.py`:

```python
['docker', 'exec', 'your_container_name', 'wg', 'show', 'all', 'dump'],
```

### 4. Check wg command inside container

```bash
docker exec amnezia-awg wg show all dump
```

You should get output with tabs between fields.

### 5. If awg is used instead of wg

Some versions of AmneziaWG use the `awg` command instead of `wg`. Edit `/opt/awg-exporter/exporter.py`:

```python
['docker', 'exec', 'amnezia-awg', 'awg', 'show', 'all', 'dump'],
```

### 6. Check that Prometheus collects metrics

In Prometheus UI (usually http://localhost:9090):
- Status → Targets — there should be a target `amneziawg` with UP status
- Graph → enter `awg_sent_bytes` — metrics should appear

## Prometheus Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'amneziawg'
    static_configs:
      - targets: ['localhost:9586']
```

## Grafana Dashboard

Import the dashboard into Grafana:
1. Grafana UI → Dashboards → Import
2. Upload the `grafana.json` file
3. Select your Prometheus datasource
4. Click Import

## Port

By default, the exporter listens on port `9586`.
