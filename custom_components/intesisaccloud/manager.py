import logging

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
        """Return if the controller is delivering state.

        Mirrors the controller's is_available rather than its is_connected,
        which since pyintesishome 2.3 only reports the on-demand command
        socket and is False most of the time.
        """
        return self._connected and self.controller.is_available

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
        # pyintesishome >= 2.3 keeps state flowing over HTTPS polling and
        # opens the command socket on demand, so there is no connection to
        # babysit here. Availability transitions are logged by following
        # is_available, which only goes False once state stops arriving.
        available = self.controller.is_available
        if self._connected and not available:
            _LOGGER.info("No longer receiving state from the %s API", self.device_type)
        elif available and not self._connected:
            _LOGGER.debug("Receiving state from the %s API again", self.device_type)
        self._connected = available

        # Propagate update to listeners
        for callback in self._update_callbacks:
            await callback(device_id)
