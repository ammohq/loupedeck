import struct
from pyloupe.util import rgba2rgb565


def test_rgba2rgb565_single_pixel_red():
    rgba = bytes([255, 0, 0, 255])
    result = rgba2rgb565(rgba, 1)
    assert result == struct.pack('<H', 0xF800)


def test_rgba2rgb565_two_pixels():
    rgba = bytes([
        255, 0, 0, 255,
        0, 255, 0, 255,
    ])
    result = rgba2rgb565(rgba, 2)
    expected = struct.pack('<HH', 0xF800, 0x07E0)
    assert result == expected
