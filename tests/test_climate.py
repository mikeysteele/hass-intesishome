from unittest.mock import MagicMock

from homeassistant.components.climate import (
    SWING_HORIZONTAL,
    SWING_VERTICAL,
    HVACMode,
)

from custom_components.intesisaccloud.climate import IntesisAC


async def test_climate_entity_creation(hass, mock_controller):
    """Test successful creation of IntesisAC entity."""
    device_id = "12345"
    device_info = {
        "name": "Test AC",
        "widgets": [1, 2],  # Mock widgets
    }

    # Mock controller methods used in __init__
    mock_controller.get_devices.return_value = {device_id: device_info}
    mock_controller.device_type = "IntesisHome"
    mock_controller.has_setpoint_control.return_value = True
    mock_controller.has_vertical_swing.return_value = True
    mock_controller.has_horizontal_swing.return_value = True
    mock_controller.get_fan_speed_list.return_value = ["low", "high"]
    mock_controller.get_mode_list.return_value = ["auto", "cool", "heat", "dry", "fan", "off"]

    entity = IntesisAC(device_id, device_info, mock_controller)

    assert entity.name == "Test AC"
    assert entity.unique_id == device_id
    mock_controller.is_available = False
    assert entity.available is False
    mock_controller.is_available = True
    assert entity.available is True


async def test_climate_update(hass, mock_controller):
    """Test entity update from controller."""
    device_id = "12345"
    device_info = {"name": "Test AC"}

    mock_controller.device_type = "IntesisHome"
    mock_controller.has_setpoint_control.return_value = True
    mock_controller.has_vertical_swing.return_value = False
    mock_controller.has_horizontal_swing.return_value = False
    mock_controller.get_fan_speed_list.return_value = ["auto"]
    mock_controller.get_mode_list.return_value = ["cool"]

    entity = IntesisAC(device_id, device_info, mock_controller)

    # Mock return values for async_update
    mock_controller.is_connected = True
    mock_controller.get_temperature.return_value = 22.0
    mock_controller.get_fan_speed.return_value = "auto"
    mock_controller.is_on.return_value = True
    mock_controller.get_min_setpoint.return_value = 18
    mock_controller.get_max_setpoint.return_value = 30
    mock_controller.get_rssi.return_value = 10
    mock_controller.get_run_hours.return_value = 100
    mock_controller.get_setpoint.return_value = 24.0
    mock_controller.get_outdoor_temperature.return_value = 30.0
    mock_controller.get_mode.return_value = "cool"
    mock_controller.get_preset_mode.return_value = "eco"
    mock_controller.get_vertical_swing.return_value = "auto/stop"
    mock_controller.get_horizontal_swing.return_value = "auto/stop"
    mock_controller.get_heat_power_consumption.return_value = 0
    mock_controller.get_cool_power_consumption.return_value = 1000

    await entity.async_update()

    assert entity.available is True
    assert entity.current_temperature == 22.0
    assert entity.target_temperature == 24.0
    assert entity.hvac_mode == HVACMode.COOL


async def test_climate_optimistic_operations(hass, mock_controller):
    """Test that operations update state optimistically immediately."""
    device_id = "12345"
    device_info = {"name": "Test AC", "climate_working_mode": True}

    mock_controller.device_type = "IntesisHome"
    mock_controller.has_setpoint_control.return_value = True
    mock_controller.has_vertical_swing.return_value = True
    mock_controller.has_horizontal_swing.return_value = True
    mock_controller.get_fan_speed_list.return_value = ["auto", "low", "high"]
    mock_controller.get_mode_list.return_value = ["cool", "heat", "auto"]
    mock_controller.is_on.return_value = True

    entity = IntesisAC(device_id, device_info, mock_controller)
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()

    # Test Turn On
    await entity.async_turn_on()
    assert entity._power is True
    mock_controller.set_power_on.assert_called_with(device_id)

    # Set Mode
    await entity.async_set_hvac_mode(HVACMode.COOL)
    assert entity.hvac_mode == HVACMode.COOL

    # Test Fan Mode
    await entity.async_set_fan_mode("high")
    assert entity.fan_mode == "high"
    mock_controller.set_fan_speed.assert_called_with(device_id, "high")

    # Test Temperature
    await entity.async_set_temperature(temperature=21.0)
    assert entity.target_temperature == 21.0
    mock_controller.set_temperature.assert_called_with(device_id, 21.0)

    # Test Preset Mode
    await entity.async_set_preset_mode("eco")
    assert entity.preset_mode == "eco"
    mock_controller.set_preset_mode.assert_called_with(device_id, "eco")

    # Test Swing Mode
    await entity.async_set_swing_mode(SWING_VERTICAL)
    assert entity.swing_mode == SWING_VERTICAL
    mock_controller.set_vertical_vane.assert_called_with(device_id, "swing")

    # Test Horizontal Swing Mode
    await entity.async_set_swing_horizontal_mode(SWING_HORIZONTAL)
    assert entity.swing_horizontal_mode == SWING_HORIZONTAL
    mock_controller.set_horizontal_vane.assert_called_with(device_id, "swing")
