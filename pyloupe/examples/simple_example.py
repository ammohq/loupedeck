"""Simple device demonstration similar to the JavaScript example."""

import os
import random
import sys
import threading
import time
from PIL import Image, ImageDraw

# Allow running example directly from source checkout
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pyloupe.discovery import discover


def draw_key_colors(dev) -> None:
    """Fill each key area with a solid color."""
    colors = [
        "#f66",
        "#f95",
        "#fb4",
        "#fd6",
        "#ff9",
        "#be9",
        "#9e9",
        "#9db",
        "#9cc",
        "#88c",
        "#c9c",
        "#d89",
    ]
    if not hasattr(dev, "columns") or not hasattr(dev, "rows"):
        return
    size = getattr(dev, "key_size", 90)
    offset_x = getattr(dev, "visibleX", (0, 0))[0]
    for i in range(dev.rows * dev.columns):
        col = i % dev.columns
        row = i // dev.columns
        color = colors[i % len(colors)]
        img = Image.new("RGB", (size, size), color)
        dev.display_image(img, "center", offset_x + col * size, row * size)
    if "left" in getattr(dev, "displays", {}):
        w = dev.displays["left"]["width"]
        h = dev.displays["left"]["height"]
        dev.display_image(Image.new("RGB", (w, h), "white"), "left")
    if "right" in getattr(dev, "displays", {}):
        w = dev.displays["right"]["width"]
        h = dev.displays["right"]["height"]
        dev.display_image(Image.new("RGB", (w, h), "white"), "right")
    if "knob" in getattr(dev, "displays", {}):
        draw_grid(dev, 0)


def draw_grid(dev, rotation: float) -> None:
    """Draw a simple rotated grid on the knob screen."""
    screen = dev.displays.get("knob")
    if not screen:
        return
    w = screen["width"]
    h = screen["height"]
    half = w // 2
    img = Image.new("RGB", (w, h), "black")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, half - 1, half - 1), fill="#f66")
    draw.rectangle((half, 0, w - 1, half - 1), fill="#fd6")
    draw.rectangle((0, half, half - 1, h - 1), fill="#9e9")
    draw.rectangle((half, half, w - 1, h - 1), fill="#88c")
    img = img.rotate(rotation, expand=False)
    dev.display_image(img, "knob")


def cycle_colors(dev) -> None:
    """Cycle button colors with random values."""
    idx = 0
    buttons = getattr(dev, "buttons", [])
    while buttons:
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        try:
            dev.set_button_color(buttons[idx], f"#{r:02x}{g:02x}{b:02x}")
        except Exception:
            pass
        idx = (idx + 1) % len(buttons)
        time.sleep(0.1)


def main() -> None:
    device = None
    while device is None:
        try:
            device = discover()
        except Exception as exc:  # pragma: no cover - example code
            print(f"{exc}. Reattempting in 3 seconds...")
            time.sleep(3)

    brightness = 1.0
    rotation = 180.0

    def on_connect(info):
        print(f"✅ Connected to {device.type} at {info.get('address')}")
        device.set_brightness(brightness)
        draw_key_colors(device)
        if getattr(device, "buttons", []):
            thread = threading.Thread(target=cycle_colors, args=(device,), daemon=True)
            thread.start()

    def on_disconnect(err):
        if not err:
            return
        interval = getattr(device, "reconnect_interval", 3000)
        print(
            f"Connection to Loupedeck lost ({getattr(err, 'message', err)}). Reconnecting in {interval/1000}s..."
        )

    def on_down(data):
        print(f"Button {data['id']} pressed")
        if data["id"] == 0:
            draw_key_colors(device)

    def on_up(data):
        print(f"Button {data['id']} released")

    def on_rotate(data):
        nonlocal brightness, rotation
        knob = data.get("id")
        delta = data.get("delta", 0)
        print(f"Knob {knob} rotated {'right' if delta > 0 else 'left'}")
        if knob == "knobCL":
            brightness = max(0.0, min(1.0, brightness + delta * 0.1))
            print(f"Setting brightness level {round(brightness * 100)}%")
            device.set_brightness(brightness)
        if knob == "knobCT":
            rotation += delta * 9  # approx 40 ticks per rotation
            draw_grid(device, rotation)

    device.on("connect", on_connect)
    device.on("disconnect", on_disconnect)
    device.on("down", on_down)
    device.on("up", on_up)
    device.on("rotate", on_rotate)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        device.close()


if __name__ == "__main__":
    main()
