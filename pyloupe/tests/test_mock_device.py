"""
Tests for the LoupedeckDevice class using mock connections.

This module tests the LoupedeckDevice class using mock connections
to simulate device behavior without requiring physical devices.
"""

import pytest
import struct
from unittest.mock import patch

from pyloupe.device import LoupedeckDevice
from pyloupe.constants import COMMANDS, BUTTONS
from .mocks import MockWSConnection, MockSerialConnection


@pytest.fixture
def mock_ws_device():
    """Fixture that provides a LoupedeckDevice with a mock WebSocket connection."""
    with patch('pyloupe.device.LoupedeckWSConnection', MockWSConnection):
        with patch('pyloupe.device.LoupedeckDevice.list', return_value=[
            {"connectionType": MockWSConnection, "host": "mock-host"}
        ]):
            device = LoupedeckDevice(auto_connect=True)
            yield device
            device.close()


@pytest.fixture
def mock_serial_device():
    """Fixture that provides a LoupedeckDevice with a mock Serial connection."""
    with patch('pyloupe.device.LoupedeckSerialConnection', MockSerialConnection):
        with patch('pyloupe.device.LoupedeckDevice.list', return_value=[
            {"connectionType": MockSerialConnection, "path": "mock-path"}
        ]):
            device = LoupedeckDevice(auto_connect=True)
            yield device
            device.close()


def test_device_connection_ws(mock_ws_device):
    """Test that a device can connect using a mock WebSocket connection."""
    assert mock_ws_device.connection is not None
    assert mock_ws_device.connection.is_ready()
    assert isinstance(mock_ws_device.connection, MockWSConnection)


def test_device_connection_serial(mock_serial_device):
    """Test that a device can connect using a mock Serial connection."""
    assert mock_serial_device.connection is not None
    assert mock_serial_device.connection.is_ready()
    assert isinstance(mock_serial_device.connection, MockSerialConnection)


def test_device_send_command(mock_ws_device):
    """Test that a device can send commands using a mock connection."""
    # Send a command
    command = COMMANDS["SET_BRIGHTNESS"]
    data = bytes([100])  # 100/255 brightness
    mock_ws_device.send(command, data)

    # Check that the command was sent
    assert len(mock_ws_device.connection.sent_data) == 1
    sent_data = mock_ws_device.connection.sent_data[0]

    # The sent data should be a header (3 bytes) followed by the data
    assert len(sent_data) == 3 + len(data)
    assert sent_data[1] == command  # Command byte
    assert sent_data[3:] == data    # Command data


def test_device_receive_button_event(mock_ws_device):
    """Test that a device can receive button events using a mock connection."""
    # Set up an event handler
    button_events = []
    def on_button_down(data):
        button_events.append(data)

    mock_ws_device.on("down", on_button_down)

    # Simulate receiving a button down event
    button_id = 0  # First button
    button_data = bytes([button_id, 0x00])  # 0x00 = down

    # Create a message with the button press command
    msg_length = 3 + len(button_data)
    transaction_id = 1
    message = bytes([msg_length, COMMANDS["BUTTON_PRESS"], transaction_id]) + button_data

    # Simulate receiving the message
    mock_ws_device.connection.receive_data(message)

    # Check that the event was processed
    assert len(button_events) == 1
    assert button_events[0]["id"] == BUTTONS.get(button_id)


def test_device_receive_knob_event(mock_ws_device):
    """Test that a device can receive knob events using a mock connection."""
    # Set up an event handler
    knob_events = []
    def on_knob_rotate(data):
        knob_events.append(data)

    mock_ws_device.on("rotate", on_knob_rotate)

    # Simulate receiving a knob rotation event
    knob_id = 8  # First knob (depends on the device model)
    delta = 1    # Clockwise rotation
    knob_data = bytes([knob_id, delta])

    # Create a message with the knob rotate command
    msg_length = 3 + len(knob_data)
    transaction_id = 1
    message = bytes([msg_length, COMMANDS["KNOB_ROTATE"], transaction_id]) + knob_data

    # Simulate receiving the message
    mock_ws_device.connection.receive_data(message)

    # Check that the event was processed
    assert len(knob_events) == 1
    assert knob_events[0]["id"] == BUTTONS.get(knob_id)
    assert knob_events[0]["delta"] == delta


def test_device_button_mapping(mock_ws_device):
    """Test that button mapping works correctly."""
    # Set up an event handler
    button_events = []
    def on_button_down(data):
        button_events.append(data)

    mock_ws_device.on("down", on_button_down)

    # Set a custom button mapping
    hw_button_id = 0
    custom_id = "custom_button"
    mock_ws_device.set_button_mapping(hw_button_id, custom_id)

    # Simulate receiving a button down event for the mapped button
    button_data = bytes([hw_button_id, 0x00])  # 0x00 = down

    # Create a message with the button press command
    msg_length = 3 + len(button_data)
    transaction_id = 1
    message = bytes([msg_length, COMMANDS["BUTTON_PRESS"], transaction_id]) + button_data

    # Simulate receiving the message
    mock_ws_device.connection.receive_data(message)

    # Check that the event was processed with the custom ID
    assert len(button_events) == 1
    assert button_events[0]["id"] == custom_id


def test_device_set_button_color(mock_ws_device):
    """Test that setting button colors works correctly."""
    # Set a button color
    button_id = "knobTL"  # Top-left knob
    color = "#FF0000"     # Red

    mock_ws_device.set_button_color(button_id, color)

    # Check that the command was sent
    assert len(mock_ws_device.connection.sent_data) == 1
    sent_data = mock_ws_device.connection.sent_data[0]

    # The sent data should be a header (3 bytes) followed by the button ID and RGB values
    assert len(sent_data) == 3 + 4  # 3 bytes header + 1 byte button ID + 3 bytes RGB
    assert sent_data[1] == COMMANDS["SET_COLOR"]  # Command byte

    # Find the hardware button ID for the given button ID
    hw_button_id = next((k for k, v in BUTTONS.items() if v == button_id), None)
    assert sent_data[3] == hw_button_id  # Button ID
    assert sent_data[4:7] == bytes([255, 0, 0])  # RGB values for red
