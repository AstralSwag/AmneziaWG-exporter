#!/bin/bash

# Script for generating peer_names.json template from current peers

echo "Getting peer list from amnezia-awg container..."
echo ""

# Get wg show output
output=$(docker exec amnezia-awg wg show all dump 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "Error: failed to execute command in container"
    echo "Check that container is running: docker ps | grep amnezia"
    exit 1
fi

# Parse peer public keys (skip first line with interface)
echo "{"
first=true

echo "$output" | tail -n +2 | while IFS=$'\t' read -r interface pubkey rest; do
    if [ -n "$pubkey" ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo ","
        fi
        # Take first 8 characters of key as default name
        short_key="${pubkey:0:8}"
        echo -n "  \"$pubkey\": \"Client_${short_key}\""
    fi
done

echo ""
echo "}"
echo ""
echo "Copy the output above to /opt/awg-exporter/peer_names.json"
echo "and replace client names with meaningful ones."
echo ""
echo "After changes restart the service:"
echo "  sudo systemctl restart awg-exporter"
