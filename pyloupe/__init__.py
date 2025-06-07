"""Convenience imports for the PyLoupe package."""

from .device import (
    LoupedeckDevice,
)
from .device import (
    LoupedeckLive,
    LoupedeckCT,
    LoupedeckLiveS,
    RazerStreamController,
    RazerStreamControllerX,
)
from .constants import HAPTIC
from .discovery import discover

__version__ = "0.1.0"

__all__ = [
    "LoupedeckDevice",
    "LoupedeckLive",
    "LoupedeckLiveS",
    "LoupedeckCT",
    "RazerStreamController",
    "RazerStreamControllerX",
    "HAPTIC",
    "discover",
    "__version__",
]
