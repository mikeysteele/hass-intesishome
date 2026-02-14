import logging
import random
from homeassistant.helpers.event import async_call_later
from pyintesishome import IHConnectionError

_LOGGER = logging.getLogger(__name__)

class IntesisManager:
    """Manages the connection to the IntesisHome/Airconwithme API."""

    def __init__(self, hass, controller, config_entry, device_type):
        """Initialize the manager."""
        self.hass = hass
        self.controller = controller
        self.config_entry = config_entry
        self.device_type = device_type
        self._connected = False
        self._update_callbacks = []
        from pyintesishome.const import (
            DEVICE_INTESISHOME,
            DEVICE_ANYWAIR,
            DEVICE_AIRCONWITHME,
        )
        self.cloud_devices = [DEVICE_INTESISHOME, DEVICE_ANYWAIR, DEVICE_AIRCONWITHME]

    def __getattr__(self, name):
        """Delegate undefined attributes to the controller."""
        return getattr(self.controller, name)

    async def async_connect(self):
        """Connect to the controller."""
        _LOGGER.debug("Connecting to controller...")
        await self.controller.connect()
        self._connected = True
        self.controller.add_update_callback(self.async_update_callback)
        _LOGGER.debug("Connection successful. Devices: %s", self.controller.get_devices())

    async def stop(self):
        """Stop the controller."""
        self.controller.remove_update_callback(self.async_update_callback)
        await self.controller.stop()

    @property
    def is_connected(self):
        """Return if connected."""
        return self._connected

    def get_devices(self):
        """Get devices from controller."""
        return self.controller.get_devices()
    
    def get_device(self, device_id):
        """Get a specific device."""
        return self.controller.get_device(device_id)

    def add_update_callback(self, method):
        """Add callback."""
        if method not in self._update_callbacks:
            self._update_callbacks.append(method)

    def remove_update_callback(self, method):
        """Remove callback."""
        if method in self._update_callbacks:
            self._update_callbacks.remove(method)

    async def async_update_callback(self, device_id=None):
        """Handle updates from the controller."""
        # Propagate update to listeners
        for callback in self._update_callbacks:
            await callback(device_id)

        # Track changes in connection state
        if self.controller and not self.controller.is_connected and self._connected:
            # Connection has dropped
            self._connected = False
            reconnect_seconds = 30
            if self.device_type in self.cloud_devices:
                # Add a random delay for cloud connections
                reconnect_seconds = random.randrange(10, 30)

            _LOGGER.info(
                "Connection to %s API was lost. Reconnecting in %i seconds",
                self.device_type,
                reconnect_seconds,
            )

            async def try_connect(retries):
                MAX_WAIT_TIME = 300
                try:
                    await self.controller.connect()
                    self._connected = True
                    _LOGGER.info("Reconnected to %s API", self.device_type)
                    # Notify listeners of reconnection
                    for callback in self._update_callbacks:
                        await callback()
                except IHConnectionError:
                    wait_time = min(2**retries, MAX_WAIT_TIME)
                    _LOGGER.info(
                        "Failed to reconnect to %s API. Retrying in %i seconds",
                        self.device_type,
                        wait_time,
                    )
                    async_call_later(self.hass, wait_time, try_connect(retries + 1))

            async_call_later(self.hass, reconnect_seconds, try_connect(0))

        if self.controller.is_connected and not self._connected:
             self._connected = True
             _LOGGER.debug("Connection to %s API was restored", self.device_type)
