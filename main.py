#!/usr/bin/env python3
"""NIMBARA - City Above the Clouds.

A travel poster for a place that does not exist, drawn entirely with the
Python standard library (zlib + struct PNG writer, no fonts, no network).
Writes one 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png (or /output).
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
INK = (16, 18, 46)          # deep indigo, title band
GOLD = (246, 196, 83)       # title gold
CREAM = (253, 238, 205)     # pale cream
PEACH = (250, 196, 130)
ROSE = (214, 110, 118)
VIOLET = (96, 62, 128)
DUSK = (30, 34, 80)
TEAL = (36, 90, 96)
LEAF = (74, 138, 92)
ROCK = (74, 52, 84)
ROCK_DARK = (52, 36, 62)
WOOD = (146, 90, 52)
LANTERN = (255, 190, 70)
SUN = (255, 216, 130)

# ------------------------------------------------------- 5x7 vector font
# Each glyph is 7 rows of 5 bits, '#' = filled.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "00100", "00100"),
}


def text_width(text, scale):
    """Pixel width of text drawn at the given scale (1px gap per glyph)."""
    return len(text) * 6 * scale - scale


def draw_text(canvas, text, x, y, scale, color):
    """Draw text with the 5x7 vector font; (x, y) is the top-left corner."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch.upper(), FONT[' '])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '1':
                    canvas.fill_rect(cx + col * scale, y + row * scale,
                                     scale, scale, color)
        cx += 6 * scale
    return cx


def draw_text_centered(canvas, text, cx, y, scale, color):
    draw_text(canvas, text, cx - text_width(text, scale) // 2, y, scale, color)


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.w, int(x) + int(w))
        y1 = min(self.h, int(y) + int(h))
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = color
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b

    def vgrad(self, y0, y1, stops):
        """Vertical gradient; stops = [(pos 0..1, (r,g,b)), ...] sorted."""
        for y in range(max(0, y0), min(self.h, y1)):
            t = (y - y0) / max(1, (y1 - y0 - 1))
            for k in range(len(stops) - 1):
                p0, c0 = stops[k]
                p1, c1 = stops[k + 1]
                if p0 <= t <= p1:
                    f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                    color = (int(c0[0] + (c1[0] - c0[0]) * f),
                             int(c0[1] + (c1[1] - c0[1]) * f),
                             int(c0[2] + (c1[2] - c0[2]) * f))
                    break
            else:
                color = stops[-1][1]
            self.fill_rect(0, y, self.w, 1, color)

    def circle(self, cx, cy, r, color):
        r = int(r)
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def ellipse(self, cx, cy, rx, ry, color):
        rx = int(rx)
        ry = int(ry)
        for dy in range(-ry, ry + 1):
            f = 1.0 - (dy * dy) / float(ry * ry)
            dx = int(rx * math.sqrt(max(0.0, f)))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def polygon(self, points, color):
        """Scanline fill of a simple polygon."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h - 1, int(max(ys)))
        n = len(points)
        for y in range(y0, y1 + 1):
            xs = []
            for k in range(n):
                x1, y1p = points[k]
                x2, y2p = points[(k + 1) % n]
                if y1p == y2p:
                    continue
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    t = (y - y1p) / (y2p - y1p)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = int(math.ceil(xs[k]))
                xb = int(math.floor(xs[k + 1]))
                if xb >= xa:
                    self.fill_rect(xa, y, xb - xa + 1, 1, color)

    def thick_line(self, x0, y0, x1, y1, width, color):
        steps = int(max(abs(x1 - x0), abs(y1 - y0), 1)) + 1
        r = max(1, width // 2)
        for s in range(steps + 1):
            t = s / steps
            self.circle(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t),
                        r, color)

    def quad_bezier(self, p0, p1, p2, width, color, step=0.004):
        t = 0.0
        while t <= 1.0:
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
            self.circle(int(x), int(y), max(1, width // 2), color)
            t += step

    def quad_point(self, p0, p1, p2, t):
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        return (x, y)


def write_png(path, canvas):
    """Encode the canvas as a 24-bit RGB PNG (filter 0, zlib level 9)."""
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * stride:(y + 1) * stride]
    data = zlib.compress(bytes(raw), 9)

    def chunk(tag, payload):
        out = struct.pack(">I", len(payload)) + tag + payload
        out += struct.pack(">I", zlib.crc32(tag + payload) & 0xffffffff)
        return out

    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", data)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ------------------------------------------------------------ scene pieces
def draw_stars(cv):
    """Deterministic star field in the upper sky (fixed pseudo-random)."""
    seed = 1234567
    for i in range(90):
        seed = (seed * 1103515245 + 12345) & 0x7fffffff
        x = 30 + seed % 964
        seed = (seed * 1103515245 + 12345) & 0x7fffffff
        y = 20 + seed % 260
        seed = (seed * 1103515245 + 12345) & 0x7fffffff
        s = 1 + seed % 2
        bright = 200 + seed % 55
        cv.fill_rect(x, y, s, s, (bright, bright, min(255, bright + 20)))


def draw_sun(cv):
    # glow rings, then the disc itself
    cv.circle(712, 520, 150, (250, 168, 108))
    cv.circle(712, 520, 122, (252, 186, 112))
    cv.circle(712, 520, 88, SUN)
    cv.circle(712, 520, 62, (255, 232, 160))


def draw_mountains(cv):
    # far violet ridge behind the cloud sea
    cv.polygon([(0, 660), (90, 585), (170, 640), (260, 570), (350, 645),
                (430, 600), (520, 655), (610, 590), (700, 650),
                (790, 585), (880, 650), (960, 600), (1024, 645),
                (1024, 700), (0, 700)], (58, 44, 92))
    cv.polygon([(0, 680), (120, 625), (240, 675), (380, 630), (520, 680),
                (660, 635), (800, 680), (920, 640), (1024, 675),
                (1024, 720), (0, 720)], (44, 34, 76))


def draw_cloud_puff(cv, cx, cy, scale, color):
    cv.ellipse(cx, cy, int(90 * scale), int(30 * scale), color)
    cv.ellipse(cx - int(62 * scale), cy + int(10 * scale),
               int(58 * scale), int(22 * scale), color)
    cv.ellipse(cx + int(64 * scale), cy + int(10 * scale),
               int(60 * scale), int(22 * scale), color)
    cv.ellipse(cx - int(28 * scale), cy - int(16 * scale),
               int(52 * scale), int(22 * scale), color)
    cv.ellipse(cx + int(30 * scale), cy - int(14 * scale),
               int(48 * scale), int(20 * scale), color)


def draw_cloud_sea(cv):
    # warm cloud ocean the islands float above
    cv.vgrad(640, 806, [(0.0, (250, 214, 158)), (0.55, (246, 190, 138)),
                        (1.0, (232, 158, 118))])
    for (cx, cy, s) in [(140, 668, 1.15), (330, 700, 1.35), (520, 672, 1.1),
                        (700, 706, 1.4), (880, 672, 1.2), (60, 720, 1.0),
                        (980, 716, 1.05), (430, 730, 1.2), (620, 748, 1.1),
                        (240, 752, 1.15), (830, 752, 1.0)]:
        draw_cloud_puff(cv, cx, cy, s, (253, 238, 205))
    for (cx, cy, s) in [(200, 700, 0.9), (620, 690, 0.95), (940, 700, 0.85),
                        (380, 760, 0.9), (760, 764, 0.9)]:
        draw_cloud_puff(cv, cx, cy, s, (255, 248, 226))


def draw_house(cv, x, y, w, h, wall, roof):
    """A little house: walls, pitched roof, door, two lit windows."""
    cv.fill_rect(x, y, w, h, wall)
    cv.polygon([(x - 4, y), (x + w // 2, y - h // 2), (x + w + 4, y)], roof)
    cv.fill_rect(x + w // 2 - 4, y + h - 16, 8, 16, (52, 36, 62))
    cv.fill_rect(x + 5, y + 8, 9, 9, LANTERN)
    cv.fill_rect(x + w - 14, y + 8, 9, 9, LANTERN)


def draw_dome(cv, x, y, w, h, wall, dome):
    cv.fill_rect(x, y, w, h, wall)
    cv.ellipse(x + w // 2, y, w // 2 + 2, h // 2, dome)
    cv.fill_rect(x + w // 2 - 1, y - h // 2 - 8, 2, 8, GOLD)
    cv.circle(x + w // 2, y - h // 2 - 10, 3, LANTERN)
    cv.fill_rect(x + 5, y + 10, 8, 10, LANTERN)
    cv.fill_rect(x + w - 13, y + 10, 8, 10, LANTERN)


def draw_island(cv, cx, top_y, half_w, depth, grass, rock):
    """Floating rock island: grassy top, tapering rocky underside."""
    cv.polygon([(cx - half_w, top_y), (cx + half_w, top_y),
                (cx + int(half_w * 0.62), top_y + int(depth * 0.55)),
                (cx + int(half_w * 0.22), top_y + depth),
                (cx - int(half_w * 0.18), top_y + depth),
                (cx - int(half_w * 0.58), top_y + int(depth * 0.5))], rock)
    cv.ellipse(cx, top_y + 4, half_w, 16, grass)
    # rocky strata lines
    cv.thick_line(cx - int(half_w * 0.7), top_y + int(depth * 0.35),
                  cx + int(half_w * 0.55), top_y + int(depth * 0.42), 3,
                  ROCK_DARK)
    cv.thick_line(cx - int(half_w * 0.4), top_y + int(depth * 0.62),
                  cx + int(half_w * 0.3), top_y + int(depth * 0.68), 3,
                  ROCK_DARK)
    # tiny hanging vines / moss
    for dx in (-int(half_w * 0.5), -int(half_w * 0.1), int(half_w * 0.35)):
        cv.thick_line(cx + dx, top_y + 12, cx + dx, top_y + 30, 3, LEAF)


def draw_left_island(cv):
    cx, top = 238, 452
    draw_island(cv, cx, top, 150, 120, LEAF, ROCK)
    draw_house(cv, cx - 118, top - 52, 52, 52, CREAM, (178, 62, 62))
    draw_house(cv, cx - 52, top - 44, 46, 44, (232, 210, 170), TEAL)
    draw_dome(cv, cx + 12, top - 58, 54, 58, CREAM, (72, 130, 160))
    draw_house(cv, cx + 78, top - 40, 42, 40, (240, 214, 150), (178, 62, 62))
    # flag on the dome house
    cv.thick_line(cx + 66, top - 58, cx + 66, top - 92, 3, WOOD)
    cv.polygon([(cx + 66, top - 92), (cx + 92, top - 84), (cx + 66, top - 76)],
               (214, 80, 70))
    # soft shadow on the cloud sea below
    cv.ellipse(cx, 700, 150, 12, (232, 172, 132))


def draw_tower(cv, x, base_y, w, h):
    """The Skyharbour: tall spire with a glowing beacon."""
    cv.fill_rect(x, base_y - h, w, h, (240, 226, 190))
    cv.polygon([(x - 3, base_y - h), (x + w // 2, base_y - h - 46),
                (x + w + 3, base_y - h)], (178, 62, 62))
    cv.fill_rect(x + w // 2 - 2, base_y - h - 58, 4, 14, GOLD)
    cv.circle(x + w // 2, base_y - h - 62, 7, LANTERN)
    # beacon glow + rays
    cv.circle(x + w // 2, base_y - h - 62, 12, (255, 214, 120))
    cv.circle(x + w // 2, base_y - h - 62, 18, (250, 190, 110))
    cv.thick_line(x + w // 2, base_y - h - 62, x + w // 2 - 62,
                  base_y - h - 84, 3, (255, 220, 140))
    cv.thick_line(x + w // 2, base_y - h - 62, x + w // 2 + 62,
                  base_y - h - 78, 3, (255, 220, 140))
    # lit windows up the tower
    for k in range(5):
        wy = base_y - 26 - k * 22
        cv.fill_rect(x + w // 2 - 4, wy, 8, 10, LANTERN)


def draw_right_island(cv):
    cx, top = 792, 420
    draw_island(cv, cx, top, 170, 132, LEAF, ROCK)
    draw_tower(cv, cx - 26, top, 52, 150)
    draw_dome(cv, cx - 128, top - 52, 56, 52, CREAM, (72, 130, 160))
    draw_house(cv, cx + 42, top - 46, 50, 46, (232, 210, 170), (178, 62, 62))
    draw_house(cv, cx + 100, top - 38, 42, 38, CREAM, TEAL)
    cv.thick_line(cx + 121, top - 38, cx + 121, top - 68, 3, WOOD)
    cv.polygon([(cx + 121, top - 68), (cx + 145, top - 61),
                (cx + 121, top - 54)], (72, 130, 160))
    # waterfall spilling off the island's edge into the clouds
    cv.polygon([(cx + 128, top + 6), (cx + 146, top + 6),
                (cx + 158, top + 150), (cx + 138, top + 150)],
               (190, 226, 238))
    cv.polygon([(cx + 134, top + 6), (cx + 140, top + 6),
                (cx + 148, top + 150), (cx + 144, top + 150)],
               (235, 246, 250))
    cv.ellipse(cx, 692, 170, 12, (232, 172, 132))


def draw_lantern_bridge(cv):
    """The Lantern Bridge: a wooden arc strung between the two islands,
    with a lantern hanging from every span."""
    p0 = (392, 470)
    p1 = (600, 590)
    p2 = (672, 448)
    cv.quad_bezier(p0, p1, p2, 10, WOOD)
    cv.quad_bezier(p0, p1, p2, 4, (120, 70, 40))
    for k in range(1, 9):
        t = k / 9.0
        bx, by = cv.quad_point(p0, p1, p2, t)
        bx, by = int(bx), int(by)
        cv.thick_line(bx, by + 4, bx, by + 22, 2, (90, 54, 32))
        cv.circle(bx, by + 30, 9, LANTERN)
        cv.circle(bx, by + 30, 5, (255, 226, 130))
        cv.fill_rect(bx - 2, by + 20, 4, 3, GOLD)
    # end posts
    cv.fill_rect(386, 438, 12, 40, WOOD)
    cv.fill_rect(664, 416, 12, 40, WOOD)
    cv.circle(392, 436, 7, LANTERN)
    cv.circle(670, 414, 7, LANTERN)


def draw_balloon(cv, cx, cy, rx, ry, stripes):
    """Striped hot-air balloon, drawn row by row (no clipping needed)."""
    for dy in range(-ry, ry + 1):
        f = 1.0 - (dy * dy) / float(ry * ry)
        dx = int(rx * math.sqrt(max(0.0, f)))
        y = cy + dy
        span = 2 * dx + 1
        for k, col in enumerate(stripes):
            xa = cx - dx + k * span // len(stripes)
            xb = cx - dx + (k + 1) * span // len(stripes)
            if xb > xa:
                cv.fill_rect(xa, y, xb - xa, 1, col)
    # basket
    cv.fill_rect(cx - 12, cy + ry + 6, 24, 16, WOOD)
    cv.thick_line(cx - 10, cy + ry - 2, cx - 10, cy + ry + 8, 2, (90, 54, 32))
    cv.thick_line(cx + 10, cy + ry - 2, cx + 10, cy + ry + 8, 2, (90, 54, 32))


def draw_bird(cv, x, y, s):
    cv.thick_line(x - s, y, x, y - s // 2, 3, INK)
    cv.thick_line(x, y - s // 2, x + s, y, 3, INK)


def draw_sky_clouds(cv):
    for (cx, cy, s) in [(150, 150, 0.9), (480, 110, 0.7), (880, 180, 0.8),
                        (90, 330, 0.7), (950, 330, 0.65)]:
        draw_cloud_puff(cv, cx, cy, s, (255, 244, 224))

# ------------------------------------------------------------------- poster
def build():
    cv = Canvas(W, H)

    # dusk sky
    cv.vgrad(0, 806, [
        (0.00, (24, 28, 66)),
        (0.30, (72, 52, 110)),
        (0.55, (150, 80, 120)),
        (0.78, (238, 150, 105)),
        (1.00, (250, 196, 130)),
    ])
    draw_stars(cv)
    draw_sky_clouds(cv)
    draw_sun(cv)
    draw_mountains(cv)

    # the cloud sea the city floats above
    draw_cloud_sea(cv)

    # birds
    draw_bird(cv, 420, 250, 14)
    draw_bird(cv, 470, 210, 11)
    draw_bird(cv, 540, 280, 12)
    draw_bird(cv, 880, 260, 13)

    # balloons drifting past the islands
    draw_balloon(cv, 130, 330, 42, 52,
                 [(214, 80, 70), (253, 238, 205), (72, 130, 160)])
    draw_balloon(cv, 905, 300, 30, 38,
                 [(72, 130, 160), (246, 196, 83), (253, 238, 205)])

    # the city itself: two floating islands, one lantern bridge
    draw_left_island(cv)
    draw_right_island(cv)
    draw_lantern_bridge(cv)

    # thin gold frame around the scene
    cv.fill_rect(18, 18, W - 36, 4, GOLD)
    cv.fill_rect(18, H - 222, W - 36, 4, GOLD)
    cv.fill_rect(18, 18, 4, H - 236, GOLD)
    cv.fill_rect(W - 22, 18, 4, H - 236, GOLD)

    # ------------------------------------------------ title band
    cv.fill_rect(0, 806, W, H - 806, INK)
    cv.fill_rect(0, 806, W, 4, GOLD)
    cv.fill_rect(0, 818, W, 2, (246, 196, 83))

    # place name, large and legible, shadowed in the band's dark ink
    title = "NIMBARA"
    draw_text_centered(cv, title, W // 2 + 4, 850, 16, (8, 9, 26))
    draw_text_centered(cv, title, W // 2, 846, 16, GOLD)
    # gold underline rule under the name, sized to the enlarged title
    tw = text_width(title, 16)
    cv.fill_rect(W // 2 - tw // 2, 962, tw, 2, GOLD)

    # the promise of the place, small caps beneath the name
    sub = "CITY ABOVE THE CLOUDS"
    draw_text_centered(cv, sub, W // 2, 968, 4, CREAM)

    # small gold diamonds flanking the subtitle
    for dx in (-text_width(sub, 4) // 2 - 34, text_width(sub, 4) // 2 + 34):
        cx = W // 2 + dx
        cy = 978
        cv.polygon([(cx, cy - 7), (cx + 7, cy), (cx, cy + 7), (cx - 7, cy)],
                   GOLD)

    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, build())
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
