"""
High-level API for PyLoupe.

This module provides a simplified interface for common operations with Loupedeck devices.
It builds on top of the lower-level device API to provide a more user-friendly experience.
"""

import os
from typing import Callable, Dict, List, Optional, Tuple, Union
from PIL import Image, ImageDraw, ImageFont

from .device import LoupedeckDevice
from .constants import BUTTONS


class LoupedeckAPI:
    """High-level API for interacting with Loupedeck devices."""

    def __init__(self, device: Optional[LoupedeckDevice] = None):
        """Initialize the API with an optional device.

        Args:
            device (LoupedeckDevice, optional): An existing device instance.
                If not provided, a new device will be automatically discovered and connected.
        """
        self.device = device or self._auto_connect()
        self.button_handlers = {}
        self._setup_event_handlers()

    def _auto_connect(self) -> LoupedeckDevice:
        """Automatically discover and connect to a Loupedeck device.

        Returns:
            LoupedeckDevice: A connected device instance.

        Raises:
            RuntimeError: If no devices are found.
        """
        device = LoupedeckDevice()
        return device

    def _setup_event_handlers(self):
        """Set up event handlers for the device."""
        self.device.on("down", self._handle_button_down)
        self.device.on("up", self._handle_button_up)
        self.device.on("rotate", self._handle_knob_rotate)

    def _handle_button_down(self, data):
        """Handle button down events."""
        button_id = data.get("id")
        if button_id in self.button_handlers:
            handler = self.button_handlers[button_id]
            if callable(handler):
                handler(button_id, "down")

    def _handle_button_up(self, data):
        """Handle button up events."""
        button_id = data.get("id")
        if button_id in self.button_handlers:
            handler = self.button_handlers[button_id]
            if callable(handler):
                handler(button_id, "up")

    def _handle_knob_rotate(self, data):
        """Handle knob rotation events."""
        knob_id = data.get("id")
        delta = data.get("delta", 0)
        if knob_id in self.button_handlers:
            handler = self.button_handlers[knob_id]
            if callable(handler):
                handler(knob_id, delta)

    def set_brightness(self, brightness: float):
        """Set the brightness of the device.

        Args:
            brightness (float): Brightness value between 0.0 and 1.0.
        """
        self.device.set_brightness(brightness)

    def set_button_handler(self, button_id: Union[str, int], handler: Callable):
        """Set a handler function for a button.

        Args:
            button_id (str or int): The ID of the button.
            handler (callable): A function to call when the button is pressed or released.
                The function should accept two arguments: button_id and event_type.
        """
        self.button_handlers[button_id] = handler

    def set_knob_handler(self, knob_id: str, handler: Callable):
        """Set a handler function for a knob.

        Args:
            knob_id (str): The ID of the knob.
            handler (callable): A function to call when the knob is rotated.
                The function should accept two arguments: knob_id and delta.
        """
        self.button_handlers[knob_id] = handler

    def clear_handlers(self):
        """Clear all button and knob handlers."""
        self.button_handlers = {}

    def set_button_color(self, button_id: str, color: str):
        """Set the color of a button.

        Args:
            button_id (str): The ID of the button.
            color (str): The color to set, as a hex string (e.g., "#FF0000").
        """
        self.device.set_button_color(button_id, color)

    def display_image(self, image: Image.Image, screen: str = "center", x: int = 0, y: int = 0):
        """Display an image on a screen.

        Args:
            image (PIL.Image.Image): The image to display.
            screen (str): The screen to display the image on.
            x (int): The x-coordinate offset.
            y (int): The y-coordinate offset.
        """
        self.device.display_image(image, screen, x, y)

    def display_text(
        self,
        text: str,
        screen: str = "center",
        font_size: int = 24,
        color: str = "#FFFFFF",
        background_color: str = "#000000",
        x: int = None,
        y: int = None,
        align: str = "center",
    ):
        """Display text on a screen.

        Args:
            text (str): The text to display.
            screen (str): The screen to display the text on.
            font_size (int): The font size to use.
            color (str): The text color, as a hex string.
            background_color (str): The background color, as a hex string.
            x (int, optional): The x-coordinate offset. If None, the text will be centered.
            y (int, optional): The y-coordinate offset. If None, the text will be centered.
            align (str): Text alignment ("left", "center", or "right").
        """
        # Get screen dimensions
        if not hasattr(self.device, "displays") or screen not in self.device.displays:
            raise ValueError(f"Invalid screen: {screen}")

        screen_info = self.device.displays[screen]
        width = screen_info["width"]
        height = screen_info["height"]

        # Create a new image with the background color
        image = Image.new("RGB", (width, height), background_color)
        draw = ImageDraw.Draw(image)

        # Try to load a font, fall back to default if not available
        try:
            # Try to find a system font
            font_path = None
            if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            elif os.path.exists("/System/Library/Fonts/Helvetica.ttc"):
                font_path = "/System/Library/Fonts/Helvetica.ttc"
            elif os.path.exists("C:\\Windows\\Fonts\\Arial.ttf"):
                font_path = "C:\\Windows\\Fonts\\Arial.ttf"

            if font_path:
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # Calculate text size and position
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        if x is None:
            if align == "left":
                x = 10
            elif align == "right":
                x = width - text_width - 10
            else:  # center
                x = (width - text_width) // 2

        if y is None:
            y = (height - text_height) // 2

        # Draw the text
        draw.text((x, y), text, fill=color, font=font)

        # Display the image
        self.display_image(image, screen)

    def create_button_grid(
        self,
        buttons: List[Dict],
        screen: str = "center",
        background_color: str = "#000000",
    ):
        """Create a grid of buttons on a screen.

        Args:
            buttons (list): A list of button dictionaries, each containing:
                - text (str): The text to display on the button
                - color (str, optional): The text color
                - background (str, optional): The button background color
                - handler (callable, optional): A function to call when the button is pressed
                - position (tuple, optional): The (row, col) position of the button
            screen (str): The screen to display the buttons on.
            background_color (str): The background color for the entire grid.
        """
        # Get screen dimensions and grid layout
        if not hasattr(self.device, "displays") or screen not in self.device.displays:
            raise ValueError(f"Invalid screen: {screen}")

        screen_info = self.device.displays[screen]
        width = screen_info["width"]
        height = screen_info["height"]

        # Determine grid dimensions based on the device type
        if hasattr(self.device, "rows") and hasattr(self.device, "columns"):
            rows = self.device.rows
            cols = self.device.columns
        else:
            # Default to 3x4 grid for unknown devices
            rows = 3
            cols = 4

        # Calculate button dimensions
        button_width = width // cols
        button_height = height // rows

        # Create a new image with the background color
        image = Image.new("RGB", (width, height), background_color)
        draw = ImageDraw.Draw(image)

        # Try to load a font
        try:
            font_path = None
            if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            elif os.path.exists("/System/Library/Fonts/Helvetica.ttc"):
                font_path = "/System/Library/Fonts/Helvetica.ttc"
            elif os.path.exists("C:\\Windows\\Fonts\\Arial.ttf"):
                font_path = "C:\\Windows\\Fonts\\Arial.ttf"

            if font_path:
                font = ImageFont.truetype(font_path, 18)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # Draw each button
        for button in buttons:
            text = button.get("text", "")
            text_color = button.get("color", "#FFFFFF")
            button_bg = button.get("background", "#333333")
            position = button.get("position")

            if position is None:
                continue

            row, col = position
            if row >= rows or col >= cols:
                continue

            # Calculate button position
            x1 = col * button_width
            y1 = row * button_height
            x2 = x1 + button_width - 1
            y2 = y1 + button_height - 1

            # Draw button background
            draw.rectangle([(x1, y1), (x2, y2)], fill=button_bg)

            # Calculate text position
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = x1 + (button_width - text_width) // 2
            text_y = y1 + (button_height - text_height) // 2

            # Draw button text
            draw.text((text_x, text_y), text, fill=text_color, font=font)

            # Set button handler if provided
            handler = button.get("handler")
            if handler and callable(handler):
                button_id = row * cols + col
                self.set_button_handler(button_id, handler)

        # Display the image
        self.display_image(image, screen)

    def close(self):
        """Close the device connection."""
        if self.device:
            self.device.close()


# Convenience functions

def connect() -> LoupedeckAPI:
    """Connect to a Loupedeck device and return a high-level API instance.

    Returns:
        LoupedeckAPI: A high-level API instance connected to a device.
    """
    return LoupedeckAPI()


def create_text_screen(
    text: str,
    device: Optional[LoupedeckDevice] = None,
    screen: str = "center",
    font_size: int = 24,
    color: str = "#FFFFFF",
    background_color: str = "#000000",
) -> LoupedeckAPI:
    """Create a screen with text and return the API instance.

    Args:
        text (str): The text to display.
        device (LoupedeckDevice, optional): An existing device instance.
        screen (str): The screen to display the text on.
        font_size (int): The font size to use.
        color (str): The text color, as a hex string.
        background_color (str): The background color, as a hex string.

    Returns:
        LoupedeckAPI: The API instance used to create the screen.
    """
    api = LoupedeckAPI(device)
    api.display_text(text, screen, font_size, color, background_color)
    return api


def create_button_screen(
    buttons: List[Dict],
    device: Optional[LoupedeckDevice] = None,
    screen: str = "center",
    background_color: str = "#000000",
) -> LoupedeckAPI:
    """Create a screen with buttons and return the API instance.

    Args:
        buttons (list): A list of button dictionaries.
        device (LoupedeckDevice, optional): An existing device instance.
        screen (str): The screen to display the buttons on.
        background_color (str): The background color for the entire grid.

    Returns:
        LoupedeckAPI: The API instance used to create the screen.
    """
    api = LoupedeckAPI(device)
    api.create_button_grid(buttons, screen, background_color)
    return api