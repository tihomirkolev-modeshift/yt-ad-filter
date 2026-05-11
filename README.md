# yt-ad-filter

YouTube ad-blocker — mitmproxy transparent HTTPS proxy in Docker, routed via MikroTik.

## How it works

- MikroTik routes all LAN TCP 80/443 traffic to the proxy (no per-device config needed)
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

The container automatically sets up iptables TPROXY rules and IP forwarding on startup. No manual network configuration needed on the Linux host.

### Step 2 — MikroTik rules

Open Winbox → Terminal (or SSH into 192.168.10.1) and paste:

```routeros
# Skip the proxy machine itself to prevent routing loop
/ip firewall mangle
add chain=prerouting src-address=192.168.10.99 action=accept \
    comment="Skip proxy machine - no redirect loop" passthrough=yes

add chain=prerouting in-interface=bridge-net protocol=tcp dst-port=443 \
    src-address=192.168.10.0/24 action=mark-routing \
    new-routing-mark=to-proxy passthrough=no \
    comment="Route HTTPS to yt-ad-filter proxy"

add chain=prerouting in-interface=bridge-net protocol=tcp dst-port=80 \
    src-address=192.168.10.0/24 action=mark-routing \
    new-routing-mark=to-proxy passthrough=no \
    comment="Route HTTP to yt-ad-filter proxy"

# Route marked packets to the proxy machine
/ip route
add dst-address=0.0.0.0/0 routing-mark=to-proxy \
    gateway=192.168.10.99 comment="yt-ad-filter proxy route"

# Block QUIC (UDP 443) - forces browsers to use TCP so proxy can intercept
/ip firewall filter
add chain=forward in-interface=bridge-net protocol=udp dst-port=443 \
    action=drop comment="Block QUIC/HTTP3 - force TCP for proxy" \
    place-before=[find comment="Drop all forward"]
```

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

```bash
docker compose logs -f
```

## Files

| File | Purpose |
|------|---------|
| `addon.py` | mitmproxy addon — blocks ad domains/URLs, strips ad JSON keys |
| `Dockerfile` | Container image (supports `MITM_MODE=regular` or `transparent`) |
| `docker-compose.yml` | Single container — proxy on :8080 + cert server on :8888 |
| `start.sh` | Entrypoint — starts mitmproxy then cert HTTP server in same container |
