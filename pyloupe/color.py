from typing import Tuple, Union, List


def parse_color(
    color: Union[str, Tuple[int, int, int], List[int]],
) -> Tuple[int, int, int, int]:
    """Parse a color string or RGB tuple/list into an RGBA tuple.

    Args:
        color: A color string in hex format (e.g., "#FF0000" or "#F00") or
               a tuple/list of RGB values (e.g., (255, 0, 0))

    Returns:
        A tuple of (red, green, blue, alpha) values, where each value is an integer from 0-255.
        Alpha is always 255 (fully opaque).

    Raises:
        ValueError: If the color format is not supported.
    """
    if isinstance(color, str):
        c = color.lstrip("#")
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        r = int(c[0:2], 16)
        g = int(c[2:4], 16)
        b = int(c[4:6], 16)
        return r, g, b, 255
    elif isinstance(color, (tuple, list)):
        r, g, b = color[:3]
        return int(r), int(g), int(b), 255
    else:
        raise ValueError("Unsupported color format")
