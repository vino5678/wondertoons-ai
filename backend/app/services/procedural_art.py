"""Small, deterministic scene illustrations for the local procedural renderer."""
from __future__ import annotations

import math
from pathlib import Path


_SUBJECTS = (
    ("watermelon", ("watermelon",)),
    ("banana", ("banana",)),
    ("orange", ("orange",)),
    ("pineapple", ("pineapple",)),
    ("dinosaur", ("dinosaur", "dino", "t-rex", "trex")),
    ("unicorn", ("unicorn",)),
    ("dragon", ("dragon",)),
    ("elephant", ("elephant",)),
    ("monkey", ("monkey", "chimp")),
    ("frog", ("frog",)),
    ("lion", ("lion",)),
    ("fish", ("fish", "shark", "dolphin")),
    ("whale", ("whale",)),
    ("penguin", ("penguin",)),
    ("butterfly", ("butterfly",)),
    ("bee", ("bee",)),
    ("robot", ("robot", "android")),
    ("rabbit", ("rabbit", "bunny", "hare")),
    ("fox", ("fox",)),
    ("cat", ("cat", "kitten")),
    ("bear", ("bear", "teddy")),
    ("dog", ("dog", "puppy")),
    ("bird", ("bird", "duck", "owl")),
    ("turtle", ("turtle",)),
    ("person", ("person", "human", "child", "girl", "boy", "kid")),
)


_SETTINGS = (
    ("underwater", ("underwater", "under the sea", "coral reef", "ocean floor", "ocean")),
    ("space", ("space", "moon", "planet", "galaxy", "astronaut", "rocket")),
    ("classroom", ("classroom", "school", "teacher", "lesson", "students")),
    ("city", ("city", "town", "street", "traffic", "buildings")),
    ("farm", ("farm", "barn", "tractor", "crops", "farmyard")),
    ("garden", ("garden", "flowers", "flowerbed", "rainbow")),
    ("beach", ("beach", "seaside", "coast", "sandcastle")),
    ("desert", ("desert", "dune", "oasis", "cactus")),
    ("mountains", ("mountain", "hilltop", "cliff", "snowy peak")),
    ("castle", ("castle", "palace", "kingdom", "princess", "knight")),
    ("forest", ("forest", "woods", "woodland", "magical forest", "trees")),
)


_PROPS = (
    ("kite", ("kite", "wind")),
    ("book", ("book", "reading", "story", "learn", "school", "classroom")),
    ("ball", ("ball", "play", "game", "sharing", "share")),
    ("flower", ("flower", "garden", "plant", "seed", "grow")),
    ("apple", ("apple", "fruit", "healthy", "harvest")),
    ("boat", ("boat", "sail", "ship", "ocean", "sea", "beach")),
    ("rocket", ("rocket", "space", "astronaut", "moon", "planet")),
    ("star", ("star", "night", "dream", "wish")),
    ("gift", ("gift", "present", "birthday")),
    ("music", ("music", "dance", "song", "sing")),
)


class Canvas:
    def __init__(self, width: int, height: int, color: tuple[int, int, int]):
        self.width = width
        self.height = height
        self.pixels = bytearray(color) * (width * height)

    def pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 3
            self.pixels[offset:offset + 3] = bytes(color)

    def rectangle(self, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        for y in range(max(0, y0), min(self.height, y1)):
            start = (y * self.width + max(0, x0)) * 3
            end = (y * self.width + min(self.width, x1)) * 3
            if start < end:
                self.pixels[start:end] = bytes(color) * ((end - start) // 3)

    def ellipse(self, cx: int, cy: int, rx: int, ry: int, color: tuple[int, int, int]) -> None:
        if rx <= 0 or ry <= 0:
            return
        y0, y1 = max(0, cy - ry), min(self.height, cy + ry + 1)
        for y in range(y0, y1):
            dy = (y - cy) / ry
            span = int(rx * max(0.0, 1.0 - dy * dy) ** 0.5)
            self.rectangle(cx - span, y, cx + span + 1, y + 1, color)

    def polygon(self, points: list[tuple[int, int]], color: tuple[int, int, int]) -> None:
        if len(points) < 3:
            return
        y0 = max(0, min(y for _, y in points))
        y1 = min(self.height, max(y for _, y in points) + 1)
        for y in range(y0, y1):
            crossings = []
            for index, (x1, py1) in enumerate(points):
                x2, py2 = points[(index + 1) % len(points)]
                if py1 == py2 or not (min(py1, py2) <= y < max(py1, py2)):
                    continue
                crossings.append(int(x1 + (y - py1) * (x2 - x1) / (py2 - py1)))
            crossings.sort()
            for index in range(0, len(crossings) - 1, 2):
                self.rectangle(crossings[index], y, crossings[index + 1] + 1, y + 1, color)

    def apply_style(self, style: str) -> None:
        lowered = style.lower()
        if "storybook" in lowered:
            table = bytes(min(255, int(value * 0.82 + 35)) for value in range(256))
        elif "paper" in lowered:
            table = bytes(max(0, int(value * 0.88 + 10)) for value in range(256))
        else:
            return
        self.pixels[:] = self.pixels.translate(table)

    def save_ppm(self, path: Path) -> None:
        path.write_bytes(f"P6\n{self.width} {self.height}\n255\n".encode("ascii") + self.pixels)


def _match(text: str, choices: tuple[tuple[str, tuple[str, ...]], ...], fallback: str) -> str:
    lowered = text.lower()
    return next((name for name, words in choices if any(word in lowered for word in words)), fallback)


def _draw_tree(canvas: Canvas, x: int, ground: int, scale: int = 1) -> None:
    canvas.rectangle(x - 5 * scale, ground - 46 * scale, x + 5 * scale, ground, (112, 78, 51))
    canvas.ellipse(x, ground - 55 * scale, 25 * scale, 27 * scale, (57, 139, 87))
    canvas.ellipse(x - 15 * scale, ground - 44 * scale, 18 * scale, 20 * scale, (76, 159, 95))


def _draw_house(canvas: Canvas, x: int, ground: int, width: int = 94) -> None:
    left, right, top = x - width // 2, x + width // 2, ground - 83
    canvas.rectangle(left, top, right, ground, (250, 226, 177))
    canvas.polygon([(left - 10, top + 2), (x, top - 52), (right + 10, top + 2)], (191, 91, 90))
    canvas.rectangle(x - 12, ground - 39, x + 12, ground, (127, 82, 62))
    for wx in (left + 13, right - 31):
        canvas.rectangle(wx, top + 18, wx + 19, top + 40, (131, 202, 224))
        canvas.rectangle(wx + 8, top + 18, wx + 10, top + 40, (244, 244, 225))
        canvas.rectangle(wx, top + 28, wx + 19, top + 30, (244, 244, 225))


def _draw_prop(canvas: Canvas, prop: str, x: int, y: int) -> None:
    colors = {
        "kite": (236, 91, 115), "book": (86, 123, 211), "ball": (248, 105, 97),
        "flower": (241, 126, 167), "apple": (220, 65, 59), "boat": (224, 111, 62),
        "rocket": (228, 87, 78), "star": (255, 213, 89), "gift": (151, 104, 210),
        "music": (80, 112, 194),
    }
    color = colors[prop]
    if prop in {"kite", "rocket"}:
        canvas.polygon([(x, y - 28), (x + 20, y), (x, y + 28), (x - 20, y)], color)
        if prop == "kite":
            canvas.polygon([(x, y + 28), (x + 10, y + 46), (x + 4, y + 43),
                            (x, y + 54), (x - 3, y + 42), (x - 10, y + 46)], color)
        else:
            canvas.polygon([(x - 10, y + 13), (x - 22, y + 28), (x - 6, y + 25)], (247, 187, 83))
            canvas.polygon([(x + 10, y + 13), (x + 22, y + 28), (x + 6, y + 25)], (247, 187, 83))
    elif prop == "book":
        canvas.rectangle(x - 25, y - 17, x, y + 17, color)
        canvas.rectangle(x, y - 17, x + 25, y + 17, (111, 151, 225))
        canvas.rectangle(x - 2, y - 15, x + 2, y + 15, (245, 232, 192))
    elif prop == "ball":
        canvas.ellipse(x, y, 23, 23, color)
        canvas.polygon([(x - 20, y - 6), (x - 7, y - 18), (x + 4, y - 7), (x - 3, y + 7)], (255, 225, 118))
    elif prop == "flower":
        canvas.rectangle(x - 2, y, x + 2, y + 31, (75, 151, 84))
        for dx, dy in ((-9, 0), (9, 0), (0, -9), (0, 9)):
            canvas.ellipse(x + dx, y + dy, 8, 8, color)
        canvas.ellipse(x, y, 5, 5, (255, 210, 72))
    elif prop == "apple":
        canvas.ellipse(x, y + 2, 19, 18, color)
        canvas.rectangle(x - 2, y - 22, x + 2, y - 12, (103, 77, 54))
        canvas.ellipse(x + 8, y - 18, 8, 4, (87, 157, 88))
    elif prop == "boat":
        canvas.polygon([(x - 35, y), (x + 35, y), (x + 23, y + 18), (x - 20, y + 18)], color)
        canvas.polygon([(x - 4, y - 30), (x - 4, y - 2), (x + 17, y - 2)], (250, 241, 213))
    elif prop == "star":
        points = []
        for index in range(10):
            angle = -1.5708 + index * 0.6283
            radius = 24 if index % 2 == 0 else 10
            points.append((x + int(radius * math.cos(angle)), y + int(radius * math.sin(angle))))
        canvas.polygon(points, color)
    elif prop == "gift":
        canvas.rectangle(x - 22, y - 14, x + 22, y + 21, color)
        canvas.rectangle(x - 4, y - 14, x + 4, y + 21, (250, 226, 164))
        canvas.rectangle(x - 26, y - 19, x + 26, y - 11, (239, 187, 83))
        canvas.ellipse(x - 8, y - 25, 8, 5, (239, 187, 83))
        canvas.ellipse(x + 8, y - 25, 8, 5, (239, 187, 83))
    else:
        canvas.ellipse(x - 11, y, 12, 15, color)
        canvas.ellipse(x + 11, y, 12, 15, color)
        canvas.rectangle(x - 3, y - 2, x + 3, y + 28, (63, 83, 133))


def _draw_setting(canvas: Canvas, setting: str, index: int) -> None:
    width, height = canvas.width, canvas.height
    ground = 275
    if setting == "underwater":
        canvas.rectangle(0, 0, width, height, (76, 181, 218))
        for bubble_index in range(11):
            x = (41 + bubble_index * 67 + index * 19) % width
            y = 38 + (bubble_index * 43) % 170
            canvas.ellipse(x, y, 5 + bubble_index % 4, 5 + bubble_index % 4, (169, 229, 239))
        canvas.polygon([(0, 312), (180, 290), (344, 325), (500, 286), (640, 313),
                        (640, 360), (0, 360)], (220, 193, 134))
        for x, color in ((82, (235, 113, 111)), (492, (180, 113, 196)), (564, (238, 157, 92))):
            canvas.rectangle(x - 5, 249, x + 5, 316, (67, 157, 102))
            for y in range(230, 280, 15):
                canvas.ellipse(x, y, 14, 24, color)
        return
    if setting == "space":
        canvas.rectangle(0, 0, width, height, (35, 43, 99))
        for star_index in range(32):
            x = (star_index * 97 + index * 23) % width
            y = (star_index * 53 + 31) % 225
            canvas.ellipse(x, y, 2 + star_index % 2, 2 + star_index % 2, (255, 247, 201))
        canvas.ellipse(522, 220, 91, 27, (94, 104, 174))
        canvas.ellipse(522, 210, 74, 16, (116, 132, 200))
        canvas.ellipse(112, 174, 58, 22, (179, 123, 176))
        return
    if setting == "classroom":
        canvas.rectangle(0, 0, width, height, (248, 225, 177))
        canvas.rectangle(78, 45, 566, 207, (58, 125, 107))
        canvas.rectangle(69, 207, 575, 218, (147, 92, 60))
        canvas.ellipse(325, 113, 49, 43, (253, 225, 161))
        canvas.rectangle(288, 112, 362, 117, (91, 151, 126))
        canvas.rectangle(131, 265, 514, 280, (163, 111, 72))
        for x in (166, 467):
            canvas.rectangle(x, 280, x + 10, 334, (116, 83, 61))
        return
    if setting == "city":
        canvas.rectangle(0, 0, width, height, (150, 210, 244))
        for building, color, floors in ((55, (239, 174, 108), 3), (190, (145, 164, 211), 4),
                                        (350, (244, 204, 128), 3), (488, (145, 187, 171), 4)):
            top = ground - floors * 37
            canvas.rectangle(building, top, building + 98, ground, color)
            for row in range(floors):
                for col in range(2):
                    x = building + 16 + col * 44
                    y = top + 12 + row * 31
                    canvas.rectangle(x, y, x + 18, y + 19, (178, 224, 232))
        canvas.rectangle(0, ground, width, height, (105, 112, 128))
        canvas.rectangle(0, 328, width, 331, (240, 211, 114))
        return
    if setting == "farm":
        canvas.rectangle(0, 0, width, height, (151, 211, 241))
        canvas.polygon([(0, 235), (132, 179), (242, 234), (403, 164), (640, 235),
                        (640, 360), (0, 360)], (142, 190, 111))
        canvas.polygon([(0, 284), (182, 243), (321, 284), (473, 235), (640, 287),
                        (640, 360), (0, 360)], (101, 161, 91))
        _draw_house(canvas, 494, 293, 112)
        canvas.rectangle(0, 326, width, height, (87, 144, 76))
        return
    if setting == "garden":
        canvas.rectangle(0, 0, width, height, (151, 211, 246))
        canvas.ellipse(520, 66, 28, 28, (255, 220, 123))
        canvas.polygon([(0, 223), (110, 160), (229, 226), (370, 155), (520, 225), (640, 175),
                        (640, 360), (0, 360)], (143, 195, 132))
        canvas.polygon([(0, 281), (140, 225), (272, 286), (430, 215), (550, 280), (640, 239),
                        (640, 360), (0, 360)], (88, 164, 103))
        for x in (104, 276, 472):
            _draw_tree(canvas, x, 296)
        return
    if setting in {"beach", "desert"}:
        sky = (124, 207, 240) if setting == "beach" else (245, 183, 105)
        canvas.rectangle(0, 0, width, height, sky)
        canvas.ellipse(520, 70, 30, 30, (255, 222, 132))
        if setting == "beach":
            canvas.rectangle(0, 245, width, height, (64, 176, 211))
            canvas.polygon([(0, 270), (160, 248), (300, 273), (480, 248), (640, 269),
                            (640, 360), (0, 360)], (245, 218, 163))
            for y in (287, 307):
                canvas.rectangle(0, y, width, y + 3, (239, 250, 233))
        else:
            canvas.polygon([(0, 240), (125, 181), (280, 253), (458, 185), (640, 247),
                            (640, 360), (0, 360)], (224, 152, 86))
            canvas.rectangle(0, 295, width, height, (240, 186, 106))
            for x in (84, 551):
                canvas.rectangle(x - 3, 263, x + 3, 327, (56, 128, 86))
                canvas.ellipse(x, 255, 24, 7, (75, 153, 90))
                canvas.ellipse(x - 18, 267, 7, 21, (75, 153, 90))
        return
    if setting == "mountains":
        canvas.rectangle(0, 0, width, height, (142, 205, 241))
        canvas.polygon([(0, 275), (138, 80), (276, 275)], (117, 150, 189))
        canvas.polygon([(220, 272), (422, 49), (640, 277)], (93, 131, 177))
        canvas.polygon([(103, 130), (138, 80), (174, 132), (148, 121), (137, 137)], (247, 248, 237))
        canvas.polygon([(374, 102), (422, 49), (476, 105), (443, 88), (421, 113)], (247, 248, 237))
        canvas.polygon([(0, 285), (150, 251), (330, 286), (484, 242), (640, 282),
                        (640, 360), (0, 360)], (104, 160, 111))
        return
    if setting == "castle":
        canvas.rectangle(0, 0, width, height, (160, 211, 244))
        canvas.rectangle(113, 142, 527, 304, (205, 190, 167))
        for x in (132, 238, 396, 502):
            canvas.rectangle(x, 93, x + 53, 302, (222, 207, 180))
            canvas.polygon([(x - 5, 96), (x + 26, 52), (x + 58, 96)], (177, 86, 92))
            canvas.rectangle(x + 12, 118, x + 39, 157, (95, 112, 150))
        canvas.rectangle(283, 228, 357, 304, (108, 83, 79))
        canvas.rectangle(0, 304, width, height, (105, 167, 91))
        return
    if setting == "forest":
        canvas.rectangle(0, 0, width, height, (153, 211, 235))
        canvas.polygon([(0, 254), (117, 190), (240, 258), (380, 178), (515, 250), (640, 189),
                        (640, 360), (0, 360)], (105, 165, 109))
        canvas.rectangle(0, 280, width, height, (82, 150, 91))
        for x, scale in ((65, 1), (203, 1), (433, 1), (584, 1)):
            _draw_tree(canvas, x, 301, scale)
        return
    # Clear day fallback for topics without a recognized setting.
    canvas.rectangle(0, 0, width, height, (155, 211, 246))
    canvas.ellipse(520, 71, 27, 27, (255, 213, 111))
    canvas.polygon([(0, 230), (105, 159), (220, 229), (350, 158), (510, 235), (640, 174),
                    (640, 360), (0, 360)], (148, 202, 137))
    canvas.polygon([(0, 284), (130, 221), (250, 286), (389, 218), (520, 288), (640, 236),
                    (640, 360), (0, 360)], (91, 177, 125))


def _draw_creature(canvas: Canvas, kind: str, x: int, y: int, scale: float = 1.0,
                   color_override: tuple[int, int, int] | None = None,
                   clothing_color: tuple[int, int, int] | None = None) -> None:
    """Add prompt-matched scenery characters in the illustration, not only as the moving mascot."""
    sizes = (int(24 * scale), int(18 * scale))
    colors = {
        "rabbit": (240, 226, 211), "fox": (236, 126, 63), "cat": (239, 177, 92),
        "bear": (159, 109, 73), "dog": (204, 157, 102), "bird": (255, 207, 72),
        "turtle": (82, 171, 120), "dinosaur": (84, 166, 111), "unicorn": (244, 215, 237),
        "dragon": (98, 172, 121), "elephant": (139, 158, 190), "monkey": (171, 117, 81),
        "frog": (100, 183, 99), "lion": (221, 163, 72), "fish": (244, 139, 91),
        "whale": (103, 148, 201), "penguin": (72, 84, 108), "butterfly": (183, 113, 211),
        "bee": (242, 194, 64), "robot": (117, 165, 193), "person": (214, 151, 119),
        "watermelon": (50, 148, 84), "banana": (249, 211, 72), "orange": (245, 151, 55),
        "pineapple": (194, 163, 67),
    }
    body = color_override or colors[kind]
    rx, ry = sizes
    if kind == "watermelon":
        canvas.ellipse(x, y, rx, ry, (50, 148, 84))
        canvas.ellipse(x, y, int(rx * 0.72), int(ry * 0.72), (242, 91, 96))
        for dx in (-9, 0, 9):
            canvas.ellipse(x + dx, y - 5, 2, 3, (54, 71, 52))
        return
    if kind == "banana":
        canvas.polygon([(x - 18, y - 19), (x - 4, y - 24), (x + 17, y - 10),
                        (x + 21, y + 9), (x + 6, y + 24), (x - 13, y + 17),
                        (x + 8, y + 12), (x + 13, y + 1), (x + 2, y - 10)], (249, 211, 72))
        canvas.ellipse(x + 2, y - 3, 2, 2, (57, 54, 48))
        return
    if kind == "orange":
        canvas.ellipse(x, y, rx, ry, (245, 151, 55))
        canvas.ellipse(x + rx // 2, y - ry + 4, 8, 4, (83, 158, 91))
        canvas.ellipse(x + rx // 2, y - ry + 3, 2, 2, (67, 125, 75))
        canvas.ellipse(x + rx // 3, y - 4, 2, 2, (53, 55, 58))
        return
    if kind in {"fish", "whale"}:
        canvas.ellipse(x, y, rx, ry, body)
        canvas.polygon([(x - rx, y), (x - rx - 15, y - 13), (x - rx - 15, y + 13)], body)
        canvas.ellipse(x + rx // 2, y - 4, 2, 2, (39, 47, 61))
        return
    if kind == "butterfly":
        canvas.ellipse(x - 13, y - 7, 12, 15, body)
        canvas.ellipse(x + 13, y - 7, 12, 15, (239, 168, 95))
        canvas.rectangle(x - 2, y - 4, x + 2, y + 15, (90, 73, 78))
        return
    if kind == "bee":
        canvas.ellipse(x, y, rx, ry, body)
        canvas.rectangle(x - 10, y - ry + 2, x - 6, y + ry - 2, (58, 55, 51))
        canvas.rectangle(x + 4, y - ry + 2, x + 8, y + ry - 2, (58, 55, 51))
        canvas.ellipse(x - 9, y - ry - 7, 8, 5, (238, 249, 245))
        canvas.ellipse(x + 9, y - ry - 7, 8, 5, (238, 249, 245))
        return
    if kind == "person":
        head_radius = int(12 * scale)
        skin = color_override or (214, 151, 119)
        hair = (59, 43, 39)
        shirt = clothing_color or (85, 133, 191)
        canvas.rectangle(int(x - 17 * scale), y + ry + 10, int(x - 8 * scale), y + ry + 31,
                         (65, 79, 115))
        canvas.rectangle(int(x + 8 * scale), y + ry + 10, int(x + 17 * scale), y + ry + 31,
                         (65, 79, 115))
        canvas.ellipse(x, y - ry - 9, head_radius + 2, head_radius + 3, hair)
        canvas.ellipse(x, y - ry - 10, head_radius, head_radius, skin)
        canvas.ellipse(x - 3, y - ry - 15, max(2, head_radius - 3), 4, hair)
        canvas.rectangle(int(x - 14 * scale), y - ry + 1, int(x + 14 * scale), y + ry + 14, shirt)
        canvas.polygon([(x - 6, y - ry + 1), (x, y - ry + 9), (x + 6, y - ry + 1)], (247, 239, 220))
        canvas.ellipse(x - 4, y - ry - 10, max(1, int(2 * scale)), max(2, int(3 * scale)), (255, 255, 250))
        canvas.ellipse(x + 4, y - ry - 10, max(1, int(2 * scale)), max(2, int(3 * scale)), (255, 255, 250))
        canvas.ellipse(x - 4, y - ry - 10, max(1, int(scale)), max(2, int(2 * scale)), (55, 49, 51))
        canvas.ellipse(x + 4, y - ry - 10, max(1, int(scale)), max(2, int(2 * scale)), (55, 49, 51))
        canvas.ellipse(x - 3, y - ry - 11, 1, 1, (255, 255, 255))
        canvas.ellipse(x + 5, y - ry - 11, 1, 1, (255, 255, 255))
        canvas.ellipse(x, y - ry - 5, 2, 1, (171, 91, 93))
        return
    # Layered limbs, a shaded body and a soft highlight make the silhouette less
    # like a flat symbol while keeping the drawing fast and fully local.
    shadow = tuple(max(0, int(channel * 0.72)) for channel in body)
    highlight = tuple(min(255, int(channel * 1.19 + 10)) for channel in body)
    canvas.ellipse(x - rx // 2, y + ry - 1, max(3, rx // 4), max(4, ry // 2), shadow)
    canvas.ellipse(x + rx // 2, y + ry - 1, max(3, rx // 4), max(4, ry // 2), shadow)
    canvas.ellipse(x, y, rx, ry, body)
    canvas.ellipse(x - rx // 3, y - ry // 3, max(2, rx // 3), max(2, ry // 3), highlight)
    head_x, head_y = x, y - ry
    canvas.ellipse(head_x, head_y - ry // 2, int(rx * 0.83), int(ry * 0.83), body)
    canvas.ellipse(head_x - rx // 3, head_y - ry // 2, max(3, rx // 5), max(4, ry // 4), (255, 255, 247))
    canvas.ellipse(head_x + rx // 3, head_y - ry // 2, max(3, rx // 5), max(4, ry // 4), (255, 255, 247))
    canvas.ellipse(head_x - rx // 3, head_y - ry // 2, max(2, rx // 9), max(3, ry // 6), (42, 44, 52))
    canvas.ellipse(head_x + rx // 3, head_y - ry // 2, max(2, rx // 9), max(3, ry // 6), (42, 44, 52))
    canvas.ellipse(head_x - rx // 3 - 1, head_y - ry // 2 - 2, 1, 1, (255, 255, 255))
    canvas.ellipse(head_x + rx // 3 - 1, head_y - ry // 2 - 2, 1, 1, (255, 255, 255))
    muzzle_color = tuple(min(255, int(channel * 0.65 + 255 * 0.35)) for channel in body)
    if kind in {"rabbit", "fox", "cat", "bear", "dog", "lion"}:
        canvas.ellipse(head_x, head_y + 1, max(4, rx // 3), max(3, ry // 5), muzzle_color)
        canvas.ellipse(head_x, head_y, 2, 2, (103, 67, 73))
        canvas.ellipse(head_x - rx // 2, head_y + 2, max(2, rx // 7), max(1, ry // 10), (239, 151, 156))
        canvas.ellipse(head_x + rx // 2, head_y + 2, max(2, rx // 7), max(1, ry // 10), (239, 151, 156))
    canvas.ellipse(head_x - rx // 2, head_y + 5, max(1, rx // 8), max(1, ry // 8), shadow)
    canvas.ellipse(head_x + rx // 2, head_y + 5, max(1, rx // 8), max(1, ry // 8), shadow)
    if kind in {"rabbit", "fox", "cat", "unicorn"}:
        canvas.ellipse(head_x - rx // 2, head_y - ry - 8, 5, 13 if kind == "rabbit" else 7, body)
        canvas.ellipse(head_x + rx // 2, head_y - ry - 8, 5, 13 if kind == "rabbit" else 7, body)
    if kind == "unicorn":
        canvas.polygon([(head_x, head_y - ry - 9), (head_x - 5, head_y - ry - 22),
                        (head_x + 6, head_y - ry - 12)], (248, 205, 93))
    if kind == "elephant":
        canvas.ellipse(head_x - rx, head_y - 2, 9, 11, (167, 180, 203))
        canvas.rectangle(head_x - 3, head_y, head_x + 4, head_y + 16, (167, 180, 203))
    if kind == "dinosaur":
        canvas.polygon([(x - rx, y - 6), (x - rx - 19, y + 2), (x - rx, y + 8)], body)
        for spike in range(3):
            sx = x - 8 + spike * 10
            canvas.polygon([(sx, y - ry + 1), (sx + 5, y - ry - 8), (sx + 10, y - ry + 1)], (240, 192, 83))
    if kind == "robot":
        canvas.rectangle(head_x - 11, head_y - ry - 14, head_x + 11, head_y - ry + 1, (117, 165, 193))
        canvas.ellipse(head_x - 5, head_y - ry - 9, 2, 2, (248, 227, 111))
        canvas.ellipse(head_x + 5, head_y - ry - 9, 2, 2, (248, 227, 111))
    if kind == "lion":
        canvas.ellipse(head_x, head_y - ry // 2, int(rx * 1.1), int(ry * 1.1), (210, 138, 52))
        canvas.ellipse(head_x, head_y - ry // 2, int(rx * 0.7), int(ry * 0.7), body)


_NAMED_COLORS = {
    "red": (201, 83, 85), "orange": (225, 132, 61), "yellow": (221, 180, 73),
    "green": (95, 156, 102), "blue": (100, 143, 190), "purple": (153, 119, 182),
    "pink": (218, 141, 164), "brown": (145, 99, 72), "black": (75, 73, 82),
    "white": (226, 220, 207), "gray": (156, 158, 166), "grey": (156, 158, 166),
    "cream": (221, 206, 173), "golden": (206, 165, 72), "silver": (161, 177, 185),
}


def _creature_default_color(kind: str) -> tuple[int, int, int]:
    return {
        "rabbit": (240, 226, 211), "fox": (236, 126, 63), "cat": (239, 177, 92),
        "bear": (159, 109, 73), "dog": (204, 157, 102), "bird": (255, 207, 72),
        "turtle": (82, 171, 120), "dinosaur": (84, 166, 111), "unicorn": (244, 215, 237),
        "dragon": (98, 172, 121), "elephant": (139, 158, 190), "monkey": (171, 117, 81),
        "frog": (100, 183, 99), "lion": (221, 163, 72), "fish": (244, 139, 91),
        "whale": (103, 148, 201), "penguin": (72, 84, 108), "butterfly": (183, 113, 211),
        "bee": (242, 194, 64), "robot": (117, 165, 193), "person": (214, 151, 119),
        "watermelon": (50, 148, 84), "banana": (249, 211, 72), "orange": (245, 151, 55),
        "pineapple": (194, 163, 67),
    }[kind]


def _prompt_color(text: str, kind: str, default: tuple[int, int, int]) -> tuple[int, int, int]:
    if kind in {"watermelon", "banana", "orange", "pineapple"}:
        return default
    aliases = next((words for name, words in _SUBJECTS if name == kind), (kind,))
    subject_positions = [text.find(alias) for alias in aliases if text.find(alias) >= 0]
    if not subject_positions:
        return default
    subject_position = min(subject_positions)
    color_positions = [
        (text.find(name), color) for name, color in _NAMED_COLORS.items()
        if text.find(name) >= 0 and abs(text.find(name) - subject_position) <= 48
    ]
    if not color_positions:
        return default
    return min(color_positions, key=lambda item: abs(item[0] - subject_position))[1]


def _prompt_clothing_color(text: str) -> tuple[int, int, int] | None:
    garments = ("shirt", "dress", "jacket", "scarf", "vest", "overalls", "coat", "sweater")
    positions = [text.find(garment) for garment in garments if text.find(garment) >= 0]
    if not positions:
        return None
    garment_position = min(positions)
    color_positions = [
        (text.find(name), color) for name, color in _NAMED_COLORS.items()
        if text.find(name) >= 0 and 0 <= garment_position - text.find(name) <= 24
    ]
    return min(color_positions, key=lambda item: item[0])[1] if color_positions else None


def _draw_setting_details(canvas: Canvas, text: str, index: int) -> None:
    lowered = text.lower()
    setting = _match(lowered, _SETTINGS, "meadow")
    prop = _match(lowered, _PROPS, "")
    if prop:
        prop_x = 92 + (index * 137) % 455
        _draw_prop(canvas, prop, prop_x, 236 if setting in {"space", "underwater"} else 267)

    if setting == "meadow":
        for flower_index in range(9):
            x = 28 + ((flower_index * 79 + index * 31) % 585)
            y = 326 + ((flower_index * 13) % 24)
            petal = (255, 229, 146) if flower_index % 2 else (255, 206, 218)
            canvas.ellipse(x, y, 5, 5, petal)
            canvas.ellipse(x, y, 2, 2, (245, 174, 77))

    creatures = []
    for kind, words in _SUBJECTS:
        if any(word in lowered for word in words):
            creatures.append(kind)
    if any(word in lowered for word in ("children", "child", "friends", "people", "girl", "boy")):
        creatures.append("person")
    for creature_index, kind in enumerate(dict.fromkeys(creatures[:5])):
        creature_x = 398 + creature_index * 54
        creature_y = 292 - (creature_index % 2) * 25
        _draw_creature(canvas, kind, creature_x, creature_y, 0.56 if creature_index else 0.72,
                       _prompt_color(lowered, kind, _creature_default_color(kind)),
                       _prompt_clothing_color(lowered))

    if any(word in lowered for word in ("night", "evening", "stars")) and setting not in {"space", "underwater"}:
        for star_index in range(12):
            x = (star_index * 59 + index * 17) % canvas.width
            y = 25 + (star_index * 29) % 125
            canvas.ellipse(x, y, 2, 2, (255, 246, 196))
    if any(word in lowered for word in ("rain", "rainy", "storm")):
        for rain_index in range(28):
            x = (rain_index * 43 + index * 13) % canvas.width
            y = (rain_index * 61) % 205
            canvas.polygon([(x, y), (x + 2, y + 10), (x - 1, y + 8)], (114, 168, 204))


def make_background(scene_text: str, style: str, index: int, path: Path) -> None:
    width, height = 640, 360
    setting = _match(scene_text, _SETTINGS, "meadow")
    background = (43, 52, 113) if setting == "space" else (85, 174, 212) if setting == "underwater" \
        else (155, 211, 246)
    canvas = Canvas(width, height, background)
    _draw_setting(canvas, setting, index)
    _draw_setting_details(canvas, scene_text, index)
    canvas.apply_style(style)
    canvas.save_ppm(path)


def mascot_kind(prompt: str) -> str:
    lowered = prompt.lower()
    matches = [
        (lowered.find(term), kind)
        for kind, terms in _SUBJECTS
        for term in terms
        if lowered.find(term) >= 0
    ]
    return min(matches)[1] if matches else "person"


def make_mascot(prompt: str, path: Path) -> str:
    kind = mascot_kind(prompt)
    canvas = Canvas(180, 220, (0, 255, 0))
    colors = {
        "rabbit": (241, 228, 218), "fox": (239, 132, 64), "cat": (243, 181, 95),
        "bear": (159, 109, 73), "dog": (205, 159, 104), "bird": (255, 211, 76),
        "turtle": (82, 171, 120), "dinosaur": (84, 166, 111), "unicorn": (244, 215, 237),
        "dragon": (98, 172, 121), "elephant": (139, 158, 190), "monkey": (171, 117, 81),
        "frog": (100, 183, 99), "lion": (221, 163, 72), "fish": (244, 139, 91),
        "whale": (103, 148, 201), "penguin": (72, 84, 108), "butterfly": (183, 113, 211),
        "bee": (242, 194, 64), "robot": (117, 165, 193), "person": (214, 151, 119),
        "watermelon": (50, 148, 84), "banana": (249, 211, 72), "orange": (245, 151, 55),
        "pineapple": (194, 163, 67),
    }
    body = colors[kind]
    outline = (115, 85, 73)
    if kind in {"fish", "whale", "butterfly", "bee", "watermelon", "banana", "orange"}:
        _draw_creature(canvas, kind, 88, 103, 1.5)
    elif kind == "person":
        _draw_creature(canvas, kind, 88, 107, 1.65)
    else:
        lowered = prompt.lower()
        _draw_creature(canvas, kind, 88, 120, 1.55, _prompt_color(lowered, kind, body),
                       _prompt_clothing_color(lowered))
    if kind == "fox":
        canvas.polygon([(128, 171), (165, 145), (157, 190), (134, 192)], outline)
        canvas.polygon([(137, 171), (157, 154), (151, 181)], (255, 244, 222))
    elif kind == "bird":
        canvas.ellipse(129, 152, 25, 13, (255, 176, 66))
        canvas.polygon([(128, 85), (149, 93), (128, 101)], (239, 132, 64))
    elif kind == "turtle":
        canvas.ellipse(88, 162, 46, 29, (57, 111, 86))
        canvas.ellipse(88, 158, 39, 24, (93, 160, 112))
        canvas.ellipse(130, 144, 18, 16, body)
    elif kind == "penguin":
        canvas.ellipse(88, 150, 35, 51, body)
        canvas.ellipse(88, 157, 22, 35, (246, 241, 223))
        canvas.polygon([(118, 121), (143, 131), (117, 137)], (245, 161, 73))
    elif kind == "dragon":
        canvas.polygon([(58, 145), (28, 104), (75, 122)], (106, 193, 143))
        canvas.polygon([(115, 145), (149, 104), (126, 158)], (106, 193, 143))
        canvas.polygon([(78, 48), (88, 28), (96, 50)], (247, 183, 77))
    elif kind == "dinosaur":
        canvas.polygon([(40, 153), (14, 169), (45, 172)], body)
        for spike in range(5):
            sx = 57 + spike * 15
            canvas.polygon([(sx, 132), (sx + 7, 112), (sx + 14, 135)], (245, 186, 76))
    elif kind == "unicorn":
        canvas.polygon([(88, 47), (75, 9), (101, 43)], (249, 203, 101))
        canvas.ellipse(69, 110, 9, 4, (226, 133, 174))
        canvas.ellipse(107, 110, 9, 4, (226, 133, 174))

    canvas.save_ppm(path)
    return kind


def motion_kind(prompt: str) -> str:
    lowered = prompt.lower()
    if any(word in lowered for word in ("freeze", "freezes", "frozen")):
        return "freeze"
    if any(word in lowered for word in ("fly", "flying", "soar", "glide", "float", "rocket", "space")):
        return "fly"
    if any(word in lowered for word in ("swim", "swimming", "underwater", "ocean", "sea")):
        return "swim"
    if any(word in lowered for word in ("dance", "dancing", "sing", "celebrate", "party")):
        return "dance"
    if any(word in lowered for word in ("jump", "jumping", "hop", "bounce")):
        return "jump"
    if any(word in lowered for word in ("sleep", "sleeping", "rest", "calm", "quiet")):
        return "rest"
    return "walk"
