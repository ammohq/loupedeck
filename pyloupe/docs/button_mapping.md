# Button Mapping with PyLoupe

This document explains how to use PyLoupe with YAML configuration files for button mappings.

## Overview

PyLoupe allows you to map buttons on your Loupedeck device to specific actions. While the library provides methods to set button mappings programmatically, you can also use a YAML configuration file to define your button mappings in a more structured and maintainable way.

## YAML Configuration Format

Below is an example of a YAML configuration file for button mappings:

```yaml
buttons:
  1:
    label: "Brave"
    action: "Brave Browser"
    icon: "icons/brave-browser-icon.png"
  2:
    label: "Telegram"
    action: "Telegram"
    icon: "icons/telegram.512x512.png"
  3:
    label: "Slack"
    action: "Slack"
    icon: "icons/slack-icon.512x511.png"
  4:
    label: "Mail"
    action: "Mail"
    icon: "icons/icons8-email-96.png"
  5:
    label: "VSCode"
    action: "Visual Studio Code"
    icon: ""
  6:
    label: "PyCharm"
    action: "PyCharm"
    icon: "icons/pycharm.512x512.png"
  7:
    label: "GitKraken"
    action: "GitKraken"
    icon: "icons/gitkraken.512x506.png"
  8:
    label: "Terminal"
    action: "Terminal"
    icon: "icons/utilities-terminal.505x512.png"
  9:
    label: "pgAdmin 4"
    action: "pgAdmin 4"
    icon: "icons/postgres.png"
  10:
    label: "Bambu"
    action: "Bambu Studio"
    icon: ""
  11:
    label: "Backend"
    action: "http://localhost:8000"
    icon: ""
  12:
    label: "Frontend"
    action: "http://localhost:4200"
    icon: ""
  13:
    label: "Kubernetes"
    action: "Kubernetes Dashboard"
    icon: ""
  14:
    label: "Poopdeck"
    action: "Poopdeck"
    icon: ""
  15:
    label: "K9s"
    action: "K9s"
    icon: ""
```

### Configuration Structure

Each button configuration has the following properties:

- `label`: The text to display on the button
- `action`: The action to perform when the button is pressed (e.g., launch an application, open a URL)
- `icon`: Path to an icon image to display on the button (optional)

## Using YAML Configuration with PyLoupe

To use a YAML configuration file with PyLoupe, you'll need to:

1. Install the PyYAML package:
   ```bash
   pip install pyyaml
   ```

2. Create a YAML configuration file (e.g., `button_config.yaml`) with your button mappings.

3. Load the configuration in your Python script:

```python
import yaml
from PIL import Image
from pyloupe.device import LoupedeckDevice
from pyloupe.api import connect

# Load the YAML configuration
with open('button_config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Connect to the device
device = connect()

# Apply button configurations
for button_id, button_config in config['buttons'].items():
    # Convert button_id to integer (if it's a string in the YAML)
    hw_button_id = int(button_id)
    
    # Set button mapping
    device.set_button_mapping(hw_button_id, button_config['action'])
    
    # Display button label and icon (if available)
    if 'icon' in button_config and button_config['icon']:
        try:
            # Load and display the icon
            icon = Image.open(button_config['icon'])
            # You might need to resize the icon to fit the button
            icon = icon.resize((80, 80))
            device.display_image(icon, "center", x=(hw_button_id % 5) * 90, y=(hw_button_id // 5) * 90)
        except Exception as e:
            print(f"Error loading icon for button {button_id}: {e}")
    else:
        # Create a text-based button if no icon is available
        from pyloupe.api import create_text_screen
        
        # You might need to adjust the position calculation based on your device layout
        create_text_screen(
            button_config['label'],
            screen="center",
            x=(hw_button_id % 5) * 90,
            y=(hw_button_id // 5) * 90,
            width=90,
            height=90,
            font_size=14,
            color="#FFFFFF",
            background_color="#333333",
        )

# Set up event handlers
@device.on("down")
def on_button_down(data):
    button_id = data['id']
    if button_id in config['buttons']:
        action = config['buttons'][button_id]['action']
        print(f"Button {button_id} pressed, executing action: {action}")
        # Here you would implement the logic to execute the action
        # For example, launching an application or opening a URL

# Keep the script running to handle events
import time
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    device.close()
```

## Executing Actions

The `action` field in your YAML configuration can be used to define what happens when a button is pressed. Here are some examples of how to implement different types of actions:

### Launching Applications

```python
import subprocess
import platform

def execute_action(action):
    if action.startswith("http://") or action.startswith("https://"):
        # Open URL in default browser
        import webbrowser
        webbrowser.open(action)
    else:
        # Launch application
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", action])
        elif system == "Windows":
            subprocess.Popen(["start", action], shell=True)
        elif system == "Linux":
            subprocess.Popen([action])
```

## Advanced Configuration

You can extend the YAML configuration to include additional properties for more advanced button configurations:

```yaml
buttons:
  1:
    label: "Brave"
    action: "Brave Browser"
    icon: "icons/brave-browser-icon.png"
    color: "#FF0000"  # Button LED color
    background: "#333333"  # Button background color
    font_size: 14
    font_color: "#FFFFFF"
```

Then update your Python script to handle these additional properties:

```python
# Set button color if specified
if 'color' in button_config:
    device.set_button_color(hw_button_id, button_config['color'])
```

## Conclusion

Using YAML configuration files with PyLoupe provides a flexible and maintainable way to define button mappings for your Loupedeck device. This approach allows you to easily update your button configurations without modifying your Python code.