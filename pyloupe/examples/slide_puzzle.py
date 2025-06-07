"""Slide puzzle demo ported from the JavaScript example."""

import os
import random
import sys
import threading
import time
from math import floor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pyloupe.discovery import discover


class Tile:
    def __init__(self, source: Image.Image, sx: int, sy: int, row: int, column: int, correct_row: int, correct_col: int, bounds):
        self.image = source.crop((sx, sy, sx + 90, sy + 90))
        self.bounds = bounds
        self._row = row
        self._col = column
        self.correct_row = correct_row
        self.correct_col = correct_col
        self.x = bounds[0][0] + column * 90
        self.y = bounds[1][0] + row * 90

    def can_move_in(self, direction, tiles) -> bool:
        dx, dy = direction
        search_x = (self.x + 90 - 1 + dx) if dx > 0 else (self.x + dx if dx < 0 else 0)
        search_y = (self.y + 90 - 1 + dy) if dy > 0 else (self.y + dy if dy < 0 else 0)
        if (
            search_x < self.bounds[0][0]
            or search_x >= self.bounds[0][1]
            or search_y < self.bounds[1][0]
            or search_y >= self.bounds[1][1]
        ):
            return False
        return not any(t.contains((search_x, search_y)) for t in tiles)

    def contains(self, pos) -> bool:
        x, y = pos
        return self.x <= x < self.x + 90 and self.y <= y < self.y + 90

    def in_place(self) -> bool:
        return self._row == self.correct_row and self._col == self.correct_col

    @property
    def row(self):
        return self._row

    @row.setter
    def row(self, val):
        self._row = val
        self.y = self.bounds[1][0] + val * 90

    @property
    def column(self):
        return self._col

    @column.setter
    def column(self, val):
        self._col = val
        self.x = self.bounds[0][0] + val * 90


class SlidePuzzle:
    def __init__(self, image_path: Path, rows: int, columns: int, offset):
        self.on_start = lambda: None
        self.on_win = lambda: None
        self.outcome = None
        self.image_path = image_path
        self.rows = rows
        self.columns = columns
        self.offset = offset
        self.tiles = []
        self.selected_tile = None
        self.source = None

    def init(self):
        self.source = Image.open(self.image_path)
        tiles = []
        for c in range(self.columns):
            for r in range(self.rows):
                if r == self.rows - 1 and c == self.columns - 1:
                    continue
                tiles.append(
                    Tile(
                        self.source,
                        c * 90,
                        r * 90,
                        r,
                        c,
                        r,
                        c,
                        [
                            [self.offset[0], self.offset[0] + self.columns * 90],
                            [0, self.rows * 90],
                        ],
                    )
                )
        self.tiles = tiles

    def shuffle(self):
        tmp = self.tiles[:]
        shuffled = []
        for c in range(self.columns):
            for r in range(self.rows):
                if r == self.rows - 1 and c == self.columns - 1:
                    continue
                idx = random.randrange(len(tmp))
                tile = tmp.pop(idx)
                tile.column = c
                tile.row = r
                shuffled.append(tile)
        self.tiles = shuffled

    def start(self):
        self.outcome = None
        self.shuffle()
        self.on_start()

    def end(self, outcome: str):
        self.outcome = outcome
        self.on_win()

    def move_tile(self, direction, pre_hook, post_hook):
        if self.outcome:
            return
        if not self.selected_tile:
            for t in self.tiles:
                if t.can_move_in(direction, self.tiles):
                    self.selected_tile = t
                    break
        if not self.selected_tile:
            return
        if not self.selected_tile.can_move_in(direction, self.tiles):
            return
        pre_hook(self.selected_tile)
        self.selected_tile.x += direction[0]
        self.selected_tile.y += direction[1]
        post_hook(self.selected_tile)
        if (self.selected_tile.x - self.offset[0]) % 90 == 0 and self.selected_tile.y % 90 == 0:
            self.selected_tile.column = self.selected_tile.x // 90
            self.selected_tile.row = self.selected_tile.y // 90
            self.selected_tile = None
            if all(t.in_place() for t in self.tiles):
                self.end("win")


def pre_move(tile, dev):
    img = Image.new("RGB", (90, 90), "black")
    dev.display_image(img, "center", tile.x, tile.y)


def post_move(tile, dev):
    dev.display_image(tile.image, "center", tile.x, tile.y)


def win_render(dev, game):
    x = random.randint(0, dev.displays["center"]["width"] - 32)
    y = random.randint(0, dev.displays["center"]["height"] - 32)
    crop = game.source.crop((x, y, x + 32, y + 32))
    draw = ImageDraw.Draw(crop)
    font = ImageFont.load_default()
    w, h = draw.textsize("♥", font=font)
    draw.text((16 - w // 2, 16 - h // 2), "♥", fill="red", font=font)
    dev.display_image(crop, "center", x, y)


def main() -> None:
    device = discover()

    win_timer = None

    def schedule_win():
        nonlocal win_timer
        win_timer = threading.Timer(0.1, render_loop)
        win_timer.start()

    def render_loop():
        win_render(device, game)
        schedule_win()

    def stop_win():
        nonlocal win_timer
        if win_timer:
            win_timer.cancel()
            win_timer = None

    def on_connect(info):
        print(f"✅ Connected to {device.type} at {info.get('address')}")

    def on_down(data):
        if data["id"] == 0:
            game.start()

    MOVE_SPEED = 10
    lock = threading.Lock()

    def on_rotate(data):
        if not lock.acquire(blocking=False):
            return
        try:
            direction = [0, 0]
            if str(data["id"]).endswith("T"):
                direction[1] = -data.get("delta", 0) * MOVE_SPEED
            else:
                direction[0] = data.get("delta", 0) * MOVE_SPEED
            game.move_tile(
                direction,
                lambda t: pre_move(t, device),
                lambda t: post_move(t, device),
            )
        finally:
            lock.release()

    device.on("connect", on_connect)
    device.on("down", on_down)
    device.on("rotate", on_rotate)

    Path_this = Path(__file__).resolve().parent
    image_file = "undredal.jpg" if device.displays["center"]["width"] > 360 else "yumi.jpg"
    game = SlidePuzzle(
        Path_this.parent.parent / "examples" / "slide-puzzle" / image_file,
        device.rows,
        device.columns,
        device.visibleX,
    )
    game.init()

    def start_handler():
        stop_win()
        img = Image.new("RGB", (device.displays["center"]["width"], device.displays["center"]["height"]))
        draw = ImageDraw.Draw(img)
        for tile in game.tiles:
            img.paste(tile.image, (tile.x, tile.y))
        device.display_image(img, "center")

    def win_handler():
        schedule_win()
        if "left" in device.displays:
            device.display_image(Image.new("RGB", (device.displays["left"]["width"], device.displays["left"]["height"]), "white"), "left")
        if "right" in device.displays:
            device.display_image(Image.new("RGB", (device.displays["right"]["width"], device.displays["right"]["height"]), "white"), "right")

    game.on_start = start_handler
    game.on_win = win_handler
    game.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_win()
        device.close()


if __name__ == "__main__":
    main()
