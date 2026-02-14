from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from custom_components.intesisaccloud.manager import IntesisManager

@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.connect = AsyncMock()
    controller.stop = AsyncMock()
    controller.get_devices.return_value = {}
    controller.is_connected = False
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

async def test_manager_reconnection_logic(hass, mock_controller, config_entry):
    """Test reconnection logic when connection is lost."""
    manager = IntesisManager(hass, mock_controller, config_entry, "IntesisHome")
    manager._connected = True
    mock_controller.is_connected = False # Simulate disconnection
    
    # Patch top-level imports in manager.py
    with patch("custom_components.intesisaccloud.manager.async_call_later") as mock_call_later, \
         patch("custom_components.intesisaccloud.manager.random.randrange", return_value=10):
        
        await manager.async_update_callback()
        
        assert not manager.is_connected
        # Verify reconnection scheduled
        mock_call_later.assert_called() 
        
        # Extract the scheduled retry function
        args, _ = mock_call_later.call_args
        delay = args[1]
        retry_func = args[2]
        
        assert delay == 10 # randrange value
        
        # Now fail the first retry
        from pyintesishome import IHConnectionError
        mock_controller.connect.side_effect = IHConnectionError("Fail")

        await retry_func
        
        # Should verify it scheduled another retry
        mock_controller.connect.assert_awaited()
        
        # Cleanup: close the recursive coroutine to avoid RuntimeWarning
        args2, _ = mock_call_later.call_args
        coro = args2[2]
        coro.close()
