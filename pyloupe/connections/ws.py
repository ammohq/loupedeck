"""WebSocket connection handling for Loupedeck devices."""

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

    def __init__(
        self,
        host: str | None = None,
        connection_timeout: int = CONNECTION_TIMEOUT,
        connect_timeout: float = 5.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """Create a WebSocket connection instance.

        Args:
            host: Device host name or IP address.
            connection_timeout: Keepalive timeout in milliseconds.
            connect_timeout: Timeout for the initial connection attempt.
            max_retries: Number of retry attempts.
            retry_delay: Delay between retries in seconds.
        """

        super().__init__()
        self.logger.debug(
            "Initializing WebSocket connection (host=%s, connection_timeout=%s, connect_timeout=%s, max_retries=%s, retry_delay=%s)",
            host,
            connection_timeout,
            connect_timeout,
            max_retries,
            retry_delay,
        )
        self.host = host
        self.last_tick = None
        self.connection_timeout = connection_timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._keepalive_task = None

    @classmethod
    def discover(cls, scan_timeout=10.0, device_timeout=0.5):
        """Discover Loupedeck devices on the local network.

        Args:
            scan_timeout (float): Maximum time in seconds to wait for the entire scan.
            device_timeout (float): Timeout in seconds for each individual device check.

        Returns:
            list: A list of dictionaries containing device information.
        """
        cls.logger.info("Discovering Loupedeck devices on the local network")

        # Get local IP addresses and network ranges
        network_ranges = cls._get_local_networks()
        cls.logger.debug("Found %d network ranges to scan", len(network_ranges))

        # Use asyncio to scan the network
        loop = asyncio.get_event_loop()
        cls.logger.debug("Starting network scan (scan_timeout=%.1f, device_timeout=%.1f)", 
                        scan_timeout, device_timeout)
        devices = loop.run_until_complete(
            cls._scan_network(network_ranges, scan_timeout, device_timeout)
        )

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
    async def _scan_network(cls, network_ranges, scan_timeout=10.0, device_timeout=0.5):
        """Scan network ranges for Loupedeck devices.

        Args:
            network_ranges (list): A list of ipaddress.IPv4Network objects to scan.
            scan_timeout (float): Maximum time in seconds to wait for the entire scan.
            device_timeout (float): Timeout in seconds for each individual device check.

        Returns:
            list: A list of dictionaries containing device information.
        """
        devices = []
        scan_tasks = []

        cls.logger.debug("Starting network scan with timeout=%.1f, device_timeout=%.1f", 
                        scan_timeout, device_timeout)

        # Create tasks for each IP in each network range
        for network in network_ranges:
            for ip in network.hosts():
                ip_str = str(ip)
                task = asyncio.create_task(cls._check_device(ip_str, timeout=device_timeout))
                scan_tasks.append(task)

        cls.logger.debug("Created %d scan tasks", len(scan_tasks))

        # Wait for all tasks to complete (with timeout)
        cls.logger.debug("Waiting for scan tasks to complete (timeout=%.1f)", scan_timeout)
        done, pending = await asyncio.wait(scan_tasks, timeout=scan_timeout)

        # Cancel any pending tasks
        if pending:
            cls.logger.debug("Cancelling %d pending tasks", len(pending))
            for task in pending:
                task.cancel()

        # Collect results from completed tasks
        for task in done:
            try:
                result = task.result()
                if result:
                    cls.logger.debug("Found device: %s", result)
                    devices.append(result)
            except Exception as e:
                cls.logger.debug("Error processing scan result: %s", str(e))

        cls.logger.debug("Network scan completed, found %d devices", len(devices))
        return devices

    @classmethod
    async def _check_device(cls, ip, port=DEFAULT_WS_PORT, timeout=0.5):
        """Check if a device at the given IP and port is a Loupedeck device.

        Args:
            ip (str): The IP address to check.
            port (int): The port to check.
            timeout (float): Connection timeout in seconds.

        Returns:
            dict or None: Device information if a Loupedeck device is found, None otherwise.
        """
        uri = f"ws://{ip}:{port}"

        try:
            # Try to establish a WebSocket connection with the specified timeout
            cls.logger.debug("Checking device at %s (timeout=%.1f)", uri, timeout)
            connection = await asyncio.wait_for(websockets.connect(uri), timeout=timeout)

            # If we can connect, it might be a Loupedeck device
            await connection.close()
            cls.logger.debug("Successfully connected to %s", uri)

            return {"connectionType": cls, "host": ip, "port": port, "address": uri}
        except asyncio.TimeoutError:
            cls.logger.debug("Connection to %s timed out after %.1f seconds", uri, timeout)
            return None
        except Exception as e:
            cls.logger.debug("Failed to connect to %s: %s", uri, str(e))
            return None

    async def connect(self):
        """Establish the WebSocket connection with retry logic."""
        self.logger.info("Connecting to WebSocket server")
        if not self.host:
            self.logger.error("Cannot connect: host is required")
            raise ValueError("host is required")

        self.address = f"ws://{self.host}"
        self.logger.debug("Connecting to %s", self.address)

        retry_count = 0
        last_error = None

        while retry_count <= self.max_retries:
            try:
                if retry_count > 0:
                    self.logger.info("Retry attempt %d of %d", retry_count, self.max_retries)
                    await asyncio.sleep(self.retry_delay)

                self.logger.debug("Connecting with timeout of %.1f seconds", self.connect_timeout)
                self.connection = await asyncio.wait_for(
                    websockets.connect(self.address),
                    timeout=self.connect_timeout
                )
                self.logger.debug("WebSocket connection established")

                self.last_tick = asyncio.get_event_loop().time()
                self._keepalive_task = asyncio.create_task(self._check_connected())
                self.logger.debug("Started keepalive task")

                self.emit("connect", {"address": self.address})
                self.logger.info("Connection successful")
                return  # Connection successful, exit the retry loop
            except asyncio.TimeoutError as e:
                last_error = e
                self.logger.warning("Connection timed out after %.1f seconds", self.connect_timeout)
                retry_count += 1
            except Exception as e:
                last_error = e
                self.logger.error("Connection failed: %s", str(e))
                retry_count += 1

        # If we get here, all retries have failed
        self.logger.error("All connection attempts failed after %d retries", self.max_retries)
        if last_error:
            from ..exceptions import ConnectionTimeoutError, ConnectionError
            if isinstance(last_error, asyncio.TimeoutError):
                raise ConnectionTimeoutError(device=self.host)
            else:
                raise ConnectionError(f"Failed to connect to {self.address}: {str(last_error)}")

    async def close(self):
        """Close the WebSocket connection and cleanup tasks."""
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
        """Return ``True`` if the WebSocket is open."""
        is_ready = self.connection and not self.connection.closed
        self.logger.debug("Connection ready: %s", is_ready)
        return is_ready

    async def _check_connected(self):
        """Monitor the connection and close on timeout."""
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
        """Read messages from the WebSocket and emit events."""
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
        """Send raw bytes to the WebSocket."""
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
