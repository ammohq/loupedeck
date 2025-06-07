"""
Mock objects for testing PyLoupe without physical devices.

This module provides mock implementations of the connection classes
to enable testing without physical Loupedeck devices.
"""

import asyncio
from unittest.mock import MagicMock
from typing import List, Dict, Any, Optional, Callable

from pyloupe.connections import Connection
from pyloupe.eventemitter import EventEmitter


class MockConnection(Connection):
    """Base class for mock connections.
    
    This class provides a common implementation for both WebSocket and Serial mock connections.
    """
    
    def __init__(self):
        super().__init__()
        self.is_connected = False
        self.sent_data = []
        self.received_data = []
        self.response_handlers = {}
        
    @classmethod
    def discover(cls):
        """Mock device discovery.
        
        Returns:
            list: A list containing a single mock device.
        """
        return [
            {
                "connectionType": cls,
                "host": "mock-host" if hasattr(cls, "host") else None,
                "path": "mock-path" if hasattr(cls, "path") else None,
                "address": "mock-address",
            }
        ]
        
    def connect(self):
        """Mock connection establishment."""
        self.is_connected = True
        self.connection = MagicMock()
        self.emit("connect", {"address": "mock-address"})
        
    def close(self):
        """Mock connection closure."""
        self.is_connected = False
        self.connection = None
        self.emit("disconnect", None)
        
    def is_ready(self):
        """Check if the mock connection is ready.
        
        Returns:
            bool: True if the connection is ready, False otherwise.
        """
        return self.is_connected and self.connection is not None
        
    def read(self):
        """Mock data reading.
        
        This method doesn't do anything in the base implementation.
        Derived classes should override this method to provide specific behavior.
        """
        pass
        
    def send(self, data: bytes):
        """Mock data sending.
        
        Args:
            data (bytes): The data to send.
        """
        self.sent_data.append(data)
        
        # Check if there's a response handler for this data
        for pattern, handler in self.response_handlers.items():
            if pattern in data:
                response = handler(data)
                if response:
                    self.receive_data(response)
                    
    def receive_data(self, data: bytes):
        """Simulate receiving data from the device.
        
        Args:
            data (bytes): The data to receive.
        """
        self.received_data.append(data)
        self.emit("message", data)
        
    def add_response_handler(self, pattern: bytes, handler: Callable[[bytes], Optional[bytes]]):
        """Add a response handler for specific data patterns.
        
        Args:
            pattern (bytes): The pattern to match in sent data.
            handler (callable): A function that takes the sent data and returns a response.
        """
        self.response_handlers[pattern] = handler


class MockWSConnection(MockConnection):
    """Mock WebSocket connection for testing."""
    
    def __init__(self, host: str = "mock-host"):
        super().__init__()
        self.host = host
        self.address = f"ws://{host}"
        self._keepalive_task = None
        
    async def connect(self):
        """Mock async connection establishment."""
        self.is_connected = True
        self.connection = MagicMock()
        self.connection.closed = False
        self.emit("connect", {"address": self.address})
        
    async def close(self):
        """Mock async connection closure."""
        if self._keepalive_task:
            self._keepalive_task.cancel()
            self._keepalive_task = None
            
        self.is_connected = False
        if self.connection:
            self.connection.closed = True
            self.connection = None
        self.emit("disconnect", None)
        
    async def read(self):
        """Mock async data reading."""
        # This is a placeholder that would normally read from the WebSocket
        # In a real implementation, this would be an async for loop
        pass
        
    async def send(self, data: bytes):
        """Mock async data sending.
        
        Args:
            data (bytes): The data to send.
        """
        self.sent_data.append(data)
        
        # Check if there's a response handler for this data
        for pattern, handler in self.response_handlers.items():
            if pattern in data:
                response = handler(data)
                if response:
                    self.receive_data(response)


class MockSerialConnection(MockConnection):
    """Mock Serial connection for testing."""
    
    def __init__(self, path: str = "mock-path"):
        super().__init__()
        self.path = path
        self.parser = MagicMock()
        self.parser.feed.return_value = []
        
    def connect(self):
        """Mock connection establishment."""
        self.is_connected = True
        self.connection = MagicMock()
        self.connection.is_open = True
        self.emit("connect", {"address": self.path})
        
    def close(self):
        """Mock connection closure."""
        self.is_connected = False
        if self.connection:
            self.connection.is_open = False
            self.connection = None
        self.emit("disconnect", None)
        
    def read(self):
        """Mock data reading."""
        # This is a placeholder that would normally read from the serial port
        pass
        
    def send(self, data: bytes, raw: bool = False):
        """Mock data sending.
        
        Args:
            data (bytes): The data to send.
            raw (bool): Whether to send the data raw or wrap it in a frame.
        """
        self.sent_data.append((data, raw))
        
        # Check if there's a response handler for this data
        for pattern, handler in self.response_handlers.items():
            if pattern in data:
                response = handler(data)
                if response:
                    self.receive_data(response)