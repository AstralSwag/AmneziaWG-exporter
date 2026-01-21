#!/bin/bash

echo "=== AmneziaWG Exporter Diagnostics ==="
echo ""

echo "1. Checking AmneziaWG container:"
docker ps | grep -i amnezia || echo "❌ Container not found!"
echo ""

echo "2. Checking wg command inside container:"
docker exec amnezia-awg wg show all dump 2>&1 | head -5 || {
    echo "❌ Error executing 'wg'. Trying 'awg'..."
    docker exec amnezia-awg awg show all dump 2>&1 | head -5 || echo "❌ Both commands don't work!"
}
echo ""

echo "3. Checking exporter service status:"
systemctl is-active awg-exporter 2>/dev/null || echo "❌ Service not running or not installed"
echo ""

echo "4. Checking metrics on port 9586:"
curl -s http://localhost:9586/metrics | grep -E "awg_(sent|received|latest)" | head -5 || {
    echo "❌ awg_* metrics not found!"
    echo ""
    echo "Checking if exporter is working at all:"
    curl -s http://localhost:9586/metrics | grep python_info || echo "❌ Exporter not responding on port 9586"
}
echo ""

echo "5. Latest exporter logs:"
journalctl -u awg-exporter -n 20 --no-pager 2>/dev/null || {
    echo "❌ Failed to get logs. Run: sudo journalctl -u awg-exporter -f"
}
echo ""

echo "=== Recommendations ==="
echo "If no metrics, check logs: sudo journalctl -u awg-exporter -f"
echo "If container has different name, change name in exporter.py"
echo "If using 'awg' command instead of 'wg', change command in exporter.py"