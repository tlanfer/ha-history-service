"""The history access service."""

from datetime import datetime as dt, timedelta
import enum
import logging

import voluptuous as vol
from typing import Any, cast

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
    State,
)
from homeassistant.helpers import config_validation as cv
import homeassistant.util.dt as dt_util

from .const import DOMAIN

PLATFORMS: list[Platform] = []

_LOGGER = logging.getLogger(__name__)

_ONE_DAY = timedelta(days=1)

class Window(enum.Enum):
    """Different windows for aggregations."""

    DAY = 10
    HOUR = 13
    MINUTE = 16


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

    def get_history_job(
        entity_ids: list[str],
        start_time: dt,
        end_time: dt,
    ) -> dict[str, list[State | dict[str, Any]]]:
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

    async def get_history_handler(call: ServiceCall) -> ServiceResponse:
        entity_ids = call.data["entity_ids"]

        end_time = dt_util.utcnow()
        if "end_time" in call.data:
            end_time = call.data["end_time"].astimezone()

        start_time = end_time - _ONE_DAY
        if "start_time" in call.data:
            start_time = call.data["start_time"].astimezone()

        return cast(
            ServiceResponse,
            await get_instance(hass).async_add_executor_job(
                get_history_job, entity_ids, start_time, end_time
            ),
        )

    hass.data.setdefault(DOMAIN, {})

    hass.services.async_register(
        DOMAIN,
        "get_history",
        get_history_handler,
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
