FROM python:3.12-slim

RUN pip install --no-cache-dir mitmproxy

WORKDIR /app
COPY addon.py .

VOLUME ["/root/.mitmproxy"]
EXPOSE 8080 8888
ENV MITM_MODE=transparent

CMD ["/bin/sh", "-c", "\
  mitmdump --listen-host 0.0.0.0 --listen-port 8080 --mode ${MITM_MODE} --set block_global=false -s /app/addon.py & \
  MITM_PID=$!; \
  until [ -f /root/.mitmproxy/mitmproxy-ca-cert.pem ]; do sleep 1; done; \
  cd /root/.mitmproxy && python3 -m http.server 8888 & \
  wait $MITM_PID"]
