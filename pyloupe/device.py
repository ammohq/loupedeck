from __future__ import annotations
import struct
import asyncio
from typing import Union, Literal, Optional
from PIL import Image

from .constants import (
    BUTTONS,
    COMMANDS,
    DEFAULT_RECONNECT_INTERVAL,
    HAPTIC,
    MAX_BRIGHTNESS,
)
from .eventemitter import EventEmitter
from .util import rgba2rgb565
from .parser import MagicByteLengthParser
from .connections.serial import LoupedeckSerialConnection
from .connections.ws import LoupedeckWSConnection
from .logger import get_logger
from .exceptions import (
    DeviceNotFoundError,
    ConnectionError,
    CommandError,
    ValidationError,
    UnsupportedFeatureError,
)


class LoupedeckDevice(EventEmitter):
    key_size = 90

    # Class logger
    logger = get_logger("device")

    @staticmethod
    def list(ignore_serial: bool = False, ignore_websocket: bool = False):
        LoupedeckDevice.logger.debug("Listing available devices (serial=%s, websocket=%s)", 
                                    not ignore_serial, not ignore_websocket)
        devices = []
        if not ignore_serial:
            serial_devices = LoupedeckSerialConnection.discover()
            LoupedeckDevice.logger.debug("Found %d serial devices", len(serial_devices))
            devices.extend(serial_devices)
        if not ignore_websocket:
            ws_devices = LoupedeckWSConnection.discover()
            LoupedeckDevice.logger.debug("Found %d WebSocket devices", len(ws_devices))
            devices.extend(ws_devices)
        LoupedeckDevice.logger.info("Found %d total devices", len(devices))
        return devices

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point, ensures device is properly closed."""
        self.close()
        return False

    def __init__(
        self,
        host: str | None = None,
        path: str | None = None,
        auto_connect: bool = True,
        reconnect_interval: int | None = DEFAULT_RECONNECT_INTERVAL,
    ):
        super().__init__()
        self.logger.debug("Initializing LoupedeckDevice (host=%s, path=%s, auto_connect=%s, reconnect_interval=%s)",
                         host, path, auto_connect, reconnect_interval)

        self.host = host
        self.path = path
        self.reconnect_interval = reconnect_interval
        self.transaction_id = 0
        self.connection = None
        self.pending_transactions: dict[int, callable] = {}
        self._reconnect_task = None
        self._should_reconnect = reconnect_interval is not None

        # Custom button mapping dictionary
        self.button_mapping = {}

        # Initialize event handler references
        self._connect_handler = None
        self._message_handler = None
        self._disconnect_handler = None

        self.handlers = {
            COMMANDS["BUTTON_PRESS"]: self.on_button,
            COMMANDS["KNOB_ROTATE"]: self.on_rotate,
        }

        if auto_connect:
            self.logger.info("Auto-connecting to device")
            try:
                self.connect()
            except Exception as e:
                self.logger.error("Failed to auto-connect: %s", str(e))
                pass

    def _handle_disconnect(self, data):
        """Handle disconnect event and attempt reconnection if enabled."""
        self.logger.info("Device disconnected")
        self.emit("disconnect", data)
        if self._should_reconnect and self.reconnect_interval:
            self.logger.info("Scheduling reconnection attempt")
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt."""
        if self._reconnect_task is not None:
            self.logger.debug("Reconnection already scheduled, skipping")
            return

        async def reconnect_task():
            self.logger.debug("Waiting %d ms before reconnection attempt", self.reconnect_interval)
            await asyncio.sleep(self.reconnect_interval / 1000)
            self._reconnect_task = None
            try:
                self.logger.info("Attempting to reconnect")
                self.connect()
                self.logger.info("Reconnection successful")
                self.emit("reconnect", None)
            except Exception as e:
                self.logger.error("Reconnection failed: %s", str(e))
                self.emit("reconnect_error", {"error": str(e)})
                self._schedule_reconnect()

        self.logger.info("Scheduling reconnection attempt")
        self.emit("reconnect_attempt", None)
        loop = asyncio.get_event_loop()
        self._reconnect_task = loop.create_task(reconnect_task())

    def connect(self):
        self.logger.info("Connecting to device")

        if self.path:
            self.logger.debug("Using serial connection with path: %s", self.path)
            self.connection = LoupedeckSerialConnection(self.path)
        elif self.host:
            self.logger.debug("Using WebSocket connection with host: %s", self.host)
            self.connection = LoupedeckWSConnection(self.host)
        else:
            self.logger.debug("No path or host specified, discovering devices")
            devices = self.list()
            if not devices:
                self.logger.error("No devices found")
                raise DeviceNotFoundError("No devices found during auto-discovery")
            device = devices[0]
            conn_type = device["connectionType"]
            args = {k: v for k, v in device.items() if k != "connectionType"}
            self.logger.info("Using discovered device: %s", args)
            self.connection = conn_type(**args)

        if hasattr(self.connection, "connect"):
            self.logger.debug("Establishing connection")
            if asyncio.iscoroutinefunction(self.connection.connect):
                self.logger.debug("Using asyncio for connection")
                asyncio.get_event_loop().run_until_complete(self.connection.connect())
            else:
                self.connection.connect()

        # Store event handler references for later cleanup
        self._connect_handler = lambda data: self.emit("connect", data)
        self._message_handler = self.on_receive
        self._disconnect_handler = self._handle_disconnect

        # Attach event handlers
        self.logger.debug("Setting up event handlers")
        self.connection.on("connect", self._connect_handler)
        self.connection.on("message", self._message_handler)
        self.connection.on("disconnect", self._disconnect_handler)

        self.logger.info("Connection established")
        return self

    def close(self):
        self.logger.info("Closing device connection")

        # Cancel any pending reconnection task
        if self._reconnect_task is not None:
            self.logger.debug("Cancelling pending reconnection task")
            self._reconnect_task.cancel()
            self._reconnect_task = None

        # Disable automatic reconnection
        self._should_reconnect = False
        self.logger.debug("Disabled automatic reconnection")

        if self.connection:
            # Remove event listeners to prevent memory leaks
            self.logger.debug("Removing event listeners")
            if hasattr(self, "_connect_handler"):
                self.connection.off("connect", self._connect_handler)
            if hasattr(self, "_message_handler"):
                self.connection.off("message", self._message_handler)
            if hasattr(self, "_disconnect_handler"):
                self.connection.off("disconnect", self._disconnect_handler)

            # Close the connection
            if hasattr(self.connection, "close"):
                self.logger.debug("Closing connection")
                if asyncio.iscoroutinefunction(self.connection.close):
                    self.logger.debug("Using asyncio for closing connection")
                    asyncio.get_event_loop().run_until_complete(self.connection.close())
                else:
                    self.connection.close()

            # Clear connection reference
            self.connection = None
            self.logger.info("Connection closed and reference cleared")

    # Simplified drawing and command helpers
    def send(self, command: int, data: bytes = b""):
        if not self.connection or not self.connection.is_ready():
            self.logger.warning("Cannot send command: connection not ready")
            raise CommandError("Cannot send command: device connection is not ready")

        self.transaction_id = (self.transaction_id + 1) % 256 or 1
        header = struct.pack(
            "BBB", min(3 + len(data), 0xFF), command, self.transaction_id
        )
        packet = header + data

        self.logger.debug("Sending command: %d, transaction ID: %d, data length: %d", 
                         command, self.transaction_id, len(data))

        if hasattr(self.connection, "send"):
            if asyncio.iscoroutinefunction(self.connection.send):
                self.logger.debug("Using asyncio for sending data")
                asyncio.get_event_loop().run_until_complete(
                    self.connection.send(packet)
                )
            else:
                self.connection.send(packet)

        self.logger.debug("Command sent successfully")
        return self.transaction_id

    def set_brightness(self, value: float):
        byte = max(0, min(MAX_BRIGHTNESS, round(value * MAX_BRIGHTNESS)))
        self.send(COMMANDS["SET_BRIGHTNESS"], bytes([byte]))

    def set_button_mapping(self, hw_button_id: int, custom_id: str | int):
        """Set a custom mapping for a button.

        Args:
            hw_button_id (int): The hardware button ID (in decimal or hex)
            custom_id (str | int): The custom ID to map the button to
        """
        self.button_mapping[hw_button_id] = custom_id

    def get_button_mapping(self, hw_button_id: int) -> str | int | None:
        """Get the current mapping for a button.

        Args:
            hw_button_id (int): The hardware button ID (in decimal or hex)

        Returns:
            str | int | None: The current mapping for the button, or None if not mapped
        """
        if hw_button_id in self.button_mapping:
            return self.button_mapping[hw_button_id]
        return BUTTONS.get(hw_button_id)

    def reset_button_mapping(self, hw_button_id: int = None):
        """Reset button mappings.

        Args:
            hw_button_id (int, optional): The hardware button ID to reset.
                                         If None, all mappings are reset.
        """
        if hw_button_id is None:
            self.button_mapping = {}
        elif hw_button_id in self.button_mapping:
            del self.button_mapping[hw_button_id]

    def set_button_color(self, id: str, color: str):
        key = next((k for k, v in BUTTONS.items() if v == id), None)
        if key is None:
            self.logger.error("Invalid button ID: %s", id)
            raise ValidationError(f"Invalid button ID: {id}")
        from .color import parse_color

        r, g, b, _ = parse_color(color)
        self.send(COMMANDS["SET_COLOR"], bytes([key, r, g, b]))

    def display_image(
        self, image: Image.Image, screen: str = "center", x: int = 0, y: int = 0
    ):
        """Display an image on the device screen.

        Args:
            image (PIL.Image.Image): The image to display
            screen (str): The target screen ('center', 'left', 'right', 'knob')
            x (int): The x-coordinate offset
            y (int): The y-coordinate offset

        Raises:
            ValidationError: If the screen is invalid or the image is incompatible
        """
        if not hasattr(self, "displays") or screen not in self.displays:
            self.logger.error("Invalid screen: %s", screen)
            raise ValidationError(f"Invalid screen: {screen}")

        # Get screen dimensions
        screen_info = self.displays[screen]
        screen_width = screen_info["width"]
        screen_height = screen_info["height"]

        # Ensure image is in RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Resize image if it doesn't match the screen dimensions
        if image.width != screen_width or image.height != screen_height:
            image = image.resize((screen_width, screen_height))

        # Convert image to RGBA bytes
        rgba_data = bytearray()
        pixels = image.load()
        for y_pos in range(image.height):
            for x_pos in range(image.width):
                r, g, b = pixels[x_pos, y_pos]
                rgba_data.extend([r, g, b, 255])  # Add alpha channel

        # Convert RGBA to RGB565
        rgb565_data = rgba2rgb565(rgba_data, image.width * image.height)

        # Prepare the frame buffer command
        screen_id = screen_info["id"]

        # Create header with screen ID, x, y, width, height
        header = bytearray()
        header.extend(screen_id)
        header.extend(struct.pack("<HH", x, y))
        header.extend(struct.pack("<HH", image.width, image.height))

        # Send the frame buffer command with the image data
        self.send(COMMANDS["FRAMEBUFF"], header + rgb565_data)

        return True

    def update_firmware(self, firmware_path: str, chunk_size: int = 4096):
        """Update device firmware from a binary file.

        The firmware is sent in chunks using the ``FIRMWARE_UPDATE`` command.

        Args:
            firmware_path: Path to the firmware binary file.
            chunk_size: Size of each data chunk to send.
        """
        self.logger.info("Updating firmware using %s", firmware_path)

        with open(firmware_path, "rb") as fw:
            offset = 0
            chunk = fw.read(chunk_size)
            while chunk:
                header = struct.pack("<I", offset)
                self.send(COMMANDS["FIRMWARE_UPDATE"], header + chunk)
                offset += len(chunk)
                chunk = fw.read(chunk_size)

        self.logger.info("Firmware update data sent")

    # Event handlers
    def on_button(self, data: bytes):
        if len(data) < 2:
            return
        # Get the hardware button ID
        hw_button_id = data[0]
        # Check if there's a custom mapping for this button
        if hw_button_id in self.button_mapping:
            button_id = self.button_mapping[hw_button_id]
        else:
            button_id = BUTTONS.get(hw_button_id)
        event = "down" if data[1] == 0x00 else "up"
        self.emit(event, {"id": button_id})

    def on_rotate(self, data: bytes):
        if len(data) < 2:
            return
        knob = BUTTONS.get(data[0])
        delta = struct.unpack("b", data[1:2])[0]
        self.emit("rotate", {"id": knob, "delta": delta})

    def on_receive(self, data: bytes):
        if not data:
            return
        msg_length = data[0]
        cmd = data[1]
        transaction = data[2]
        payload = data[3:msg_length]
        handler = self.handlers.get(cmd)
        if handler:
            handler(payload)
        resolver = self.pending_transactions.pop(transaction, None)
        if resolver:
            resolver(payload)


class LoupedeckLive(LoupedeckDevice):
    productId = 0x0004
    vendorId = 0x2EC2
    buttons = list(range(8))
    knobs = ["knobCL", "knobCR", "knobTL", "knobTR", "knobBL", "knobBR"]
    columns = 4
    rows = 3
    type = "Loupedeck Live"
    visibleX = (0, 480)
    displays = {
        "center": {"id": b"\x00M", "width": 360, "height": 270, "offset": (60, 0)},
        "left": {"id": b"\x00M", "width": 60, "height": 270},
        "right": {"id": b"\x00M", "width": 60, "height": 270, "offset": (420, 0)},
    }

    def get_target(self, x, y, _id=None):
        if x < self.displays["left"]["width"]:
            return {"screen": "left"}
        if x >= self.displays["left"]["width"] + self.displays["center"]["width"]:
            return {"screen": "right"}
        column = int((x - self.displays["left"]["width"]) / self.key_size)
        row = int(y / self.key_size)
        key = row * self.columns + column
        return {"screen": "center", "key": key}


class LoupedeckCT(LoupedeckLive):
    productId = 0x0003
    buttons = [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        "home",
        "enter",
        "undo",
        "save",
        "keyboard",
        "fnL",
        "a",
        "b",
        "c",
        "d",
        "fnR",
        "e",
    ]
    displays = {
        "center": {"id": b"\x00A", "width": 360, "height": 270},
        "left": {"id": b"\x00L", "width": 60, "height": 270},
        "right": {"id": b"\x00R", "width": 60, "height": 270},
        "knob": {"id": b"\x00W", "width": 240, "height": 240, "endianness": "be"},
    }
    type = "Loupedeck CT"

    def get_target(self, x, y, id=None):
        if id == 0:
            return {"screen": "knob"}
        return super().get_target(x, y)


class LoupedeckLiveS(LoupedeckDevice):
    productId = 0x0006
    vendorId = 0x2EC2
    buttons = [0, 1, 2, 3]
    knobs = ["knobCL", "knobTL"]
    columns = 5
    rows = 3
    type = "Loupedeck Live S"
    visibleX = (15, 465)
    displays = {
        "center": {"id": b"\x00M", "width": 480, "height": 270},
    }

    def get_target(self, x, y, _id=None):
        if x < self.visibleX[0] or x >= self.visibleX[1]:
            return {}
        column = int((x - self.visibleX[0]) / self.key_size)
        row = int(y / self.key_size)
        key = row * self.columns + column
        return {"screen": "center", "key": key}


class RazerStreamController(LoupedeckLive):
    productId = 0x0D06
    vendorId = 0x1532
    type = "Razer Stream Controller"


class RazerStreamControllerX(LoupedeckDevice):
    productId = 0x0D09
    vendorId = 0x1532
    type = "Razer Stream Controller X"
    buttons = []
    columns = 5
    rows = 3
    visibleX = (0, 480)
    key_size = 96
    displays = {
        "center": {"id": b"\x00M", "width": 480, "height": 288},
    }

    def on_button(self, data: bytes):
        super().on_button(data)
        event = "touchstart" if data[1] == 0x00 else "touchend"
        key = BUTTONS.get(data[0])
        row = key // self.columns
        col = key % self.columns
        touch = {
            "id": 0,
            "x": (col + 0.5) * self.key_size,
            "y": (row + 0.5) * self.key_size,
            "target": {"key": key},
        }
        self.emit(
            event,
            {
                "touches": [touch] if event == "touchstart" else [],
                "changedTouches": [touch],
            },
        )

    def set_button_color(self, *args, **kwargs):
        raise UnsupportedFeatureError("Setting key color", self.type)

    def vibrate(self, *args, **kwargs):
        raise UnsupportedFeatureError("Vibration", self.type)
