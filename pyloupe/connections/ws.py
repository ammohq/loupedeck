import asyncio
import socket
import ipaddress
import websockets
from ..constants import CONNECTION_TIMEOUT
from . import Connection

DISCONNECT_CODES = {
    'NORMAL': 1000,
    'TIMEOUT': 1006,
}

# Default port for Loupedeck WebSocket connections
DEFAULT_WS_PORT = 80


class LoupedeckWSConnection(Connection):
    """WebSocket connection to a Loupedeck device."""

    def __init__(self, host: str | None = None):
        super().__init__()
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
        # Get local IP addresses and network ranges
        network_ranges = cls._get_local_networks()

        # Use asyncio to scan the network
        loop = asyncio.get_event_loop()
        devices = loop.run_until_complete(cls._scan_network(network_ranges))

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
            ip_parts = host_ip.split('.')
            network_prefix = '.'.join(ip_parts[0:3]) + '.0/24'
            network = ipaddress.IPv4Network(network_prefix, strict=False)
            network_ranges.append(network)
        except Exception:
            # Fallback to common local networks if we can't determine the host network
            common_networks = [
                '192.168.0.0/24',
                '192.168.1.0/24',
                '10.0.0.0/24',
                '10.0.1.0/24',
                '172.16.0.0/24'
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
            connection = await asyncio.wait_for(
                websockets.connect(uri), 
                timeout=0.5
            )

            # If we can connect, it might be a Loupedeck device
            await connection.close()

            return {
                'connectionType': cls,
                'host': ip,
                'port': port,
                'address': uri
            }
        except Exception:
            # Not a Loupedeck device or connection failed
            return None

    async def connect(self):
        if not self.host:
            raise ValueError('host is required')
        self.address = f'ws://{self.host}'
        self.connection = await websockets.connect(self.address)
        self.last_tick = asyncio.get_event_loop().time()
        self._keepalive_task = asyncio.create_task(self._check_connected())
        self.emit('connect', {'address': self.address})

    async def close(self):
        # Cancel the keepalive task if it exists
        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            self._keepalive_task = None

        if self.connection:
            try:
                # Close the WebSocket connection
                await self.connection.close()
            except Exception:
                # Ignore errors during cleanup
                pass

            # Clear connection reference
            self.connection = None

        # Reset last tick
        self.last_tick = None

        # Emit disconnect event
        self.emit('disconnect', None)

    def is_ready(self):
        return self.connection and not self.connection.closed

    async def _check_connected(self):
        while self.is_ready():
            await asyncio.sleep(self.connection_timeout / 1000)
            if (asyncio.get_event_loop().time() - self.last_tick) * 1000 > self.connection_timeout:
                await self.connection.close(code=DISCONNECT_CODES['TIMEOUT'])
                break

    async def read(self):
        async for message in self.connection:
            self.last_tick = asyncio.get_event_loop().time()
            self.emit('message', message)

    async def send(self, data: bytes):
        await self.connection.send(data)
