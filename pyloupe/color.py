def parse_color(color):
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
