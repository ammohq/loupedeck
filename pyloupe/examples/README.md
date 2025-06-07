# PyLoupe Examples

This directory contains example scripts demonstrating various features of the PyLoupe library.

## Available Examples

### Basic Examples

- **simple_example.py**: Basic device usage and button color cycling.
- **api_example.py**: Demonstrates the usage of the PyLoupe high-level API.
- **slide_puzzle.py**: A small sliding puzzle game controlled with the knobs.

### YAML Configuration Example

- **yaml_config_example.py**: Demonstrates how to use YAML configuration for button mappings.
- **button_config.yaml**: Sample YAML configuration file for button mappings.

## Using the YAML Configuration Example

The YAML configuration example demonstrates how to define button mappings, labels, and actions in a YAML file and apply them to a Loupedeck device.

### Prerequisites

Before running the example, make sure you have the required dependencies:

```bash
pip install pyyaml pillow
```

### Running the Example

1. Connect your Loupedeck device to your computer.
2. Run the example script:

```bash
python yaml_config_example.py
```

The script will:
1. Load the button configurations from `button_config.yaml`
2. Apply the configurations to your Loupedeck device
3. Set up event handlers to execute the configured actions when buttons are pressed

If the `button_config.yaml` file doesn't exist, the script will create a sample configuration file that you can customize.

### Customizing the Configuration

You can customize the button configurations by editing the `button_config.yaml` file. Each button configuration has the following properties:

- `label`: The text to display on the button
- `action`: The action to perform when the button is pressed (e.g., launch an application, open a URL)
- `icon`: Path to an icon image to display on the button (optional)

You can also add additional properties for more advanced configurations:

- `color`: Button LED color in hex format (e.g., "#FF0000")
- `background`: Button background color in hex format (e.g., "#333333")
- `font_size`: Font size for the button label
- `font_color`: Text color for the button label in hex format (e.g., "#FFFFFF")

For more detailed information about button mapping with YAML configuration, see the [Button Mapping Documentation](../docs/button_mapping.md).