import serial
from serial.tools import list_ports
from ..parser import MagicByteLengthParser
from . import Connection

WS_UPGRADE_HEADER = b"GET /index.html\r\nHTTP/1.1\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Key: 123abc\r\n\r\n"
WS_UPGRADE_RESPONSE = b"HTTP/1.1"
WS_CLOSE_FRAME = bytes([0x88, 0x80, 0x00, 0x00, 0x00, 0x00])

VENDOR_IDS = [0x2EC2, 0x1532]
MANUFACTURERS = ["Loupedeck", "Razer"]


class LoupedeckSerialConnection(Connection):
    """Serial connection to a Loupedeck device."""

    def __init__(self, path: str | None = None):
        super().__init__()
        self.path = path
        self.parser = MagicByteLengthParser(0x82)

    @classmethod
    def discover(cls):
        results = []
        for info in list_ports.comports():
            vendor = info.vid
            product = info.pid
            manufacturer = info.manufacturer
            if vendor in VENDOR_IDS or manufacturer in MANUFACTURERS:
                results.append(
                    {
                        "connectionType": cls,
                        "path": info.device,
                        "vendorId": vendor,
                        "productId": product,
                        "serialNumber": info.serial_number,
                    }
                )
        return results

    def close(self):
        if not self.connection:
            return

        try:
            # Send WebSocket close frame
            self.send(WS_CLOSE_FRAME, raw=True)

            # Close the serial connection
            self.connection.close()
        except Exception:
            # Ignore errors during cleanup
            pass

        # Reset the parser
        self.parser = MagicByteLengthParser(0x82)

        # Clear connection reference
        self.connection = None

        # Emit disconnect event
        self.emit("disconnect", None)

    def connect(self):
        if not self.path:
            raise ValueError("path is required")
        self.connection = serial.Serial(self.path, 256000, timeout=1)
        self.connection.write(WS_UPGRADE_HEADER)
        response = self.connection.readline()
        if not response.startswith(WS_UPGRADE_RESPONSE):
            raise RuntimeError(f"Invalid handshake response: {response!r}")
        self.emit("connect", {"address": self.path})

    def is_ready(self):
        return self.connection is not None and self.connection.is_open

    def read(self):
        if not self.connection:
            return
        data = self.connection.read(self.connection.in_waiting or 1)
        packets = self.parser.feed(data)
        for pkt in packets:
            self.emit("message", pkt)

    def send(self, buff: bytes, raw: bool = False):
        if not self.connection:
            return
        if not raw:
            if len(buff) > 0xFF:
                prep = bytearray(14)
                prep[0] = 0x82
                prep[1] = 0xFF
                prep[6:10] = len(buff).to_bytes(4, "big")
            else:
                prep = bytearray(6)
                prep[0] = 0x82
                prep[1] = 0x80 + len(buff)
            self.connection.write(prep)
        self.connection.write(buff)
