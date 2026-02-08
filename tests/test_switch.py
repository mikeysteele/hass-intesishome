from unittest.mock import MagicMock

from custom_components.intesisaccloud import DOMAIN
from custom_components.intesisaccloud.switch import IntesisZoneSwitch, async_setup_entry


async def test_switch_setup_discovery(hass, mock_controller):
    """Test discovery of zone switches."""
    device_id = "12345"
    device_info = {
        "name": "Test AC",
        "number_of_zones": 3,
        "zone_status_1": 1,      # On
        "zone_status_2": 0,      # Off
        "zone_status_3": 7,      # Spill (should be skipped)
    }

    mock_controller.get_devices.return_value = {device_id: device_info}

    async_add_entities = MagicMock()
    config_entry = MagicMock()
    config_entry.unique_id = "test_entry"

    # Ensure structure exists
    hass.data[DOMAIN] = {"controller": {"test_entry": mock_controller}}

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify we added entities
    assert async_add_entities.call_count == 1
    entities = async_add_entities.call_args[0][0]

    # We expect 2 entities (Zone 1 and Zone 2), Zone 3 is spill
    assert len(entities) == 2
    assert entities[0].unique_id == "12345_zone_1"
    assert entities[1].unique_id == "12345_zone_2"
    assert entities[0].name == "Test AC Zone 1"
    assert entities[1].name == "Test AC Zone 2"

async def test_switch_operations(hass, mock_controller):
    """Test turn on/off operations."""
    device_id = "12345"
    zone_index = 1

    # Mock devices for __init__
    mock_controller.get_devices.return_value = {device_id: {"name": "Test AC"}}

    entity = IntesisZoneSwitch(mock_controller, device_id, zone_index, 1)
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()

    # Test Turn On
    await entity.async_turn_on()
    mock_controller.set_zone_status.assert_called_with(device_id, zone_index, 'on')

    # Test Turn Off
    await entity.async_turn_off()
    mock_controller.set_zone_status.assert_called_with(device_id, zone_index, 'off')

async def test_switch_state(hass, mock_controller):
    """Test switch state reporting."""
    device_id = "12345"
    zone_index = 1

    # Mock devices for __init__
    mock_controller.get_devices.return_value = {device_id: {"name": "Test AC"}}

    entity = IntesisZoneSwitch(mock_controller, device_id, zone_index, 1)

    # Test On (1)
    mock_controller.get_devices.return_value = {device_id: {"zone_status_1": 1}}
    assert entity.is_on is True


    # Test Off (0)
    mock_controller.get_devices.return_value = {device_id: {"zone_status_1": 0}}
    assert entity.is_on is False

    # Test Spill (7) - even if we don't create it, checking logic just in case
    mock_controller.get_devices.return_value = {device_id: {"zone_status_1": 7}}
    assert entity.is_on is True

    # Test 'on' string
    mock_controller.get_devices.return_value = {device_id: {"zone_status_1": "on"}}
    assert entity.is_on is True
