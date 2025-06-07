"""
Example script demonstrating how to use YAML configuration for button mappings with PyLoupe.

This script shows how to:
1. Load button configurations from a YAML file
2. Apply the configurations to a Loupedeck device
3. Handle button presses to execute the configured actions
"""

import os
import sys
import time
import yaml
import platform
import subprocess
import webbrowser
from PIL import Image, ImageDraw, ImageFont

# Add the parent directory to the path so we can import pyloupe
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyloupe.api import connect
from pyloupe.logger import set_log_level, LogLevel

# Set log level to INFO
set_log_level(LogLevel.INFO)

def execute_action(action):
    """Execute the action specified in the button configuration.
    
    Args:
        action (str): The action to execute (application name or URL)
    """
    print(f"Executing action: {action}")
    
    if action.startswith("http://") or action.startswith("https://"):
        # Open URL in default browser
        webbrowser.open(action)
    else:
        # Launch application
        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                subprocess.Popen(["open", "-a", action])
            elif system == "Windows":
                subprocess.Popen(["start", action], shell=True)
            elif system == "Linux":
                subprocess.Popen([action])
        except Exception as e:
            print(f"Error executing action '{action}': {e}")

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

def main():
    # Path to the YAML configuration file
    config_path = os.path.join(os.path.dirname(__file__), "button_config.yaml")
    
    # Check if the configuration file exists
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        print("Creating a sample configuration file...")
        
        # Create a sample configuration
        sample_config = {
            "buttons": {
                "1": {
                    "label": "Browser",
                    "action": "Google Chrome",
                    "icon": ""
                },
                "2": {
                    "label": "Terminal",
                    "action": "Terminal",
                    "icon": ""
                },
                "3": {
                    "label": "GitHub",
                    "action": "https://github.com",
                    "icon": ""
                }
            }
        }
        
        # Save the sample configuration
        with open(config_path, "w") as file:
            yaml.dump(sample_config, file, default_flow_style=False)
        
        print(f"Sample configuration created at: {config_path}")
        print("You can edit this file to customize your button mappings.")
    
    # Load the configuration
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return
    
    # Connect to the device
    try:
        print("Connecting to Loupedeck device...")
        device = connect()
        print(f"Connected to {device.type}!")
    except Exception as e:
        print(f"Error connecting to device: {e}")
        return
    
    # Set brightness to 70%
    device.set_brightness(0.7)
    
    # Apply button configurations
    print("Applying button configurations...")
    for button_id, button_config in config.get("buttons", {}).items():
        try:
            # Convert button_id to integer
            hw_button_id = int(button_id)
            
            # Get button properties
            label = button_config.get("label", "")
            action = button_config.get("action", "")
            icon_path = button_config.get("icon", "")
            color = button_config.get("color", "#333333")
            
            # Set button mapping
            device.set_button_mapping(hw_button_id, action)
            
            # Set button color if specified
            if "color" in button_config:
                device.set_button_color(str(hw_button_id), color)
            
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
            
            print(f"Configured button {button_id}: {label} -> {action}")
        except Exception as e:
            print(f"Error configuring button {button_id}: {e}")
    
    # Set up event handlers
    @device.on("down")
    def on_button_down(data):
        button_id = data.get("id")
        # Convert button ID to string for dictionary lookup
        str_button_id = str(button_id)
        
        if str_button_id in config.get("buttons", {}):
            action = config["buttons"][str_button_id].get("action", "")
            if action:
                execute_action(action)
    
    # Keep the script running to handle events
    print("Setup complete. Press Ctrl+C to exit...")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        device.close()

if __name__ == "__main__":
    main()