# Brivo Access for Home Assistant

A custom component for Home Assistant that enables true Administrator-level remote unlocks for Brivo Access doors directly over your local network, with zero latency and no digital credential required.

## Features
- **Administrator Bypass**: Utilizes the hidden `/activate` endpoint to perform native momentary door strikes.
- **Lightning Fast**: Powered natively by Home Assistant's `aiohttp` over your host network.
- **Local Network**: No third-party intermediaries.

## Installation

### HACS
1. Open HACS and add a Custom Repository: `https://github.com/thelogicwizards/brivo-home-assistant`.
2. Select "Integration" as the category.
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

## Usage
Once installed, a new service `brivo_access.unlock_door` will be available in Home Assistant.

You can use it in your template buttons or automations:
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
