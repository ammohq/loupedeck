"""
Custom exceptions for the PyLoupe library.

This module defines custom exception classes for specific error conditions
that can occur when using the PyLoupe library.
"""

from typing import Optional


class PyLoupeError(Exception):
    """Base exception class for all PyLoupe errors."""
    pass


class ConnectionError(PyLoupeError):
    """Exception raised for errors related to device connections."""
    pass


class DeviceNotFoundError(ConnectionError):
    """Exception raised when no devices are found during discovery."""
    def __init__(self, message: str = "No Loupedeck devices found"):
        self.message = message
        super().__init__(self.message)


class ConnectionTimeoutError(ConnectionError):
    """Exception raised when a connection times out."""
    def __init__(self, message: str = "Connection timed out", device: Optional[str] = None):
        self.device = device
        self.message = message
        if device:
            self.message += f" (device: {device})"
        super().__init__(self.message)


class InvalidResponseError(ConnectionError):
    """Exception raised when an invalid response is received from a device."""
    def __init__(self, message: str = "Invalid response from device", response: Optional[bytes] = None):
        self.response = response
        self.message = message
        if response:
            self.message += f" (response: {response!r})"
        super().__init__(self.message)


class CommandError(PyLoupeError):
    """Exception raised for errors related to device commands."""
    pass


class InvalidCommandError(CommandError):
    """Exception raised when an invalid command is sent to a device."""
    pass


class DeviceError(PyLoupeError):
    """Exception raised for device-specific errors."""
    pass


class UnsupportedFeatureError(DeviceError):
    """Exception raised when a feature is not supported by the device."""
    def __init__(self, feature: str, device_type: Optional[str] = None):
        self.feature = feature
        self.device_type = device_type
        message = f"Feature '{feature}' is not supported"
        if device_type:
            message += f" by {device_type}"
        self.message = message
        super().__init__(self.message)


class ConfigurationError(PyLoupeError):
    """Exception raised for configuration errors."""
    pass


class ValidationError(PyLoupeError):
    """Exception raised for validation errors."""
    pass