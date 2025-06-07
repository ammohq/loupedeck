# PyLoupe

PyLoupe is a Python library for controlling Loupedeck devices. It provides a simple and intuitive API for interacting with Loupedeck Live, Loupedeck CT, Loupedeck Live S, and Razer Stream Controller devices.

## Features

- Connect to Loupedeck devices via USB (serial) or network (WebSocket)
- Automatic device discovery
- Display images and text on device screens
- Handle button presses and knob rotations
- Set button colors and device brightness
- Custom button mapping
- High-level API for common operations
- Update device firmware from a binary file

## Installation

### From PyPI (Recommended)

```bash
pip install pyloupe
```

### From Source

```bash
# Clone the repository
git clone https://github.com/foxxyz/pyloupe.git
cd pyloupe

# Install the package
pip install .
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/foxxyz/pyloupe.git
cd pyloupe

# Install development dependencies
pip install -e ".[dev]"
```

## Requirements

- Python 3.7+
- Pillow (for image processing)
- websockets (for WebSocket connections)
- pyserial (for serial connections)

## Quick Start

### Basic Usage

```python
from pyloupe.device import LoupedeckDevice

# Connect to a device (automatically discovers devices)
device = LoupedeckDevice()

# Set brightness to 70%
device.set_brightness(0.7)

# Set a button color
device.set_button_color("knobTL", "#FF0000")  # Red

# Handle button events
@device.on("down")
def on_button_down(data):
    print(f"Button {data['id']} pressed")

@device.on("up")
def on_button_up(data):
    print(f"Button {data['id']} released")

# Handle knob rotation
@device.on("rotate")
def on_knob_rotate(data):
    print(f"Knob {data['id']} rotated: {data['delta']}")

# Keep the script running to handle events
import time
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    device.close()
```

### Using the High-Level API

```python
from pyloupe.api import connect, create_text_screen, create_button_screen

# Connect to a device
api = connect()

# Display text on the center screen
api.display_text(
    "Hello, World!",
    screen="center",
    font_size=30,
    color="#FFFFFF",
    background_color="#000080",
)

# Create a button grid
buttons = [
    {
        "text": "Button 1",
        "color": "#FFFFFF",
        "background": "#FF0000",
        "position": (0, 0),
        "handler": lambda button_id, event: print(f"Button {button_id} {event}"),
    },
    {
        "text": "Button 2",
        "color": "#FFFFFF",
        "background": "#00FF00",
        "position": (0, 1),
        "handler": lambda button_id, event: print(f"Button {button_id} {event}"),
    },
]
api.create_button_grid(buttons, screen="center")

# Set a handler for a knob
api.set_knob_handler("knobTL", lambda knob_id, delta: print(f"Knob {knob_id} rotated: {delta}"))

# Keep the script running to handle events
import time
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    api.close()
```

### Using Context Managers

```python
from pyloupe.device import LoupedeckDevice
from PIL import Image

# Use a context manager to ensure the device is properly closed
with LoupedeckDevice() as device:
    # Display an image on the center screen
    image = Image.open("example.png")
    device.display_image(image, screen="center")

    # Wait for 5 seconds
    import time
    time.sleep(5)

# Device is automatically closed when exiting the context
```

### Example Scripts

Additional examples are available in the `pyloupe/examples` directory. These
mirror the JavaScript demos provided in the root of the repository:

* `simple_example.py` – basic device usage and button color cycling.
* `slide_puzzle.py` – a small sliding puzzle game controlled with the knobs.

## Supported Devices

- Loupedeck Live
- Loupedeck CT
- Loupedeck Live S
- Razer Stream Controller
- Razer Stream Controller X

## Documentation

For more detailed documentation and examples, see the [examples](examples/) directory.

### Button Mapping with YAML Configuration

PyLoupe supports using YAML configuration files for button mappings. This allows you to define button layouts, actions, and appearances in a structured and maintainable way.

For detailed instructions and examples, see:
- [Button Mapping Documentation](docs/button_mapping.md) - Comprehensive guide on using YAML configuration
- [YAML Config Example](examples/yaml_config_example.py) - Working example script that loads button configurations from a YAML file

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
