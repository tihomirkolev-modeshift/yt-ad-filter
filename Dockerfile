FROM python:3.12-slim

RUN pip install --no-cache-dir mitmproxy

WORKDIR /app
COPY addon.py .
COPY start.sh /start.sh
RUN chmod +x /start.sh

# mitmproxy stores generated CA cert here
VOLUME ["/root/.mitmproxy"]

# 8080 = proxy, 8888 = CA cert download
EXPOSE 8080 8888

# MITM_MODE=regular      -> explicit proxy (set proxy on each device manually)
# MITM_MODE=transparent  -> transparent mode (MikroTik/router redirects traffic)
ENV MITM_MODE=regular

CMD ["/start.sh"]
