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

    def __init__(
        self, 
        path: str | None = None,
        timeout: float = 1.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        super().__init__()
        self.logger.debug(
            "Initializing serial connection (path=%s, timeout=%s, max_retries=%s, retry_delay=%s)",
            path, timeout, max_retries, retry_delay
        )
        self.path = path
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
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

        retry_count = 0
        last_error = None

        while retry_count <= self.max_retries:
            try:
                if retry_count > 0:
                    self.logger.info("Retry attempt %d of %d", retry_count, self.max_retries)
                    import time
                    time.sleep(self.retry_delay)

                self.logger.debug("Opening serial port %s at 256000 baud (timeout=%.1f)", 
                                 self.path, self.timeout)
                self.connection = serial.Serial(self.path, 256000, timeout=self.timeout)

                self.logger.debug("Sending WebSocket upgrade header")
                self.connection.write(WS_UPGRADE_HEADER)

                self.logger.debug("Waiting for response")
                response = self.connection.readline()

                if not response.startswith(WS_UPGRADE_RESPONSE):
                    self.logger.error("Invalid handshake response: %r", response)
                    raise RuntimeError(f"Invalid handshake response: {response!r}")

                self.logger.info("Connection successful")
                self.emit("connect", {"address": self.path})
                return  # Connection successful, exit the retry loop
            except serial.SerialTimeoutException as e:
                last_error = e
                self.logger.warning("Connection timed out: %s", str(e))
                retry_count += 1
            except Exception as e:
                last_error = e
                self.logger.error("Connection failed: %s", str(e))
                retry_count += 1

                # Close the connection if it was opened
                if hasattr(self, 'connection') and self.connection:
                    try:
                        self.connection.close()
                    except Exception:
                        pass
                    self.connection = None

        # If we get here, all retries have failed
        self.logger.error("All connection attempts failed after %d retries", self.max_retries)
        if last_error:
            from ..exceptions import ConnectionTimeoutError, ConnectionError
            if isinstance(last_error, serial.SerialTimeoutException):
                raise ConnectionTimeoutError(device=self.path)
            else:
                raise ConnectionError(f"Failed to connect to {self.path}: {str(last_error)}")

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

            # Set a timeout for the read operation
            self.connection.timeout = self.timeout
            data = self.connection.read(bytes_waiting)

            if data:
                self.logger.debug("Read %d bytes", len(data))
                packets = self.parser.feed(data)
                self.logger.debug("Parsed %d packets", len(packets))

                for pkt in packets:
                    self.logger.debug("Emitting message (%d bytes)", len(pkt))
                    self.emit("message", pkt)
            else:
                self.logger.debug("No data read (possible timeout)")
        except serial.SerialTimeoutException as e:
            self.logger.warning("Timeout reading from serial port: %s", str(e))
            # Don't close the connection on timeout, just report it
        except serial.SerialException as e:
            self.logger.error("Serial error: %s", str(e))
            # Connection might be broken, try to close it
            self.close()
        except Exception as e:
            self.logger.error("Error reading from serial port: %s", str(e))

    def send(self, buff: bytes, raw: bool = False, retry_on_error: bool = True):
        if not self.connection:
            self.logger.warning("Cannot send: connection not ready")
            from ..exceptions import CommandError
            raise CommandError("Cannot send data: device connection is not ready")

        retry_count = 0
        max_send_retries = 2 if retry_on_error else 0

        while retry_count <= max_send_retries:
            try:
                # Set write timeout
                self.connection.write_timeout = self.timeout

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
                return  # Success, exit the retry loop
            except serial.SerialTimeoutException as e:
                self.logger.warning("Timeout sending data: %s", str(e))
                retry_count += 1
                if retry_count <= max_send_retries:
                    self.logger.info("Retrying send operation (%d of %d)", 
                                    retry_count, max_send_retries)
                    import time
                    time.sleep(0.5)  # Short delay before retry
            except serial.SerialException as e:
                self.logger.error("Serial error sending data: %s", str(e))
                # Connection might be broken, try to close it
                self.close()
                from ..exceptions import ConnectionError
                raise ConnectionError(f"Serial connection error: {str(e)}")
            except Exception as e:
                self.logger.error("Error sending data: %s", str(e))
                from ..exceptions import CommandError
                raise CommandError(f"Failed to send data: {str(e)}")

        # If we get here, all retries have failed
        if retry_count > 0:
            self.logger.error("Failed to send data after %d retries", max_send_retries)
            from ..exceptions import ConnectionTimeoutError
            raise ConnectionTimeoutError(f"Failed to send data after {max_send_retries} retries", 
                                        device=self.path)
