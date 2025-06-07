from __future__ import annotations
import struct
import asyncio

from .constants import BUTTONS, COMMANDS, DEFAULT_RECONNECT_INTERVAL, HAPTIC, MAX_BRIGHTNESS
from .eventemitter import EventEmitter
from .util import rgba2rgb565
from .parser import MagicByteLengthParser
from .connections.serial import LoupedeckSerialConnection
from .connections.ws import LoupedeckWSConnection


class LoupedeckDevice(EventEmitter):
    key_size = 90

    @staticmethod
    def list(ignore_serial: bool = False, ignore_websocket: bool = False):
        devices = []
        if not ignore_serial:
            devices.extend(LoupedeckSerialConnection.discover())
        if not ignore_websocket:
            devices.extend(LoupedeckWSConnection.discover())
        return devices

    def __init__(self, host: str | None = None, path: str | None = None,
                 auto_connect: bool = True, reconnect_interval: int | None = DEFAULT_RECONNECT_INTERVAL):
        super().__init__()
        self.host = host
        self.path = path
        self.reconnect_interval = reconnect_interval
        self.transaction_id = 0
        self.connection = None
        self.pending_transactions: dict[int, callable] = {}
        self.handlers = {
            COMMANDS['BUTTON_PRESS']: self.on_button,
            COMMANDS['KNOB_ROTATE']: self.on_rotate,
        }
        if auto_connect:
            try:
                self.connect()
            except Exception:
                pass

    def connect(self):
        if self.path:
            self.connection = LoupedeckSerialConnection(self.path)
        elif self.host:
            self.connection = LoupedeckWSConnection(self.host)
        else:
            devices = self.list()
            if not devices:
                raise RuntimeError('No devices found')
            device = devices[0]
            conn_type = device['connectionType']
            args = {k: v for k, v in device.items() if k != 'connectionType'}
            self.connection = conn_type(**args)
        if hasattr(self.connection, 'connect'):
            if asyncio.iscoroutinefunction(self.connection.connect):
                import asyncio
                asyncio.get_event_loop().run_until_complete(self.connection.connect())
            else:
                self.connection.connect()
        self.connection.on('connect', self.emit.bind(self, 'connect'))
        self.connection.on('message', self.on_receive)
        self.connection.on('disconnect', self.emit.bind(self, 'disconnect'))
        return self

    def close(self):
        if self.connection:
            if hasattr(self.connection, 'close'):
                if asyncio.iscoroutinefunction(self.connection.close):
                    import asyncio
                    asyncio.get_event_loop().run_until_complete(self.connection.close())
                else:
                    self.connection.close()

    # Simplified drawing and command helpers
    def send(self, command: int, data: bytes = b""):
        if not self.connection or not self.connection.is_ready():
            return
        self.transaction_id = (self.transaction_id + 1) % 256 or 1
        header = struct.pack('BBB', min(3 + len(data), 0xFF), command, self.transaction_id)
        packet = header + data
        if hasattr(self.connection, 'send'):
            if asyncio.iscoroutinefunction(self.connection.send):
                import asyncio
                asyncio.get_event_loop().run_until_complete(self.connection.send(packet))
            else:
                self.connection.send(packet)
        return self.transaction_id

    def set_brightness(self, value: float):
        byte = max(0, min(MAX_BRIGHTNESS, round(value * MAX_BRIGHTNESS)))
        self.send(COMMANDS['SET_BRIGHTNESS'], bytes([byte]))

    def set_button_color(self, id: str, color: str):
        key = next((k for k, v in BUTTONS.items() if v == id), None)
        if key is None:
            raise ValueError(f'Invalid button ID: {id}')
        from .color import parse_color
        r, g, b, _ = parse_color(color)
        self.send(COMMANDS['SET_COLOR'], bytes([key, r, g, b]))

    # Event handlers
    def on_button(self, data: bytes):
        if len(data) < 2:
            return
        button_id = BUTTONS.get(data[0])
        event = 'down' if data[1] == 0x00 else 'up'
        self.emit(event, {'id': button_id})

    def on_rotate(self, data: bytes):
        if len(data) < 2:
            return
        knob = BUTTONS.get(data[0])
        delta = struct.unpack('b', data[1:2])[0]
        self.emit('rotate', {'id': knob, 'delta': delta})

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
    vendorId = 0x2ec2
    buttons = list(range(8))
    knobs = ['knobCL', 'knobCR', 'knobTL', 'knobTR', 'knobBL', 'knobBR']
    columns = 4
    rows = 3
    type = 'Loupedeck Live'
    visibleX = (0, 480)
    displays = {
        'center': {'id': b'\x00M', 'width': 360, 'height': 270, 'offset': (60, 0)},
        'left': {'id': b'\x00M', 'width': 60, 'height': 270},
        'right': {'id': b'\x00M', 'width': 60, 'height': 270, 'offset': (420, 0)},
    }

    def get_target(self, x, y, _id=None):
        if x < self.displays['left']['width']:
            return {'screen': 'left'}
        if x >= self.displays['left']['width'] + self.displays['center']['width']:
            return {'screen': 'right'}
        column = int((x - self.displays['left']['width']) / self.key_size)
        row = int(y / self.key_size)
        key = row * self.columns + column
        return {'screen': 'center', 'key': key}


class LoupedeckCT(LoupedeckLive):
    productId = 0x0003
    buttons = [0, 1, 2, 3, 4, 5, 6, 7, 'home', 'enter', 'undo', 'save', 'keyboard', 'fnL', 'a', 'b', 'c', 'd', 'fnR', 'e']
    displays = {
        'center': {'id': b'\x00A', 'width': 360, 'height': 270},
        'left': {'id': b'\x00L', 'width': 60, 'height': 270},
        'right': {'id': b'\x00R', 'width': 60, 'height': 270},
        'knob': {'id': b'\x00W', 'width': 240, 'height': 240, 'endianness': 'be'},
    }
    type = 'Loupedeck CT'

    def get_target(self, x, y, id=None):
        if id == 0:
            return {'screen': 'knob'}
        return super().get_target(x, y)


class LoupedeckLiveS(LoupedeckDevice):
    productId = 0x0006
    vendorId = 0x2ec2
    buttons = [0, 1, 2, 3]
    knobs = ['knobCL', 'knobTL']
    columns = 5
    rows = 3
    type = 'Loupedeck Live S'
    visibleX = (15, 465)
    displays = {
        'center': {'id': b'\x00M', 'width': 480, 'height': 270},
    }

    def get_target(self, x, y, _id=None):
        if x < self.visibleX[0] or x >= self.visibleX[1]:
            return {}
        column = int((x - self.visibleX[0]) / self.key_size)
        row = int(y / self.key_size)
        key = row * self.columns + column
        return {'screen': 'center', 'key': key}


class RazerStreamController(LoupedeckLive):
    productId = 0x0d06
    vendorId = 0x1532
    type = 'Razer Stream Controller'


class RazerStreamControllerX(LoupedeckDevice):
    productId = 0x0d09
    vendorId = 0x1532
    type = 'Razer Stream Controller X'
    buttons = []
    columns = 5
    rows = 3
    visibleX = (0, 480)
    key_size = 96
    displays = {
        'center': {'id': b'\x00M', 'width': 480, 'height': 288},
    }

    def on_button(self, data: bytes):
        super().on_button(data)
        event = 'touchstart' if data[1] == 0x00 else 'touchend'
        key = BUTTONS.get(data[0])
        row = key // self.columns
        col = key % self.columns
        touch = {
            'id': 0,
            'x': (col + 0.5) * self.key_size,
            'y': (row + 0.5) * self.key_size,
            'target': {'key': key},
        }
        self.emit(event, {'touches': [touch] if event == 'touchstart' else [], 'changedTouches': [touch]})

    def set_button_color(self, *args, **kwargs):
        raise RuntimeError('Setting key color not available on this device!')

    def vibrate(self, *args, **kwargs):
        raise RuntimeError('Vibration not available on this device!')

