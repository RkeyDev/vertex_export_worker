#!/bin/bash

# =============================================================================
# Docker Entrypoint — Port Forwarding Bridge
# =============================================================================
# Inside the container, "localhost" points to the container itself (not the host).
# The frontend and WebSocket server run on the HOST, so we use socat to create
# transparent TCP tunnels from container-localhost to the host machine.
#
# This preserves the browser's Origin (http://localhost:5174) and Host headers,
# which the WebSocket server validates during the handshake.
# =============================================================================

echo "[entrypoint] Starting port forwarding bridges..."

# Frontend dev server (Vite)
socat TCP-LISTEN:5174,fork,reuseaddr TCP:host.docker.internal:5174 &

# WebSocket server
socat TCP-LISTEN:9080,fork,reuseaddr TCP:host.docker.internal:9080 &

# Brief pause to let socat bind the ports
sleep 0.5

echo "[entrypoint] Port forwarding active — launching export worker..."
exec python -m app.main
