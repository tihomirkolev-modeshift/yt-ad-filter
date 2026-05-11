# yt-ad-filter

YouTube ad-blocker — mitmproxy transparent HTTPS proxy in Docker, routed via MikroTik.

## How it works

- MikroTik port-forwards LAN TCP 80/443 directly to the container on port 8080 (no per-device config needed)
- Proxy strips ad keys from YouTube's player API and HTML pages
- Ad tracking/analytics URLs are blocked with `204 No Content`
- Each device needs the CA cert installed once

---

## Setup

### Step 1 — Clone and start the container on 192.168.10.99

```bash
git clone https://github.com/tihomirkolev-modeshift/yt-ad-filter.git
cd yt-ad-filter
docker compose up -d --build
```

### Step 2 — MikroTik rules

Open Winbox → Terminal (or SSH into 192.168.10.1) and paste:

```routeros
# DST-NAT: forward all LAN HTTPS to the proxy container on port 8080
/ip firewall nat
add chain=dstnat in-interface=bridge-net protocol=tcp dst-port=443 \
    src-address=!192.168.10.99 action=dst-nat \
    to-addresses=192.168.10.99 to-ports=8080 \
    comment="Redirect HTTPS to yt-ad-filter"

add chain=dstnat in-interface=bridge-net protocol=tcp dst-port=80 \
    src-address=!192.168.10.99 action=dst-nat \
    to-addresses=192.168.10.99 to-ports=8080 \
    comment="Redirect HTTP to yt-ad-filter"

# Block QUIC (UDP 443) - forces browsers to use TCP so proxy can intercept
/ip firewall filter
add chain=forward in-interface=bridge-net protocol=udp dst-port=443 \
    action=drop comment="Block QUIC/HTTP3 - force TCP for proxy"
```

> **How it works**: MikroTik port-forwards 80/443 to the container on port 8080. mitmproxy reads the TLS SNI (HTTPS) or Host header (HTTP) to know where to connect upstream — no iptables needed on the Linux host.

### Step 3 — Install CA cert on each device

Download from: `http://192.168.10.99:8888/mitmproxy-ca-cert.pem`

| Device | How |
|--------|-----|
| **Linux** | `sudo cp mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt && sudo update-ca-certificates` |
| **Windows** | Double-click → install to **Trusted Root Certification Authorities** (Local Machine) |
| **Android** | Settings → Security → Install certificate → CA certificate |
| **iOS/macOS** | Open URL in Safari → Settings → General → VPN & Device Management → trust it |

---

## Logs

Debug logging is off by default. To enable, uncomment `DEBUG=1` in `docker-compose.yml` then restart:

```bash
docker compose up -d
docker compose logs -f
```

## Files

| File | Purpose |
|------|---------|
| `addon.py` | mitmproxy addon — blocks ad domains/URLs, strips ad JSON keys |
| `Dockerfile` | Container image — proxy on :8080 + cert server on :8888 |
| `docker-compose.yml` | Single container with port mappings |
