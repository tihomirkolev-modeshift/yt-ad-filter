FROM python:3.12-slim

RUN pip install --no-cache-dir mitmproxy

WORKDIR /app
COPY addon.py .

# mitmproxy stores generated CA cert here
VOLUME ["/root/.mitmproxy"]

EXPOSE 8080

# MITM_MODE=regular  → explicit proxy (set proxy on each device manually)
# MITM_MODE=transparent → transparent mode (MikroTik/router redirects traffic)
ENV MITM_MODE=regular

CMD mitmdump --listen-host 0.0.0.0 --listen-port 8080 \
    --mode ${MITM_MODE} \
    --set block_global=false \
    -s /app/addon.py
