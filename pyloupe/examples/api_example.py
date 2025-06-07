"""
Example script demonstrating the usage of the PyLoupe high-level API.

This script shows how to:
1. Connect to a Loupedeck device
2. Display text on the screen
3. Create a button grid with handlers
4. Handle knob rotations
"""

import time
import sys
import os

# Add the parent directory to the path so we can import pyloupe
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyloupe.api import LoupedeckAPI, connect, create_text_screen, create_button_screen


def button_handler(button_id, event_type):
    """Handler for button press events."""
    if event_type == "down":
        print(f"Button {button_id} pressed")
    else:
        print(f"Button {button_id} released")


def knob_handler(knob_id, delta):
    """Handler for knob rotation events."""
    print(f"Knob {knob_id} rotated: {delta}")


def main():
    # Method 1: Using the connect() convenience function
    try:
        print("Connecting to Loupedeck device...")
        api = connect()
        print("Connected!")
    except RuntimeError as e:
        print(f"Error connecting to device: {e}")
        return

    # Set brightness to 70%
    api.set_brightness(0.7)

    # Display text on the center screen
    print("Displaying welcome text...")
    api.display_text(
        "Welcome to PyLoupe!",
        screen="center",
        font_size=30,
        color="#FFFFFF",
        background_color="#000080",
    )

    # Wait for 2 seconds
    time.sleep(2)

    # Create a button grid
    print("Creating button grid...")
    buttons = [
        {
            "text": "Button 1",
            "color": "#FFFFFF",
            "background": "#FF0000",
            "position": (0, 0),
            "handler": button_handler,
        },
        {
            "text": "Button 2",
            "color": "#FFFFFF",
            "background": "#00FF00",
            "position": (0, 1),
            "handler": button_handler,
        },
        {
            "text": "Button 3",
            "color": "#FFFFFF",
            "background": "#0000FF",
            "position": (0, 2),
            "handler": button_handler,
        },
        {
            "text": "Button 4",
            "color": "#FFFFFF",
            "background": "#FFFF00",
            "position": (1, 0),
            "handler": button_handler,
        },
        {
            "text": "Button 5",
            "color": "#000000",
            "background": "#00FFFF",
            "position": (1, 1),
            "handler": button_handler,
        },
        {
            "text": "Button 6",
            "color": "#FFFFFF",
            "background": "#FF00FF",
            "position": (1, 2),
            "handler": button_handler,
        },
    ]
    api.create_button_grid(buttons, screen="center", background_color="#333333")

    # Set handlers for knobs
    print("Setting up knob handlers...")
    for knob_id in ["knobTL", "knobCL", "knobBL", "knobTR", "knobCR", "knobBR"]:
        api.set_knob_handler(knob_id, knob_handler)

    # Keep the script running to handle events
    print("Press Ctrl+C to exit...")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        # Clean up
        api.close()


def alternative_examples():
    """Show alternative ways to use the API."""
    
    # Method 2: Using the create_text_screen() convenience function
    api = create_text_screen(
        "Hello, Loupedeck!",
        screen="center",
        font_size=24,
        color="#FFFF00",
        background_color="#800000",
    )
    
    # Method 3: Using the create_button_screen() convenience function
    buttons = [
        {
            "text": "Red",
            "color": "#FFFFFF",
            "background": "#FF0000",
            "position": (0, 0),
            "handler": button_handler,
        },
        {
            "text": "Green",
            "color": "#FFFFFF",
            "background": "#00FF00",
            "position": (0, 1),
            "handler": button_handler,
        },
        {
            "text": "Blue",
            "color": "#FFFFFF",
            "background": "#0000FF",
            "position": (0, 2),
            "handler": button_handler,
        },
    ]
    api = create_button_screen(buttons, screen="center", background_color="#333333")
    
    # Don't forget to close the connection when done
    api.close()


if __name__ == "__main__":
    main()