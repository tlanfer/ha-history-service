"""The history access service."""

import datetime
import logging

import voluptuous as vol

from homeassistant.components.recorder import get_instance, history
from homeassistant.components.recorder.util import session_scope
from homeassistant.config import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers import config_validation as cv
import homeassistant.util.dt as dt_util

from .const import DOMAIN

PLATFORMS: list[Platform] = []

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up entry."""

    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration."""

    def get_history_data(start_time, end_time, entity_ids):
        with session_scope(hass=hass, read_only=True) as session:
            return history.get_significant_states_with_session(
                hass=hass,
                session=session,
                start_time=start_time,
                end_time=end_time,
                entity_ids=entity_ids,
                filters=None,
                compressed_state_format=False,
                include_start_time_state=True,
                minimal_response=True,
                no_attributes=True,
                significant_changes_only=True,
            )

    async def handle_retrieve(call: ServiceCall) -> ServiceResponse:
        entity_ids = call.data["entity_ids"]

        end_time = dt_util.utcnow()
        start_time = end_time - datetime.timedelta(hours=1)

        if "start_time" in call.data:
            start_time = call.data["start_time"].astimezone()

        if "end_time" in call.data:
            end_time = call.data["end_time"].astimezone()

        if start_time > end_time:
            raise "start_time must be before end_time"

        return await get_instance(hass).async_add_executor_job(
            get_history_data,
            start_time,
            end_time,
            entity_ids,
        )

    hass.data.setdefault(DOMAIN, {})

    hass.services.async_register(
        DOMAIN,
        "retrieve",
        handle_retrieve,
        supports_response=SupportsResponse.ONLY,
        schema=vol.Schema(
            {
                vol.Required("entity_ids"): cv.entity_ids,
                vol.Optional("start_time"): cv.datetime,
                vol.Optional("end_time"): cv.datetime,
            }
        ),
    )

    return True
