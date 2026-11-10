from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.intesisaccloud.manager import IntesisManager


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.connect = AsyncMock()
    controller.stop = AsyncMock()
    controller.get_devices.return_value = {}
    controller.is_connected = False
    controller.is_available = True
    return controller

async def test_manager_initialization(hass, mock_controller, config_entry):
    """Test manager initialization."""
    manager = IntesisManager(hass, mock_controller, config_entry, "IntesisHome")
    assert manager.hass == hass
    assert manager.controller == mock_controller
    assert manager.config_entry == config_entry
    assert manager.device_type == "IntesisHome"
    assert not manager.is_connected

async def test_manager_connect(hass, mock_controller, config_entry):
    """Test async_connect."""
    manager = IntesisManager(hass, mock_controller, config_entry, "IntesisHome")
    await manager.async_connect()

    mock_controller.connect.assert_awaited_once()
    assert manager.is_connected
    mock_controller.add_update_callback.assert_called_once_with(manager.async_update_callback)

async def test_manager_stop(hass, mock_controller, config_entry):
    """Test stop."""
    manager = IntesisManager(hass, mock_controller, config_entry, "IntesisHome")
    await manager.stop()

    # Check that remove_update_callback is called on the controller (manager delegates)
    mock_controller.remove_update_callback.assert_called_once_with(manager.async_update_callback)
    mock_controller.stop.assert_awaited_once()

async def test_manager_callbacks(hass, mock_controller, config_entry):
    """Test add/remove update callbacks."""
    manager = IntesisManager(hass, mock_controller, config_entry, "IntesisHome")
    mock_callback = AsyncMock()

    manager.add_update_callback(mock_callback)
    assert mock_callback in manager._update_callbacks

    # Test callback propagation
    await manager.async_update_callback("123")
    mock_callback.assert_awaited_with("123")

    manager.remove_update_callback(mock_callback)
    assert mock_callback not in manager._update_callbacks

async def test_manager_tracks_availability_without_reconnecting(
    hass, mock_controller, config_entry
):
    """Availability follows is_available; the library owns connectivity."""
    manager = IntesisManager(hass, mock_controller, config_entry, "IntesisHome")
    await manager.async_connect()
    mock_controller.connect.reset_mock()

    # The command socket being closed is normal and must not matter.
    mock_controller.is_connected = False
    await manager.async_update_callback()
    assert manager.is_connected

    mock_controller.is_available = False
    await manager.async_update_callback()
    assert not manager.is_connected

    mock_controller.is_available = True
    await manager.async_update_callback()
    assert manager.is_connected

    mock_controller.connect.assert_not_awaited()
