# yt-ad-filter

A YouTube ad-blocker running as a [mitmproxy](https://mitmproxy.org/) transparent HTTPS proxy in Docker.

Works on any device on your network — phones, smart TVs, browsers — with no browser extension required.

## How it works

1. All HTTPS traffic routes through the proxy on port 8080
2. The proxy strips ad scheduling data from YouTube's player API responses and HTML pages
3. Ad tracking/analytics URLs are blocked with `204 No Content`

## Setup

### 1. Run the proxy

```bash
git clone https://github.com/tihomirkolev-modeshift/yt-ad-filter.git
cd yt-ad-filter
docker compose up -d --build
```

### 2. Install the CA certificate (once per device)

Extract the generated certificate:

```bash
docker compose cp yt-ad-filter:/root/.mitmproxy/mitmproxy-ca-cert.pem .
```

Install it on each device:

| Device | How |
|--------|-----|
| **Linux** | `sudo cp mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt && sudo update-ca-certificates` |
| **Windows** | Double-click the `.pem`, install to **Trusted Root Certification Authorities** (Local Machine) |
| **Android** | Settings → Security → Install certificate → CA certificate |
| **iOS/macOS** | AirDrop the file → Settings → General → VPN & Device Management → trust it |

### 3. Configure proxy on each device

Set HTTP/HTTPS proxy to:
- **Host:** `<ip-of-your-linux-machine>`
- **Port:** `8080`

> **For browsers on Windows:** Go to Settings → Proxy → Manual proxy setup

### 4. Force TCP (block QUIC) — optional but recommended

On the machine running Docker, block outbound UDP 443 to prevent browsers from bypassing the proxy via QUIC:

```bash
# Linux (iptables)
sudo iptables -I OUTPUT -p udp --dport 443 -j DROP
sudo iptables -I FORWARD -p udp --dport 443 -j DROP
```

Or add to `/etc/ufw/before.rules` for persistence.

## Logs

```bash
docker compose logs -f
```

## Files

| File | Purpose |
|------|---------|
| `addon.py` | mitmproxy addon — blocks ad domains/URLs, strips ad JSON keys |
| `Dockerfile` | Container image |
| `docker-compose.yml` | Service definition with persistent cert volume |
