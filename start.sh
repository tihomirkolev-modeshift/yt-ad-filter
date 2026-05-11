#!/bin/sh
set -e

CERT_DIR=/root/.mitmproxy
CERT_FILE=$CERT_DIR/mitmproxy-ca-cert.pem

# Start mitmproxy in the background
mitmdump \
  --listen-host 0.0.0.0 \
  --listen-port 8080 \
  --mode ${MITM_MODE:-regular} \
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
