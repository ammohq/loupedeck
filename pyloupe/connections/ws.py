import asyncio
import socket
import ipaddress
import websockets
from ..constants import CONNECTION_TIMEOUT
from . import Connection
from ..logger import get_logger

DISCONNECT_CODES = {
    "NORMAL": 1000,
    "TIMEOUT": 1006,
}

# Default port for Loupedeck WebSocket connections
DEFAULT_WS_PORT = 80


class LoupedeckWSConnection(Connection):
    """WebSocket connection to a Loupedeck device."""

    # Class logger
    logger = get_logger("connection.ws")

    def __init__(self, host: str | None = None):
        super().__init__()
        self.logger.debug("Initializing WebSocket connection (host=%s)", host)
        self.host = host
        self.last_tick = None
        self.connection_timeout = CONNECTION_TIMEOUT
        self._keepalive_task = None

    @classmethod
    def discover(cls):
        """Discover Loupedeck devices on the local network.

        Returns:
            list: A list of dictionaries containing device information.
        """
        cls.logger.info("Discovering Loupedeck devices on the local network")

        # Get local IP addresses and network ranges
        network_ranges = cls._get_local_networks()
        cls.logger.debug("Found %d network ranges to scan", len(network_ranges))

        # Use asyncio to scan the network
        loop = asyncio.get_event_loop()
        cls.logger.debug("Starting network scan")
        devices = loop.run_until_complete(cls._scan_network(network_ranges))

        cls.logger.info("Found %d devices", len(devices))
        return devices

    @staticmethod
    def _get_local_networks():
        """Get a list of local network ranges to scan.

        Returns:
            list: A list of ipaddress.IPv4Network objects representing local networks.
        """
        network_ranges = []

        # Get all network interfaces
        try:
            # Get hostname
            hostname = socket.gethostname()
            # Get host IP
            host_ip = socket.gethostbyname(hostname)

            # Create a /24 network from the host IP
            ip_parts = host_ip.split(".")
            network_prefix = ".".join(ip_parts[0:3]) + ".0/24"
            network = ipaddress.IPv4Network(network_prefix, strict=False)
            network_ranges.append(network)
        except Exception:
            # Fallback to common local networks if we can't determine the host network
            common_networks = [
                "192.168.0.0/24",
                "192.168.1.0/24",
                "10.0.0.0/24",
                "10.0.1.0/24",
                "172.16.0.0/24",
            ]
            for net in common_networks:
                try:
                    network_ranges.append(ipaddress.IPv4Network(net))
                except Exception:
                    pass

        return network_ranges

    @classmethod
    async def _scan_network(cls, network_ranges):
        """Scan network ranges for Loupedeck devices.

        Args:
            network_ranges (list): A list of ipaddress.IPv4Network objects to scan.

        Returns:
            list: A list of dictionaries containing device information.
        """
        devices = []
        scan_tasks = []

        # Create tasks for each IP in each network range
        for network in network_ranges:
            for ip in network.hosts():
                ip_str = str(ip)
                task = asyncio.create_task(cls._check_device(ip_str))
                scan_tasks.append(task)

        # Wait for all tasks to complete (with timeout)
        done, pending = await asyncio.wait(scan_tasks, timeout=5)

        # Cancel any pending tasks
        for task in pending:
            task.cancel()

        # Collect results from completed tasks
        for task in done:
            try:
                result = task.result()
                if result:
                    devices.append(result)
            except Exception:
                pass

        return devices

    @classmethod
    async def _check_device(cls, ip, port=DEFAULT_WS_PORT):
        """Check if a device at the given IP and port is a Loupedeck device.

        Args:
            ip (str): The IP address to check.
            port (int): The port to check.

        Returns:
            dict or None: Device information if a Loupedeck device is found, None otherwise.
        """
        uri = f"ws://{ip}:{port}"

        try:
            # Try to establish a WebSocket connection with a short timeout
            connection = await asyncio.wait_for(websockets.connect(uri), timeout=0.5)

            # If we can connect, it might be a Loupedeck device
            await connection.close()

            return {"connectionType": cls, "host": ip, "port": port, "address": uri}
        except Exception:
            # Not a Loupedeck device or connection failed
            return None

    async def connect(self):
        self.logger.info("Connecting to WebSocket server")
        if not self.host:
            self.logger.error("Cannot connect: host is required")
            raise ValueError("host is required")

        self.address = f"ws://{self.host}"
        self.logger.debug("Connecting to %s", self.address)

        try:
            self.connection = await websockets.connect(self.address)
            self.logger.debug("WebSocket connection established")

            self.last_tick = asyncio.get_event_loop().time()
            self._keepalive_task = asyncio.create_task(self._check_connected())
            self.logger.debug("Started keepalive task")

            self.emit("connect", {"address": self.address})
            self.logger.info("Connection successful")
        except Exception as e:
            self.logger.error("Connection failed: %s", str(e))
            raise

    async def close(self):
        self.logger.info("Closing WebSocket connection")

        # Cancel the keepalive task if it exists
        if self._keepalive_task is not None:
            self.logger.debug("Cancelling keepalive task")
            self._keepalive_task.cancel()
            self._keepalive_task = None

        if self.connection:
            try:
                # Close the WebSocket connection
                self.logger.debug("Closing WebSocket connection")
                await self.connection.close()
                self.logger.debug("WebSocket connection closed")
            except Exception as e:
                # Log but ignore errors during cleanup
                self.logger.warning("Error during connection close: %s", str(e))
                pass

            # Clear connection reference
            self.connection = None
            self.logger.debug("Connection reference cleared")

        # Reset last tick
        self.last_tick = None

        # Emit disconnect event
        self.emit("disconnect", None)
        self.logger.info("Disconnected")

    def is_ready(self):
        is_ready = self.connection and not self.connection.closed
        self.logger.debug("Connection ready: %s", is_ready)
        return is_ready

    async def _check_connected(self):
        self.logger.debug("Starting connection keepalive check")
        while self.is_ready():
            await asyncio.sleep(self.connection_timeout / 1000)

            if (
                asyncio.get_event_loop().time() - self.last_tick
            ) * 1000 > self.connection_timeout:
                self.logger.warning("Connection timed out, closing")
                await self.connection.close(code=DISCONNECT_CODES["TIMEOUT"])
                break

        self.logger.debug("Keepalive check ended")

    async def read(self):
        self.logger.debug("Starting to read messages")
        try:
            async for message in self.connection:
                self.last_tick = asyncio.get_event_loop().time()
                self.logger.debug("Received message (%d bytes)", len(message))
                self.emit("message", message)
        except Exception as e:
            self.logger.error("Error reading from connection: %s", str(e))
            raise
        finally:
            self.logger.debug("Stopped reading messages")

    async def send(self, data: bytes):
        if not self.is_ready():
            self.logger.warning("Cannot send data: connection not ready")
            return

        self.logger.debug("Sending data (%d bytes)", len(data))
        try:
            await self.connection.send(data)
            self.logger.debug("Data sent successfully")
        except Exception as e:
            self.logger.error("Error sending data: %s", str(e))
            raise
