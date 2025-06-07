"""
Test script for Razer Stream Controller X.

This script tests the basic functionality of a Razer Stream Controller X device:
1. Connects to the device
2. Displays a grid of colored buttons with labels
3. Provides visual feedback when buttons are pressed
4. Tests touch events
5. Includes error handling and diagnostics
"""

import os
import sys
import time
import random
from PIL import Image, ImageDraw, ImageFont

# Allow running example directly from source checkout
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pyloupe.discovery import discover
from pyloupe.device import RazerStreamControllerX
from pyloupe.logger import set_log_level, LogLevel

# Set log level to INFO for better diagnostics
set_log_level(LogLevel.INFO)

def create_button_image(label, color="#333333", width=96, height=96, font_size=18, text_color="#FFFFFF"):
    """Create a button image with a label."""
    img = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(img)
    
    # Try to load a font
    try:
        font = ImageFont.truetype("Arial", font_size)
    except:
        # Fallback to default font if Arial is not available
        font = ImageFont.load_default()
    
    # Calculate text position to center it
    text_width, text_height = draw.textsize(label, font=font)
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2
    
    # Draw the text
    draw.text((text_x, text_y), label, fill=text_color, font=font)
    
    # Draw a border
    draw.rectangle((0, 0, width-1, height-1), outline="#FFFFFF", width=1)
    
    return img

def draw_button_grid(device):
    """Draw a grid of colored buttons with labels."""
    colors = [
        "#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF",
        "#4B0082", "#9400D3", "#FF1493", "#00FFFF", "#FF00FF",
        "#800000", "#808000", "#008000", "#800080", "#008080"
    ]
    
    print("Drawing button grid...")
    for i in range(device.rows * device.columns):
        col = i % device.columns
        row = i // device.columns
        color = colors[i % len(colors)]
        label = f"Button {i+1}"
        
        # Create and display button image
        img = create_button_image(label, color, device.key_size, device.key_size)
        x = col * device.key_size
        y = row * device.key_size
        device.display_image(img, "center", x, y)

def draw_pressed_button(device, key, pressed=True):
    """Draw a button in pressed or released state."""
    col = key % device.columns
    row = key // device.columns
    x = col * device.key_size
    y = row * device.key_size
    
    # Create a different appearance for pressed buttons
    if pressed:
        color = "#FFFFFF"
        text_color = "#000000"
        label = f"Pressed {key+1}"
    else:
        colors = [
            "#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF",
            "#4B0082", "#9400D3", "#FF1493", "#00FFFF", "#FF00FF",
            "#800000", "#808000", "#008000", "#800080", "#008080"
        ]
        color = colors[key % len(colors)]
        text_color = "#FFFFFF"
        label = f"Button {key+1}"
    
    img = create_button_image(label, color, device.key_size, device.key_size, text_color=text_color)
    device.display_image(img, "center", x, y)

def draw_welcome_screen(device):
    """Draw a welcome screen with device information."""
    width = device.displays["center"]["width"]
    height = device.displays["center"]["height"]
    
    img = Image.new("RGB", (width, height), "#000080")
    draw = ImageDraw.Draw(img)
    
    # Try to load a font
    try:
        title_font = ImageFont.truetype("Arial", 24)
        body_font = ImageFont.truetype("Arial", 18)
    except:
        # Fallback to default font
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
    
    # Draw title
    title = "Razer Stream Controller X Test"
    title_width, title_height = draw.textsize(title, font=title_font)
    draw.text(((width - title_width) // 2, 30), title, fill="#FFFFFF", font=title_font)
    
    # Draw device info
    info_text = [
        f"Device Type: {device.type}",
        f"Display Size: {width}x{height}",
        f"Button Grid: {device.columns}x{device.rows}",
        f"Button Size: {device.key_size}x{device.key_size}",
        "",
        "Touch any button to test",
        "Press Ctrl+C to exit"
    ]
    
    y_pos = 80
    for line in info_text:
        text_width, text_height = draw.textsize(line, font=body_font)
        draw.text(((width - text_width) // 2, y_pos), line, fill="#FFFFFF", font=body_font)
        y_pos += text_height + 10
    
    device.display_image(img, "center")
    
    # Wait for 3 seconds
    time.sleep(3)

def main():
    print("Searching for Razer Stream Controller X...")
    device = None
    
    # Try to discover the device
    try:
        device = discover(device_type=RazerStreamControllerX)
    except Exception as e:
        print(f"Error discovering device: {e}")
        print("Trying to discover any available device...")
        try:
            device = discover()
            if not isinstance(device, RazerStreamControllerX):
                print(f"Warning: Found {device.type}, not a Razer Stream Controller X")
                print("The test will continue, but some features may not work as expected.")
        except Exception as e:
            print(f"Error discovering any device: {e}")
            print("Please make sure your device is connected and try again.")
            return
    
    if not device:
        print("No device found. Please make sure your device is connected and try again.")
        return
    
    print(f"✅ Connected to {device.type}")
    
    # Set up event handlers
    @device.on("connect")
    def on_connect(info):
        print(f"Connected to {device.type} at {info.get('address')}")
        device.set_brightness(0.8)  # Set brightness to 80%
        draw_welcome_screen(device)
        draw_button_grid(device)
    
    @device.on("disconnect")
    def on_disconnect(err):
        if not err:
            return
        interval = getattr(device, "reconnect_interval", 3000)
        print(f"Connection lost ({getattr(err, 'message', err)}). Reconnecting in {interval/1000}s...")
    
    @device.on("down")
    def on_button_down(data):
        key = data.get("id")
        print(f"Button {key} pressed")
        draw_pressed_button(device, key, True)
    
    @device.on("up")
    def on_button_up(data):
        key = data.get("id")
        print(f"Button {key} released")
        draw_pressed_button(device, key, False)
    
    @device.on("touchstart")
    def on_touch_start(data):
        touches = data.get("touches", [])
        for touch in touches:
            key = touch.get("target", {}).get("key")
            if key is not None:
                print(f"Touch started on button {key}")
    
    @device.on("touchend")
    def on_touch_end(data):
        changed_touches = data.get("changedTouches", [])
        for touch in changed_touches:
            key = touch.get("target", {}).get("key")
            if key is not None:
                print(f"Touch ended on button {key}")
    
    # Run the test
    try:
        print("Test running. Press Ctrl+C to exit.")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Test ended by user.")
    finally:
        print("Closing connection to device...")
        device.close()
        print("Test completed.")

if __name__ == "__main__":
    main()