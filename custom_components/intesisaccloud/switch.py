"""Support for IntesisACCloud Zone Switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyintesishome import IntesisBase

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IntesisACCloud switch entities."""
    controller: IntesisBase = hass.data[DOMAIN]["controller"][config_entry.unique_id]
    ih_devices = controller.get_devices()

    entities = []

    for ih_device_id, device in ih_devices.items():
        # Zone Discovery
        number_of_zones = device.get("number_of_zones", 0)

        if number_of_zones > 0:
            _LOGGER.debug(
                "Device %s has %s zones. Discovering...", ih_device_id, number_of_zones
            )
            for zone_index in range(1, number_of_zones + 1):
                # Check initial status
                zone_status = device.get(f"zone_status_{zone_index}")

                _LOGGER.debug("Zone %s status: %s", zone_index, zone_status)

                # Filter out spill zones (7)
                if zone_status == 7 or zone_status == 'spill':
                    _LOGGER.debug("Skipping spill zone %s for device %s", zone_index, ih_device_id)
                    continue

                # Add entity for valid zone
                entities.append(IntesisZoneSwitch(controller, ih_device_id, zone_index))

    if entities:
        async_add_entities(entities)


class IntesisZoneSwitch(SwitchEntity):
    """Representation of an IntesisACCloud Zone Switch."""

    def __init__(self, controller: IntesisBase, device_id: str, zone_index: int) -> None:
        """Initialize the switch."""
        self._controller = controller
        self._device_id = device_id
        self._zone_index = zone_index
        self._device_name = controller.get_devices()[device_id].get("name")
        self._attr_name = f"{self._device_name} Zone {zone_index}"
        self._attr_unique_id = f"{device_id}_zone_{zone_index}"

    @property
    def is_on(self) -> bool | None:
        """Return True if zone is on."""
        devices = self._controller.get_devices()
        state = devices[self._device_id].get(f"zone_status_{self._zone_index}")

        # 1 = On, 7 = Spill (but spill shouldn't be here if we filtered correctly,
        # unless it changed state dynamically to spill)
        # If it changes to spill dynamically, it should technically be ON?
        # User said: "Check number of zones... if status is spill... just don't create entity"
        # Implies static check? Or dynamic?
        # "zone_status" updates dynamically.
        # If it becomes spill later, we probably should report it as ON if we already have the entity.
        # But 'spill' implies it's open for safety. So ON is correct.
        return state in [1, 7, 'on', 'spill']

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the zone on."""
        await self._controller.set_zone_status(self._device_id, self._zone_index, 'on')
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the zone off."""
        await self._controller.set_zone_status(self._device_id, self._zone_index, 'off')
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        self._controller.add_update_callback(self.async_update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from updates."""
        self._controller.remove_update_callback(self.async_update_callback)

    async def async_update_callback(self, device_id: str | None = None) -> None:
        """Update the entity's state."""
        if not device_id or self._device_id == device_id:
            self.async_schedule_update_ha_state(True)
