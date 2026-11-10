"""Support for IntesisACCloud Zone Fans."""
from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyintesishome import IntesisBase

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IntesisACCloud zone fan entities."""
    controller = hass.data[DOMAIN]["controller"][config_entry.unique_id]
    ih_devices = controller.get_devices()
    _LOGGER.debug("Found %s devices", len(ih_devices))
    entities = []

    for ih_device_id, device in ih_devices.items():
        # Zone Discovery
        number_of_zones = device.get("number_of_zones", 0)

        if number_of_zones > 0:
            _LOGGER.debug(
                "Device %s has %s zones. Discovering...", ih_device_id, number_of_zones
            )
        else:
            _LOGGER.debug(
                "Device %s reports 0 zones. Full device data: %s", ih_device_id, device
            )

        zone_friendly_index = 1
        for zone_index in range(1, number_of_zones + 1):
            # Check initial status
            zone_status = device.get(f"zone_status_{zone_index}")

            _LOGGER.debug("Zone %s status: %s", zone_index, zone_status)

            # Filter out spill zones (7)
            if zone_status == 7 or zone_status == 'spill':
                _LOGGER.debug("Skipping spill zone %s for device %s", zone_index, ih_device_id)
                continue

            # Add entity for valid zone
            entities.append(IntesisZoneFan(controller, ih_device_id, zone_index, zone_friendly_index))
            zone_friendly_index += 1

    if entities:
        async_add_entities(entities)


class IntesisZoneFan(FanEntity):
    """Representation of an IntesisACCloud Zone Fan."""

    def __init__(self, manager, device_id: str, zone_index: int, zone_friendly_index: int) -> None:
        """Initialize the fan."""
        self._manager = manager
        self._controller: IntesisBase = manager.controller
        self._device_id = device_id
        self._zone_index = zone_index
        self._zone_friendly_index = zone_friendly_index
        device_name = self._controller.get_devices()[device_id].get("name")
        self._device_name = str(device_name) if device_name is not None else "Intesis AC"
        self._attr_name = f"{self._device_name} Zone {zone_friendly_index}"
        self._attr_unique_id = f"{device_id}_zone_{zone_index}"
        self._attr_supported_features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        self._is_on: bool | None = None
        self._is_on_time: float | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer="Intesis",
            model=self._controller.get_devices()[self._device_id].get("model"),
        )

    @property
    def available(self) -> bool:
        """Return True while the controller is delivering state."""
        return bool(self._controller.is_available)

    @property
    def is_on(self) -> bool | None:
        """Return True if zone is on."""
        devices = self._controller.get_devices()
        if self._device_id not in devices:
            return self._is_on

        state = devices[self._device_id].get(f"zone_status_{self._zone_index}")
        current_state = state in [1, 7, 'on', 'spill'] if state is not None else None

        if self._is_on is not None:
            if current_state is not None and current_state == self._is_on:
                # Controller has caught up with user's action
                self._is_on = None
                self._is_on_time = None
            elif self._is_on_time and (time.monotonic() - self._is_on_time < 90):
                # Still within optimistic window waiting for cloud/hardware confirmation
                return self._is_on
            else:
                # Optimistic window expired; revert to controller state
                self._is_on = None
                self._is_on_time = None

        return current_state

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        """Turn the zone on."""
        self._is_on = True
        self._is_on_time = time.monotonic()
        self.async_write_ha_state()
        await self._controller.set_zone_status(self._device_id, self._zone_index, 'on')

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the zone off."""
        self._is_on = False
        self._is_on_time = time.monotonic()
        self.async_write_ha_state()
        await self._controller.set_zone_status(self._device_id, self._zone_index, 'off')

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        self._manager.add_update_callback(self.async_update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from updates."""
        self._manager.remove_update_callback(self.async_update_callback)

    async def async_update_callback(self, device_id: str | None = None) -> None:
        """Update the entity's state."""
        if not device_id or self._device_id == device_id:
            self.async_schedule_update_ha_state(True)
