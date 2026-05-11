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

Download from: `http://<proxy-ip>:8888/mitmproxy-ca-cert.pem`

| Device | How |
|--------|-----|
| **Linux** | `sudo cp mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt && sudo update-ca-certificates` |
| **Windows** | Double-click the `.pem` → install to **Trusted Root Certification Authorities** (Local Machine) |
| **Android** | Settings → Security → Install certificate → CA certificate |
| **iOS/macOS** | Open URL in Safari → Settings → General → VPN & Device Management → trust it |

### 3. Set proxy on each device

- **Host:** `<proxy-ip>`
- **Port:** `8080`

---

## Option B — MikroTik transparent redirect (automatic, all devices)

MikroTik automatically routes all LAN traffic through the proxy. Devices do **not** need to configure a proxy manually — but still need the CA cert installed (one-time).

### Architecture

```
LAN devices  →  MikroTik (policy route, no NAT)  →  Linux proxy machine
                                                         ↓  iptables TPROXY
                                                       mitmproxy:8080
                                                         ↓
                                                       YouTube
```

Key: MikroTik uses **policy routing** (not dst-nat) so the original destination IP is preserved.
Linux TPROXY delivers packets to mitmproxy with the original destination intact.

### Step 1 — Start the container (transparent mode is the default)

```bash
git clone https://github.com/tihomirkolev-modeshift/yt-ad-filter.git
cd yt-ad-filter
docker compose up -d --build
```

### Step 2 — iptables on the Linux proxy machine

Run these once on the Linux host (add to `/etc/rc.local` or a systemd unit for persistence):

```bash
# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf

# TPROXY: intercept port 443 and 80, deliver to mitmproxy on port 8080
sudo iptables -t mangle -A PREROUTING -p tcp --dport 443 -j TPROXY \
    --tproxy-mark 0x1/0x1 --on-port 8080
sudo iptables -t mangle -A PREROUTING -p tcp --dport 80  -j TPROXY \
    --tproxy-mark 0x1/0x1 --on-port 8080

# Policy routing: deliver TPROXY-marked packets locally
sudo ip rule add fwmark 1 lookup 100
sudo ip route add local 0.0.0.0/0 dev lo table 100
```

> To persist `ip rule` / `ip route` across reboots, add them to `/etc/network/interfaces` or a systemd-networkd `.network` file.

### Step 3 — MikroTik rules

Open MikroTik terminal (Winbox → Terminal or SSH). Replace the placeholders:

| Placeholder | Example |
|-------------|---------|
| `<LAN_IFACE>` | `bridge` or `ether2` |
| `<LAN_SUBNET>` | `192.168.88.0/24` |
| `<PROXY_IP>` | `192.168.88.2` |

```routeros
# Mark HTTP and HTTPS from LAN for special routing (no NAT — preserves original destination)
/ip firewall mangle
add chain=prerouting in-interface=<LAN_IFACE> protocol=tcp dst-port=443 \
    src-address=<LAN_SUBNET> action=mark-routing \
    new-routing-mark=to-proxy passthrough=no comment="Route HTTPS to proxy"

add chain=prerouting in-interface=<LAN_IFACE> protocol=tcp dst-port=80 \
    src-address=<LAN_SUBNET> action=mark-routing \
    new-routing-mark=to-proxy passthrough=no comment="Route HTTP to proxy"

# Route marked packets to the proxy machine (no NAT)
/ip route
add dst-address=0.0.0.0/0 routing-mark=to-proxy gateway=<PROXY_IP> comment="Proxy route"

# Block QUIC (UDP 443) — forces browsers to use TCP so the proxy can intercept
/ip firewall filter
add chain=forward in-interface=<LAN_IFACE> protocol=udp dst-port=443 \
    action=drop comment="Block QUIC/HTTP3"
```

### Step 4 — Install CA cert on each device

Download from: `http://<proxy-ip>:8888/mitmproxy-ca-cert.pem`

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
| `docker-compose.yml` | Service definition — transparent mode + cert server on port 8888 |
