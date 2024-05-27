"""ConfigFlow for the history service."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow

from .const import DOMAIN


async def _async_has_devices(hass: HomeAssistant) -> bool:
    return True


config_entry_flow.register_discovery_flow(DOMAIN, "history_service", _async_has_devices)
