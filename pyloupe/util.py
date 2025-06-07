import struct


def rgba2rgb565(rgba: bytes, pixel_size: int) -> bytes:
    """Convert RGBA byte data to RGB565 byte data."""
    output = bytearray(pixel_size * 2)
    for i in range(0, pixel_size * 4, 4):
        red = rgba[i]
        green = rgba[i + 1]
        blue = rgba[i + 2]
        color = (blue >> 3) | ((green & 0xFC) << 3) | ((red & 0xF8) << 8)
        struct.pack_into("<H", output, i // 2, color)
    return bytes(output)
