FROM python:3.12-slim

RUN pip install --no-cache-dir mitmproxy

WORKDIR /app
COPY addon.py .

# mitmproxy stores generated CA cert here
VOLUME ["/root/.mitmproxy"]

EXPOSE 8080

# --set block_global=false allows traffic from non-localhost clients (other devices on the LAN)
CMD ["mitmdump", "--listen-host", "0.0.0.0", "--listen-port", "8080", \
     "--set", "block_global=false", \
     "-s", "/app/addon.py"]
