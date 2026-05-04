import logging
import aiohttp
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DOMAIN = "brivo_access"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_API_KEY = "api_key"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_CLIENT_ID): cv.string,
        vol.Required(CONF_CLIENT_SECRET): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)

AUTH_URL = "https://auth.brivo.com/oauth/token"
BASE_URL = "https://api.brivo.com/v1"

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Brivo Access component."""
    conf = config.get(DOMAIN)
    if conf is None:
        _LOGGER.error("brivo_access configuration missing")
        return True

    client_id = conf[CONF_CLIENT_ID]
    client_secret = conf[CONF_CLIENT_SECRET]
    api_key = conf[CONF_API_KEY]
    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]

    hass.data[DOMAIN] = {
        "token": None
    }

    async def get_token():
        auth = aiohttp.BasicAuth(client_id, client_secret)
        payload = {
            'grant_type': 'password',
            'username': username,
            'password': password,
            'scope': 'brivo.api'
        }
        headers = {
            'api-key': api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(AUTH_URL, data=payload, headers=headers, auth=auth, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        hass.data[DOMAIN]["token"] = data.get("access_token")
                        _LOGGER.info("Successfully fetched Brivo token")
                        return True
                    else:
                        _LOGGER.error("Brivo auth failed: %s", await resp.text())
                        return False
            except Exception as e:
                _LOGGER.error("Brivo auth exception: %s", e)
                return False

    async def handle_unlock_door(call):
        """Handle the service call to unlock a door."""
        door_id = call.data.get("door_id")
        if not door_id:
            _LOGGER.error("No door_id provided")
            return

        token = hass.data[DOMAIN].get("token")
        if not token:
            success = await get_token()
            if not success:
                return
            token = hass.data[DOMAIN].get("token")

        url = f"{BASE_URL}/api/access-points/{door_id}/activate"
        headers = {
            'api-key': api_key,
            'Authorization': f'Bearer {token}'
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, timeout=10) as resp:
                    if resp.status == 401:
                        # Refresh token and retry
                        _LOGGER.info("Brivo token expired, refreshing...")
                        success = await get_token()
                        if success:
                            token = hass.data[DOMAIN]["token"]
                            headers['Authorization'] = f'Bearer {token}'
                            async with session.post(url, headers=headers, timeout=10) as retry_resp:
                                if retry_resp.status != 200:
                                    _LOGGER.error("Retry unlock failed: %s", await retry_resp.text())
                                else:
                                    _LOGGER.info("Successfully unlocked door %s", door_id)
                        return
                    if resp.status != 200:
                        _LOGGER.error("Unlock failed: %s", await resp.text())
                    else:
                        _LOGGER.info("Successfully unlocked door %s", door_id)
            except Exception as e:
                _LOGGER.error("Unlock exception: %s", e)

    hass.services.async_register(DOMAIN, "unlock_door", handle_unlock_door)
    
    _LOGGER.info("Brivo Access component successfully set up")
    return True
