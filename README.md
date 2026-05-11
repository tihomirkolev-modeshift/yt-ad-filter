# yt-ad-filter

A YouTube ad-blocker running as a [mitmproxy](https://mitmproxy.org/) transparent HTTPS proxy in Docker.

Works on any device on your network — phones, smart TVs, browsers — with no browser extension required.

## How it works

1. All HTTPS traffic routes through the proxy on port 8080
2. The proxy strips ad scheduling data from YouTube's player API responses and HTML pages
3. Ad tracking/analytics URLs are blocked with `204 No Content`

---

## Option A — Manual per-device proxy (simple)

Run the container, set proxy settings on each device manually.

### 1. Start (explicit proxy mode)

Edit `docker-compose.yml` and change:
- `MITM_MODE=transparent` → `MITM_MODE=regular`
- `network_mode: host` → remove it and add `ports: ["8080:8080"]`

Then:
```bash
git clone https://github.com/tihomirkolev-modeshift/yt-ad-filter.git
cd yt-ad-filter
docker compose up -d --build
```

### 2. Install CA cert (once per device)

Download from: `http://192.168.10.99:8888/mitmproxy-ca-cert.pem`

| Device | How |
|--------|-----|
| **Linux** | `sudo cp mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt && sudo update-ca-certificates` |
| **Windows** | Double-click the `.pem` → install to **Trusted Root Certification Authorities** (Local Machine) |
| **Android** | Settings → Security → Install certificate → CA certificate |
| **iOS/macOS** | Open URL in Safari → Settings → General → VPN & Device Management → trust it |

### 3. Set proxy on each device

- **Host:** `192.168.10.99`
- **Port:** `8080`

---

## Option B — MikroTik transparent redirect (automatic, all devices)

MikroTik automatically routes all LAN traffic through the proxy. Devices do **not** need to configure a proxy manually — but still need the CA cert installed (one-time).

### Architecture

```
LAN devices  →  MikroTik (policy route, no NAT)  →  192.168.10.99 (Linux proxy)
                                                         ↓  iptables TPROXY
                                                       mitmproxy:8080
                                                         ↓
                                                       YouTube
```

### Step 1 — Clone and start the container on 192.168.10.99

```bash
git clone https://github.com/tihomirkolev-modeshift/yt-ad-filter.git
cd yt-ad-filter
docker compose up -d --build
```

### Step 2 — iptables on 192.168.10.99

```bash
# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf

# TPROXY: redirect port 80 and 443 to mitmproxy on port 8080
sudo iptables -t mangle -A PREROUTING -p tcp --dport 443 -j TPROXY \
    --tproxy-mark 0x1/0x1 --on-port 8080
sudo iptables -t mangle -A PREROUTING -p tcp --dport 80  -j TPROXY \
    --tproxy-mark 0x1/0x1 --on-port 8080

# Policy routing: deliver TPROXY-marked packets locally
sudo ip rule add fwmark 1 lookup 100
sudo ip route add local 0.0.0.0/0 dev lo table 100
```

To persist across reboots, save iptables rules:
```bash
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

And add to `/etc/rc.local` before `exit 0`:
```bash
ip rule add fwmark 1 lookup 100
ip route add local 0.0.0.0/0 dev lo table 100
```

### Step 3 — MikroTik rules

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

### Step 4 — Install CA cert on each device

Download from: `http://192.168.10.99:8888/mitmproxy-ca-cert.pem`

Same installation steps as Option A above.

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
