import struct


def rgba2rgb565(rgba: bytes, pixel_size: int) -> bytes:
    """Convert RGBA byte data to RGB565 byte data.

    This function converts 32-bit RGBA color data (8 bits per channel) to 16-bit RGB565 format
    (5 bits for red, 6 bits for green, 5 bits for blue). This format is commonly used by
    embedded displays to reduce memory usage.

    Args:
        rgba: A bytes object containing RGBA data (4 bytes per pixel)
        pixel_size: The number of pixels in the data

    Returns:
        A bytes object containing the RGB565 data (2 bytes per pixel)
    """
    output = bytearray(pixel_size * 2)
    for i in range(0, pixel_size * 4, 4):
        red = rgba[i]
        green = rgba[i + 1]
        blue = rgba[i + 2]
        color = (blue >> 3) | ((green & 0xFC) << 3) | ((red & 0xF8) << 8)
        struct.pack_into("<H", output, i // 2, color)
    return bytes(output)
