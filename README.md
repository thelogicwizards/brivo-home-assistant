# Brivo Access for Home Assistant

A custom Home Assistant integration that enables **Administrator-level remote unlocks** for Brivo Access doors — powered natively by Home Assistant's `aiohttp` with zero latency and no digital credential required.

## Features

- **Administrator Bypass**: Utilizes the hidden `/activate` endpoint to perform native momentary door strikes.
- **Lightning Fast**: Powered natively by Home Assistant's `aiohttp` over your host network.
- **Local Network**: No third-party intermediaries.
- **Auto Token Refresh**: Handles OAuth2 token expiration gracefully — automatically refreshes and retries on `401` responses.

---

## Architecture

### How This Integration Fits

This integration is one component in a broader **edge gateway ecosystem** (codenamed "WizardBase") running at the LogicWizards office. The diagram below shows the full system architecture — the `brivo_access` custom component runs **inside** the Home Assistant container, while the surrounding infrastructure provides secure remote access, DNS filtering, monitoring, and local device control.

> **Reading the diagram:** Components with a solid border are **direct actors** in the Brivo integration flow. Components with a dashed border are part of the broader office ecosystem — they run on the same hardware but are not involved in the Brivo unlock flow.

```mermaid
graph TB
    subgraph CLOUD["☁️ Cloud Services"]
        direction LR
        CF["Cloudflare Tunnel<br/><i>office.logicwizards.dev</i><br/>───────────<br/>Zero-Trust Proxy"]
        BRIVO_API["Brivo Cloud API<br/>───────────<br/>OAuth 2.0 (Password Grant)<br/>+ API Key Auth<br/>/v1/api/access-points/{id}/activate"]
    end

    subgraph EDGE["🖥️ Edge Gateway — Raspberry Pi 5 · Debian/Linux"]
        direction TB

        subgraph DOCKER["🐳 Docker Compose"]
            direction LR

            subgraph CORE["Integration Core"]
                HA["Home Assistant<br/><i>:8123</i><br/>───────────<br/>brivo_access custom component<br/>Unified Dashboard<br/>Automations Engine"]
            end

            subgraph INFRA["Office Infrastructure"]
                CFD["cloudflared<br/>───────────<br/>Outbound Tunnel<br/>No Open Ports"]:::ecosystem
                NPM["Nginx Proxy Mgr<br/>───────────<br/>Reverse Proxy<br/>SSL Termination"]:::ecosystem
                PH["Pi-hole<br/>───────────<br/>DNS Filtering"]:::ecosystem
                JF["Jellyfin<br/><i>:8096</i><br/>───────────<br/>Media Server"]:::ecosystem
            end
        end

        subgraph SECURITY["🔒 Host Security"]
            direction LR
            UFW["UFW Firewall<br/>Default Deny<br/>172.18.0.0/16 → :8123, :8096"]:::ecosystem
            F2B["Fail2Ban · SSH Ed25519<br/>Key-Only Auth"]:::ecosystem
        end

        subgraph HW["🔌 Local Hardware"]
            direction LR
            ZWAVE["Zooz 800<br/>Z-Wave USB Stick<br/>───────────<br/>Z-Wave JS UI"]:::ecosystem
            DEVICES["Z-Wave Devices<br/>───────────<br/>Lights · Locks<br/>Thermostats"]:::ecosystem
            NETDATA["Netdata<br/>───────────<br/>Monitoring"]:::ecosystem
        end
    end

    subgraph USER["👤 User"]
        BROWSER["Browser / HA Mobile App<br/>───────────<br/>office.logicwizards.dev"]
    end

    %% === Primary Integration Flow (solid lines) ===
    BROWSER -->|"HTTPS"| CF
    CF -->|"Encrypted Tunnel"| CFD
    CFD --> NPM
    NPM --> HA
    HA -->|"OAuth2 Bearer Token + API Key<br/>POST /v1/api/access-points/{id}/activate"| BRIVO_API
    BRIVO_API -->|"200 OK · Door Unlocked"| HA

    %% === Ecosystem connections (dotted lines) ===
    HA -.->|"Z-Wave JS"| ZWAVE
    ZWAVE -.->|"908.42 MHz Mesh"| DEVICES

    %% Styling
    classDef ecosystem fill:#f5f5f5,stroke:#9e9e9e,stroke-width:1px,stroke-dasharray: 5 5,color:#616161
    classDef core fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1
    classDef cloud fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20
    classDef user fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#4a148c

    class CF,BRIVO_API cloud
    class HA core
    class BROWSER user
```

### Component Legend

| Component | Role in Brivo Integration | Notes |
|---|---|---|
| **Home Assistant** | ✅ **Core** — runs the `brivo_access` custom component | Handles OAuth2 auth, token refresh, and the `/activate` API call |
| **Brivo Cloud API** | ✅ **Core** — the target API | OAuth2 password grant + API key authentication |
| **cloudflared** | 🔗 Infrastructure — secure remote access | Cloudflare Tunnel provides Zero-Trust access to HA without opening ports |
| **Nginx Proxy Manager** | 🔗 Infrastructure — reverse proxy | Routes `office.logicwizards.dev` to the correct container |
| **Pi-hole** | 🏠 Ecosystem — DNS filtering | Network-wide ad/tracker blocking; not involved in the Brivo flow |
| **Jellyfin** | 🏠 Ecosystem — media server | Separate home service on the same hardware |
| **Z-Wave JS / Zooz 800** | 🏠 Ecosystem — local device mesh | Controls lights, thermostats, locks via 908.42 MHz; separate protocol from Brivo |
| **UFW / Fail2Ban / SSH** | 🔗 Infrastructure — host security | Default-deny firewall, intrusion prevention, key-only SSH |
| **Netdata** | 🏠 Ecosystem — monitoring | Real-time CPU/RAM/network I/O dashboards for the Pi |

### Unlock Flow

When a user taps "Unlock" in the Home Assistant dashboard:

```
User → office.logicwizards.dev
  ↓ HTTPS (Cloudflare proxy)
Cloudflare Edge → cloudflared (encrypted tunnel, 0 open ports)
  ↓ Docker internal network
Nginx Proxy Manager → Home Assistant (:8123)
  ↓ brivo_access service call
Home Assistant → Brivo Cloud API
  POST /v1/api/access-points/{door_id}/activate
  Headers: Authorization: Bearer {token}, api-key: {key}
  ↓ 200 OK
Home Assistant → User (door unlocked ✅)
```

If the token has expired, the integration automatically re-authenticates via the OAuth2 password grant and retries — no user intervention needed.

### Security Posture

The edge gateway achieves an **A+ security rating** with **zero publicly exposed ports**:

| Layer | Implementation |
|---|---|
| Remote Access | Cloudflare Tunnel (outbound-only, no port forwarding) |
| Firewall | UFW default-deny; surgical rules for Docker subnet `172.18.0.0/16` → `:8123`, `:8096` only |
| Authentication | SSH Ed25519 key-only (password auth disabled) |
| Intrusion Prevention | Fail2Ban monitoring SSH access logs |
| Durability | `log2ram` for SD card lifespan on Raspberry Pi |

---

## Installation

### HACS
1. Open HACS and add a Custom Repository: `https://github.com/thelogicwizards/brivo-home-assistant`.
2. Select **"Integration"** as the category.
3. Install the integration and restart Home Assistant.

### Configuration
Add your Brivo credentials to `configuration.yaml`:
```yaml
brivo_access:
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET"
  api_key: "YOUR_API_KEY"
  username: "YOUR_BRIVO_ADMIN_USERNAME"
  password: "YOUR_BRIVO_ADMIN_PASSWORD"
```

> ⚠️ **Security note:** Store credentials using [Home Assistant Secrets](https://www.home-assistant.io/docs/configuration/secrets/) rather than hardcoding them in `configuration.yaml`.

## Usage
Once installed, a new service `brivo_access.unlock_door` will be available in Home Assistant.

Use it in template buttons or automations:
```yaml
template:
  - button:
      - name: "Unlock Door"
        icon: mdi:door-open
        press:
          - service: brivo_access.unlock_door
            data:
              door_id: "12345678"
```

## Optional Companion: Z-Wave JS UI Sidebar

If you run a [Z-Wave JS UI](https://github.com/zwave-js/zwave-js-ui) gateway on your network (e.g. a dedicated Raspberry Pi with a Zooz 800 or Aeotec Z-Stick), you can embed it directly in your Home Assistant sidebar for a unified management experience — commission Z-Wave devices and unlock Brivo doors from the same interface.

### Prerequisites

- A Z-Wave JS UI instance accessible on your network (e.g. `http://192.168.1.100:8091`)
- [MQTT broker](https://mosquitto.org/) (e.g. Mosquitto) running alongside Z-Wave JS UI
- Z-Wave JS UI configured with **HA MQTT Discovery** enabled:
  - In Z-Wave JS UI Settings > Gateway, set `hassDiscovery: true` and `discoveryPrefix: homeassistant`
- HA [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) configured to connect to your broker

### Add Sidebar Link

> ⚠️ **Deprecation notice:** The `panel_iframe` YAML configuration was removed in recent Home Assistant versions. Use the built-in **Webpage Dashboard** feature instead.

In the HA UI:

1. Go to **Settings > Dashboards**
2. Click **"+ ADD DASHBOARD"** > select **"Webpage"**
3. Fill in:
   - **Title**: `Z-Wave JS UI`
   - **Icon**: `mdi:z-wave`
   - **URL**: Your Z-Wave JS UI URL (see below)
   - **Show in sidebar**: ON
   - **Require admin**: ON
4. Click **Create**

#### Choosing the Right URL

If your HA instance is served over **HTTPS** (e.g. via Cloudflare Tunnel, Nginx, or Nabu Casa), you **cannot** embed a plain `http://` URL — modern browsers block mixed content (HTTP iframe inside HTTPS page). You have two options:

| Scenario | URL to Use |
|---|---|
| **HA accessed over HTTP** (LAN only) | `http://<ZWAVE_HOST_IP>:8091` |
| **HA accessed over HTTPS** (remote/tunneled) | `https://<YOUR_ZWAVE_SUBDOMAIN>` (see tunnel setup below) |

### Tunnel Setup (Cloudflare)

If you use a [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) for remote HA access, you can route Z-Wave JS UI through the same tunnel to serve it over HTTPS — eliminating the mixed-content problem.

**How it works:** Cloudflare terminates SSL on the public side, then connects to your local Z-Wave JS UI over plain HTTP through the encrypted tunnel. The service type in the tunnel config is `HTTP` even though users access it via `HTTPS`:

```
Browser (HTTPS) → Cloudflare Edge (SSL termination) → Encrypted Tunnel → cloudflared → HTTP://zwave-host:8091
```

**Add a public hostname** to your tunnel:

1. Open the [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/) > **Networks** > **Tunnels**
2. Select your tunnel and go to the **Public Hostname** tab
3. Click **"Add a public hostname"** with:
   - **Subdomain**: `zwave` (or your preference)
   - **Domain**: your domain
   - **Type**: `HTTP`
   - **URL**: `<ZWAVE_HOST_IP>:8091`
4. Save — Cloudflare will auto-create the DNS record

Then set the Webpage Dashboard URL to `https://zwave.yourdomain.com`.

#### Hardening with Cloudflare Access

Exposing Z-Wave JS UI publicly — even through a tunnel — means anyone who discovers the URL could reach it. Protect it with a [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/) policy:

1. In Zero Trust Dashboard, go to **Access** > **Applications** > **Add an application**
2. Select **Self-hosted** and set the domain to your Z-Wave JS UI hostname (e.g. `zwave.yourdomain.com`)
3. Create a policy requiring authentication (e.g. **Email OTP**, **GitHub login**, or your identity provider)
4. Save — users will now be prompted to authenticate before reaching Z-Wave JS UI

This ensures only authorized users can access your Z-Wave controller, even if the URL is discovered.

### Commissioning Z-Wave Devices

Once the sidebar is configured:

1. Click **"Z-Wave JS UI"** in the HA sidebar
2. Go to **Control Panel** > **Manage Nodes** > **Add Node**
3. Select inclusion mode (**S2 Authenticated** recommended)
4. Put your Z-Wave device in pairing mode (see device manual — typically 3 quick taps on the paddle/button)
5. Complete the S2 security handshake if prompted (enter the 5-digit DSK from the device label)
6. Once the interview completes, the device **auto-discovers in HA** via MQTT within seconds
7. Find your new device in **Settings > Devices & Services > MQTT**

### MQTT Bridge Setup

Your Z-Wave gateway publishes device state over MQTT. HA subscribes to the broker and auto-discovers entities. The data flow:

```
Z-Wave Device <-> Z-Wave JS UI <-> MQTT Broker <-> Home Assistant
   (908 MHz)      (USB stick)     (Mosquitto)    (MQTT integration)
```

Set up the MQTT integration in HA:
1. Go to **Settings > Devices & Services > Add Integration > MQTT**
2. Enter your MQTT broker IP, port `1883`, and credentials
3. Z-Wave devices with `hassDiscovery` enabled will auto-populate

---

## Project Structure
```
brivo-home-assistant/
├── custom_components/
│   └── brivo_access/
│       ├── __init__.py        # Core integration (OAuth2 auth, unlock service)
│       ├── manifest.json      # HA integration metadata
│       └── services.yaml      # Service definition for unlock_door
├── hacs.json                  # HACS custom repository config
└── README.md
```

## Status

> 🟢 **Live** — The live instance at `office.logicwizards.dev` is online and operational. The integration is functional and tested.

## License

MIT
