import serial
from serial.tools import list_ports
from ..parser import MagicByteLengthParser
from . import Connection
from ..logger import get_logger

WS_UPGRADE_HEADER = b"GET /index.html\r\nHTTP/1.1\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Key: 123abc\r\n\r\n"
WS_UPGRADE_RESPONSE = b"HTTP/1.1"
WS_CLOSE_FRAME = bytes([0x88, 0x80, 0x00, 0x00, 0x00, 0x00])

VENDOR_IDS = [0x2EC2, 0x1532]
MANUFACTURERS = ["Loupedeck", "Razer"]


class LoupedeckSerialConnection(Connection):
    """Serial connection to a Loupedeck device."""

    # Class logger
    logger = get_logger("connection.serial")

    def __init__(self, path: str | None = None):
        super().__init__()
        self.logger.debug("Initializing serial connection (path=%s)", path)
        self.path = path
        self.parser = MagicByteLengthParser(0x82)

    @classmethod
    def discover(cls):
        cls.logger.info("Discovering serial Loupedeck devices")
        results = []

        try:
            ports = list_ports.comports()
            cls.logger.debug("Found %d serial ports", len(ports))

            for info in ports:
                vendor = info.vid
                product = info.pid
                manufacturer = info.manufacturer

                cls.logger.debug("Checking port: %s (vendor=%s, product=%s, manufacturer=%s)",
                               info.device, vendor, product, manufacturer)

                if vendor in VENDOR_IDS or manufacturer in MANUFACTURERS:
                    cls.logger.info("Found Loupedeck device: %s", info.device)
                    results.append(
                        {
                            "connectionType": cls,
                            "path": info.device,
                            "vendorId": vendor,
                            "productId": product,
                            "serialNumber": info.serial_number,
                        }
                    )
        except Exception as e:
            cls.logger.error("Error discovering devices: %s", str(e))

        cls.logger.info("Found %d Loupedeck devices", len(results))
        return results

    def close(self):
        self.logger.info("Closing serial connection")

        if not self.connection:
            self.logger.debug("No connection to close")
            return

        try:
            # Send WebSocket close frame
            self.logger.debug("Sending WebSocket close frame")
            self.send(WS_CLOSE_FRAME, raw=True)

            # Close the serial connection
            self.logger.debug("Closing serial port")
            self.connection.close()
            self.logger.debug("Serial port closed")
        except Exception as e:
            # Log but ignore errors during cleanup
            self.logger.warning("Error during connection close: %s", str(e))
            pass

        # Reset the parser
        self.logger.debug("Resetting parser")
        self.parser = MagicByteLengthParser(0x82)

        # Clear connection reference
        self.connection = None
        self.logger.debug("Connection reference cleared")

        # Emit disconnect event
        self.emit("disconnect", None)
        self.logger.info("Disconnected")

    def connect(self):
        self.logger.info("Connecting to serial device")

        if not self.path:
            self.logger.error("Cannot connect: path is required")
            raise ValueError("path is required")

        try:
            self.logger.debug("Opening serial port %s at 256000 baud", self.path)
            self.connection = serial.Serial(self.path, 256000, timeout=1)

            self.logger.debug("Sending WebSocket upgrade header")
            self.connection.write(WS_UPGRADE_HEADER)

            self.logger.debug("Waiting for response")
            response = self.connection.readline()

            if not response.startswith(WS_UPGRADE_RESPONSE):
                self.logger.error("Invalid handshake response: %r", response)
                raise RuntimeError(f"Invalid handshake response: {response!r}")

            self.logger.info("Connection successful")
            self.emit("connect", {"address": self.path})
        except Exception as e:
            self.logger.error("Connection failed: %s", str(e))
            raise

    def is_ready(self):
        is_ready = self.connection is not None and self.connection.is_open
        self.logger.debug("Connection ready: %s", is_ready)
        return is_ready

    def read(self):
        if not self.connection:
            self.logger.warning("Cannot read: connection not ready")
            return

        try:
            bytes_waiting = self.connection.in_waiting or 1
            self.logger.debug("Reading %d bytes from serial port", bytes_waiting)
            data = self.connection.read(bytes_waiting)

            if data:
                self.logger.debug("Read %d bytes", len(data))
                packets = self.parser.feed(data)
                self.logger.debug("Parsed %d packets", len(packets))

                for pkt in packets:
                    self.logger.debug("Emitting message (%d bytes)", len(pkt))
                    self.emit("message", pkt)
            else:
                self.logger.debug("No data read")
        except Exception as e:
            self.logger.error("Error reading from serial port: %s", str(e))

    def send(self, buff: bytes, raw: bool = False):
        if not self.connection:
            self.logger.warning("Cannot send: connection not ready")
            return

        try:
            if not raw:
                self.logger.debug("Preparing data frame for %d bytes", len(buff))
                if len(buff) > 0xFF:
                    self.logger.debug("Using extended frame format")
                    prep = bytearray(14)
                    prep[0] = 0x82
                    prep[1] = 0xFF
                    prep[6:10] = len(buff).to_bytes(4, "big")
                else:
                    self.logger.debug("Using standard frame format")
                    prep = bytearray(6)
                    prep[0] = 0x82
                    prep[1] = 0x80 + len(buff)

                self.logger.debug("Writing %d bytes header", len(prep))
                self.connection.write(prep)

            self.logger.debug("Writing %d bytes payload", len(buff))
            self.connection.write(buff)
            self.logger.debug("Data sent successfully")
        except Exception as e:
            self.logger.error("Error sending data: %s", str(e))
