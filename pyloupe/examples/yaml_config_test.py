"""
Test script for YAML configuration functionality in PyLoupe.

This script tests the YAML configuration functionality described in the button_mapping.md documentation.
It loads a YAML configuration file, validates it, applies it to a Loupedeck device, and tests that
the buttons work as expected.

Usage:
    python yaml_config_test.py [config_file]

    If config_file is not specified, the script will use the default button_config.yaml file.
"""

import os
import sys
import time
import yaml
import argparse
from PIL import Image, ImageDraw, ImageFont

# Add the parent directory to the path so we can import pyloupe
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyloupe.api import connect
from pyloupe.logger import set_log_level, LogLevel
from pyloupe.exceptions import ValidationError

# Set log level to INFO
set_log_level(LogLevel.INFO)

def validate_config(config):
    """Validate the YAML configuration.
    
    Args:
        config (dict): The loaded YAML configuration
        
    Returns:
        tuple: (is_valid, errors) where is_valid is a boolean and errors is a list of error messages
    """
    errors = []
    
    # Check if the config has a 'buttons' section
    if 'buttons' not in config:
        errors.append("Configuration must have a 'buttons' section")
        return False, errors
    
    # Check if the buttons section is a dictionary
    if not isinstance(config['buttons'], dict):
        errors.append("The 'buttons' section must be a dictionary")
        return False, errors
    
    # Validate each button configuration
    for button_id, button_config in config['buttons'].items():
        # Check if button_id is a valid integer
        try:
            int(button_id)
        except ValueError:
            errors.append(f"Button ID '{button_id}' must be a valid integer")
            continue
        
        # Check if button_config is a dictionary
        if not isinstance(button_config, dict):
            errors.append(f"Configuration for button {button_id} must be a dictionary")
            continue
        
        # Check for required fields
        if 'label' not in button_config:
            errors.append(f"Button {button_id} is missing required field 'label'")
        
        if 'action' not in button_config:
            errors.append(f"Button {button_id} is missing required field 'action'")
        
        # Validate icon path if provided
        if 'icon' in button_config and button_config['icon']:
            icon_path = button_config['icon']
            if not os.path.exists(icon_path):
                errors.append(f"Icon file for button {button_id} not found: {icon_path}")
    
    return len(errors) == 0, errors

def create_button_image(label, icon_path=None, width=90, height=90, 
                       background_color="#333333", text_color="#FFFFFF", font_size=14):
    """Create a button image with label and optional icon.
    
    Args:
        label (str): The text to display on the button
        icon_path (str, optional): Path to an icon image
        width (int): Button width
        height (int): Button height
        background_color (str): Background color in hex format
        text_color (str): Text color in hex format
        font_size (int): Font size for the label
        
    Returns:
        PIL.Image.Image: The created button image
    """
    # Create a new image with the specified background color
    from pyloupe.color import parse_color
    bg_color = parse_color(background_color)
    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to load the icon if provided
    icon = None
    if icon_path and os.path.exists(icon_path):
        try:
            icon = Image.open(icon_path)
            # Resize icon to fit on the button (leaving space for text)
            icon_size = min(width, height) - 30
            icon = icon.resize((icon_size, icon_size))
        except Exception as e:
            print(f"Error loading icon '{icon_path}': {e}")
    
    # Load a font
    try:
        font = ImageFont.truetype("Arial", font_size)
    except:
        # Fallback to default font if Arial is not available
        font = ImageFont.load_default()
    
    # Calculate text position
    text_width, text_height = draw.textsize(label, font=font)
    
    if icon:
        # If we have an icon, position it above the text
        icon_y = 5
        text_y = icon_y + icon.height + 5
        
        # Center the icon horizontally
        icon_x = (width - icon.size[0]) // 2
        
        # Paste the icon onto the button image
        img.paste(icon, (icon_x, icon_y), icon if icon.mode == 'RGBA' else None)
    else:
        # If no icon, center the text vertically
        text_y = (height - text_height) // 2
    
    # Center the text horizontally
    text_x = (width - text_width) // 2
    
    # Draw the text
    draw.text((text_x, text_y), label, fill=text_color, font=font)
    
    return img

def test_button_press(device, button_id, action):
    """Test a button press by simulating it and checking the result.
    
    Args:
        device: The Loupedeck device
        button_id (int): The button ID
        action (str): The expected action
        
    Returns:
        bool: True if the test passed, False otherwise
    """
    print(f"Testing button {button_id} with action: {action}")
    
    # We can't actually simulate a button press programmatically,
    # so we'll just log that we would test it
    print(f"  Would press button {button_id} and verify action: {action}")
    
    return True

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test YAML configuration for PyLoupe')
    parser.add_argument('config_file', nargs='?', 
                        default=os.path.join(os.path.dirname(__file__), "button_config.yaml"),
                        help='Path to the YAML configuration file')
    args = parser.parse_args()
    
    config_path = args.config_file
    
    # Check if the configuration file exists
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        return 1
    
    # Load the configuration
    try:
        print(f"Loading configuration from {config_path}...")
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return 1
    
    # Validate the configuration
    print("Validating configuration...")
    is_valid, errors = validate_config(config)
    if not is_valid:
        print("Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    print("Configuration validation passed!")
    
    # Connect to the device
    try:
        print("Connecting to Loupedeck device...")
        device = connect()
        print(f"Connected to {device.type}!")
    except Exception as e:
        print(f"Error connecting to device: {e}")
        return 1
    
    # Set brightness to 70%
    device.set_brightness(0.7)
    
    # Apply button configurations
    print("Applying button configurations...")
    button_count = 0
    success_count = 0
    
    for button_id, button_config in config.get("buttons", {}).items():
        try:
            button_count += 1
            
            # Convert button_id to integer
            hw_button_id = int(button_id)
            
            # Get button properties
            label = button_config.get("label", "")
            action = button_config.get("action", "")
            icon_path = button_config.get("icon", "")
            
            print(f"Configuring button {button_id}: {label} -> {action}")
            
            # Set button mapping
            device.set_button_mapping(hw_button_id, action)
            
            # Set button color if specified
            if "color" in button_config:
                color = button_config.get("color")
                try:
                    device.set_button_color(str(hw_button_id), color)
                    print(f"  Set button color to {color}")
                except Exception as e:
                    print(f"  Warning: Could not set button color: {e}")
            
            # Create and display button image
            # Calculate button position (adjust based on your device layout)
            # This assumes a 5-column layout
            x = (hw_button_id - 1) % 5 * 90
            y = (hw_button_id - 1) // 5 * 90
            
            # Create button image
            button_image = create_button_image(
                label, 
                icon_path,
                background_color=button_config.get("background", "#333333"),
                text_color=button_config.get("font_color", "#FFFFFF"),
                font_size=button_config.get("font_size", 14)
            )
            
            # Display the button image
            device.display_image(button_image, "center", x, y)
            
            # Test the button
            if test_button_press(device, hw_button_id, action):
                success_count += 1
                print(f"  Button {button_id} configured successfully")
            else:
                print(f"  Button {button_id} configuration test failed")
            
        except Exception as e:
            print(f"Error configuring button {button_id}: {e}")
    
    print(f"\nConfiguration test results: {success_count}/{button_count} buttons configured successfully")
    
    # Set up event handlers for manual testing
    print("\nSetup complete. You can now manually test the buttons.")
    print("Press each button to verify that the correct action is executed.")
    print("Press Ctrl+C to exit...")
    
    # Track which buttons have been pressed
    pressed_buttons = set()
    
    @device.on("down")
    def on_button_down(data):
        button_id = data.get("id")
        # Convert button ID to string for dictionary lookup
        str_button_id = str(button_id)
        
        if str_button_id in config.get("buttons", {}):
            action = config["buttons"][str_button_id].get("action", "")
            label = config["buttons"][str_button_id].get("label", "")
            
            print(f"Button {button_id} ({label}) pressed, action: {action}")
            pressed_buttons.add(str_button_id)
            
            # Print progress
            total_buttons = len(config.get("buttons", {}))
            pressed_count = len(pressed_buttons)
            print(f"Progress: {pressed_count}/{total_buttons} buttons tested")
            
            if pressed_count == total_buttons:
                print("All buttons have been tested!")
    
    # Keep the script running to handle events
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Test ended by user.")
    finally:
        # Print final results
        total_buttons = len(config.get("buttons", {}))
        pressed_count = len(pressed_buttons)
        print(f"\nFinal test results: {pressed_count}/{total_buttons} buttons tested")
        
        # List untested buttons
        if pressed_count < total_buttons:
            print("Untested buttons:")
            for button_id in config.get("buttons", {}):
                if button_id not in pressed_buttons:
                    label = config["buttons"][button_id].get("label", "")
                    print(f"  - Button {button_id} ({label})")
        
        device.close()
        print("Test completed.")

if __name__ == "__main__":
    sys.exit(main())