#!/bin/sh

CERT_DIR=/root/.mitmproxy
CERT_FILE=$CERT_DIR/mitmproxy-ca-cert.pem

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1

# Remove existing rules to avoid duplicates on container restart
iptables -t mangle -D PREROUTING -p tcp --dport 443 -j TPROXY --tproxy-mark 0x1/0x1 --on-port 8080 2>/dev/null || true
iptables -t mangle -D PREROUTING -p tcp --dport 80  -j TPROXY --tproxy-mark 0x1/0x1 --on-port 8080 2>/dev/null || true
ip rule del fwmark 1 lookup 100 2>/dev/null || true
ip route del local 0.0.0.0/0 dev lo table 100 2>/dev/null || true

# TPROXY: intercept TCP 80/443 and deliver to mitmproxy on :8080
iptables -t mangle -A PREROUTING -p tcp --dport 443 -j TPROXY --tproxy-mark 0x1/0x1 --on-port 8080
iptables -t mangle -A PREROUTING -p tcp --dport 80  -j TPROXY --tproxy-mark 0x1/0x1 --on-port 8080

# Policy route: deliver TPROXY-marked packets to the local stack
ip rule add fwmark 1 lookup 100
ip route add local 0.0.0.0/0 dev lo table 100

# Start mitmproxy in the background
mitmdump \
  --listen-host 0.0.0.0 \
  --listen-port 8080 \
  --mode ${MITM_MODE:-transparent} \
  --set block_global=false \
  -s /app/addon.py &
MITM_PID=$!

# Wait for mitmproxy to generate the CA cert
echo "[start] waiting for CA cert to be generated..."
until [ -f "$CERT_FILE" ]; do sleep 1; done
echo "[start] CA cert ready, starting cert server on :8888"

# Serve the cert dir over HTTP on port 8888
cd "$CERT_DIR"
python3 -m http.server 8888 &

# If mitmproxy dies, exit so Docker restarts the container
wait $MITM_PID
