# pylint: disable=duplicate-code
"""The IntesisHome integration."""
from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "intesisaccloud"
PLATFORMS = ["climate", "switch"]


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
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("controller", {})

    device_type = entry.data.get(CONF_DEVICE)
    
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

    try:
        if isinstance(controller, IntesisBox):
            await controller.connect()
        else:
            await controller.poll_status()
    except (IHAuthenticationError, IHConnectionError) as ex:
        raise ConfigEntryNotReady from ex

    hass.data[DOMAIN]["controller"][entry.unique_id] = controller

    await hass.config_entries.async_forward_entry_setups(entry, ["climate", "switch"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # example
    # unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, "climate", "switch")]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
