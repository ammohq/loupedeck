from abc import ABC, abstractmethod
from ..eventemitter import EventEmitter


class Connection(EventEmitter, ABC):
    """Base class for all connection types.

    This class defines the common interface for all connection types.
    Derived classes must implement the required methods.
    """

    def __init__(self):
        """Initialize the connection."""
        super().__init__()
        self.connection = None

    @classmethod
    @abstractmethod
    def discover(cls):
        """Discover available devices.

        Returns:
            list: A list of dictionaries containing device information.
        """
        pass

    @abstractmethod
    def connect(self):
        """Establish a connection to the device.

        Raises:
            ValueError: If required connection parameters are missing.
            RuntimeError: If the connection cannot be established.
        """
        pass

    @abstractmethod
    def close(self):
        """Close the connection."""
        pass

    @abstractmethod
    def is_ready(self):
        """Check if the connection is ready.

        Returns:
            bool: True if the connection is ready, False otherwise.
        """
        pass

    @abstractmethod
    def read(self):
        """Read data from the connection.

        This method should emit a 'message' event when data is received.
        """
        pass

    @abstractmethod
    def send(self, data: bytes):
        """Send data to the connection.

        Args:
            data (bytes): The data to send.
        """
        pass
