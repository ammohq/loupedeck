import asyncio
import websockets
from ..constants import CONNECTION_TIMEOUT
from ..eventemitter import EventEmitter

DISCONNECT_CODES = {
    'NORMAL': 1000,
    'TIMEOUT': 1006,
}


class LoupedeckWSConnection(EventEmitter):
    def __init__(self, host: str | None = None):
        super().__init__()
        self.host = host
        self.connection = None
        self.last_tick = None
        self.connection_timeout = CONNECTION_TIMEOUT
        self._keepalive_task = None

    @classmethod
    def discover(cls):
        # Python port does not implement network scanning yet
        return []

    async def connect(self):
        if not self.host:
            raise ValueError('host is required')
        self.address = f'ws://{self.host}'
        self.connection = await websockets.connect(self.address)
        self.last_tick = asyncio.get_event_loop().time()
        self._keepalive_task = asyncio.create_task(self._check_connected())
        self.emit('connect', {'address': self.address})

    async def close(self):
        if self.connection:
            await self.connection.close()

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

