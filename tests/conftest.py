from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.intesisaccloud import DOMAIN


@pytest.fixture
def hass():
    """Mock Home Assistant object."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.loop = MagicMock()
    return hass

@pytest.fixture
def config_entry():
    """Mock ConfigEntry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {
        "host": "1.2.3.4",
        "username": "user",
        "password": "password",
        "device": "IntesisHome"
    }
    entry.entry_id = "test_entry_id"
    entry.unique_id = "test_unique_id"
    return entry

@pytest.fixture
def mock_controller():
    """Mock pyIntesisHome controller."""
    controller = MagicMock()
    controller.get_devices.return_value = {}
    controller.is_connected = True
    controller.connect = AsyncMock()
    controller.stop = AsyncMock()
    controller.poll_status = AsyncMock()
    controller.set_zone_status = AsyncMock()
    return controller
