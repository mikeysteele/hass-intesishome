# pylint: disable=duplicate-code
"""The IntesisHome integration."""
from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .manager import IntesisManager
DOMAIN = "intesisaccloud"
PLATFORMS = ["climate", "switch"]

import logging
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IntesisHome from a config entry."""
    from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_PASSWORD, CONF_USERNAME
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.exceptions import ConfigEntryNotReady

    from pyintesishome import (
        IHAuthenticationError,
        IHConnectionError,
        IntesisBox,
        IntesisHome,
        IntesisHomeLocal,
    )
    from pyintesishome.const import (
        DEVICE_INTESISBOX,
        DEVICE_INTESISHOME_LOCAL,
        DEVICE_INTESISHOME,
        DEVICE_ANYWAIR,
        DEVICE_AIRCONWITHME,
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("controller", {})

    device_type = entry.data.get(CONF_DEVICE)
    _LOGGER.debug("Initializing controller for device type: %s", device_type)
    
    if device_type == DEVICE_INTESISBOX:
        controller = IntesisBox(entry.data[CONF_HOST], loop=hass.loop)
    elif device_type == DEVICE_INTESISHOME_LOCAL:
        controller = IntesisHomeLocal(
            entry.data[CONF_HOST],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            loop=hass.loop,
            websession=async_get_clientsession(hass),
        )
    else:
        controller = IntesisHome(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            loop=hass.loop,
            device_type=device_type,
            websession=async_get_clientsession(hass),
        )

    manager = IntesisManager(hass, controller, entry, device_type)
    try:
        await manager.async_connect()
    except (IHAuthenticationError, IHConnectionError) as ex:
        _LOGGER.error("Connection failed: %s", ex)
        raise ConfigEntryNotReady from ex

    hass.data[DOMAIN]["controller"][entry.unique_id] = manager

    _LOGGER.debug("Forwarding entry setups for climate and switch")
    await hass.config_entries.async_forward_entry_setups(entry, ["climate", "switch"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        manager = hass.data[DOMAIN]["controller"].pop(entry.unique_id)
        if manager:
            await manager.stop()
            _LOGGER.debug("Controller stopped")

    return unload_ok


