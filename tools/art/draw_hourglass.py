#!/usr/bin/env python3
"""Procedural pixel art for the `hourglass` sprite pack (dev tool, stdlib only).

Writes packs/hourglass/sprites/{egg,sprout,runner,keeper}.png and
packs/hourglass/preview.png. Scripts are banned inside packs, so the generator
lives here. Run from anywhere:

    python tools/art/draw_hourglass.py

Four growth stages share one animation layout (see ANIM_ORDER). The SAND LEVEL
is the growth: a few grains in a closed vial, a little sand, a healthy runner,
a full keeper with a crown of glass light. Palette rules: amber sand, glass
highlight, no pure white anywhere.
"""
import os
import sys
from dataclasses import dataclass, replace
from typing import Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pngutil  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "packs", "hourglass")

# ---- palette (RGBA). Nothing here is pure white. ------------------------------
SAND = (232, 163, 58, 255)
SAND_HI = (244, 193, 93, 255)
SAND_LO = (185, 119, 42, 255)
GLASS_OUT = (111, 147, 163, 255)
GLASS_IN = (127, 176, 196, 84)
GLASS_HI = (168, 200, 214, 210)
BRASS = (197, 138, 60, 255)
BRASS_HI = (224, 170, 85, 255)
BRASS_LO = (138, 90, 34, 255)
EYE = (43, 26, 16, 255)
CREAM = (244, 232, 200, 255)
ZZZ = (183, 168, 232, 255)
SWEAT = (143, 194, 224, 255)
GLYPH_TEAL = (79, 184, 168, 255)
GLYPH_AMBER = (232, 163, 58, 200)
CROWN_HI = (191, 227, 238, 240)
CROWN_LO = (111, 163, 182, 255)

# Frame layout shared by every stage (row-major in the sheet).
ANIM_ORDER = [
    ("walk", 4), ("sit", 2), ("nap", 2), ("pop", 4), ("cheer", 4),
    ("worry", 2), ("focus", 2), ("sleep", 2), ("celebrate", 6),
]
COLS = 7


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.p = [[None] * w for _ in range(h)]

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = c

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.px(xx, yy, c)

    def bbox(self):
        xs, ys = [], []
        for y in range(self.h):
            for x in range(self.w):
                if self.p[y][x] is not None:
                    xs.append(x)
                    ys.append(y)
        if not xs:
            return None
        return min(xs), min(ys), max(xs), max(ys)

    def crop(self, x0, y0, x1, y1):
        out = Canvas(x1 - x0 + 1, y1 - y0 + 1)
        for y in range(out.h):
            for x in range(out.w):
                out.p[y][x] = self.p[y0 + y][x0 + x]
        return out

    def rot90(self, k):
        c = self
        for _ in range(k % 4):
            n = Canvas(c.h, c.w)
            for y in range(n.h):
                for x in range(n.w):
                    n.p[y][x] = c.p[c.h - 1 - x][y]
            c = n
        return c

    def blit(self, src, dx, dy):
        for y in range(src.h):
            for x in range(src.w):
                if src.p[y][x] is not None:
                    self.px(dx + x, dy + y, src.p[y][x])

    def rgba(self):
        out = bytearray()
        for row in self.p:
            for c in row:
                out += bytes(c) if c is not None else b"\x00\x00\x00\x00"
        return bytes(out)


@dataclass(frozen=True)
class Shape:
    frame: int            # square frame size
    cap_w: int
    cap_top_h: int
    upper: tuple          # glass widths, top to bottom
    neck_w: int
    neck_h: int
    lower: tuple
    cap_bot_h: int
    eye_w: int
    eye_h: int
    eye_row: int          # row index inside `lower`
    eye_dxl: int          # left eye x offset from cx
    eye_dxr: int
    mouth: bool
    feet_w: int           # 0 = no feet
    feet_h: int
    feet_x0: int          # left foot start offset from cx
    arm_len: int          # 0 = no arms
    arm_row: int          # row index inside `upper`
    top_sand: int
    bot_sand: int
    eye_color: tuple = EYE
    crown: bool = False

    @property
    def body_h(self):
        return (self.cap_top_h + len(self.upper) + self.neck_h
                + len(self.lower) + self.cap_bot_h)

    @property
    def cx(self):
        return self.frame // 2

    @property
    def standing_top(self):
        return self.frame - 1 - self.feet_h - self.body_h + 1

    @property
    def extent(self):
        return self.body_h + self.feet_h


EGG = Shape(
    frame=32, cap_w=6, cap_top_h=1, upper=(), neck_w=0, neck_h=0,
    lower=(6, 8, 8, 8, 8, 8, 8, 6), cap_bot_h=0,
    eye_w=1, eye_h=2, eye_row=1, eye_dxl=-2, eye_dxr=1, mouth=False,
    feet_w=0, feet_h=0, feet_x0=0, arm_len=0, arm_row=0,
    top_sand=0, bot_sand=3, eye_color=CREAM,
)
SPROUT = Shape(
    frame=32, cap_w=12, cap_top_h=1, upper=(10, 10, 8, 6), neck_w=4, neck_h=1,
    lower=(6, 8, 10, 10), cap_bot_h=1,
    eye_w=1, eye_h=2, eye_row=2, eye_dxl=-3, eye_dxr=2, mouth=False,
    feet_w=3, feet_h=2, feet_x0=-4, arm_len=2, arm_row=1,
    top_sand=1, bot_sand=3,
)
RUNNER = Shape(
    frame=32, cap_w=18, cap_top_h=2, upper=(16, 16, 14, 14, 12, 10, 8, 6, 6),
    neck_w=4, neck_h=2, lower=(6, 6, 8, 10, 12, 14, 14, 16, 16), cap_bot_h=2,
    eye_w=2, eye_h=3, eye_row=4, eye_dxl=-4, eye_dxr=2, mouth=True,
    feet_w=4, feet_h=2, feet_x0=-6, arm_len=3, arm_row=3,
    top_sand=4, bot_sand=7,
)
KEEPER = Shape(
    frame=40, cap_w=22, cap_top_h=2, upper=(20, 20, 18, 18, 16, 14, 12, 10, 8, 8),
    neck_w=6, neck_h=2, lower=(8, 8, 10, 12, 14, 16, 18, 18, 20, 20), cap_bot_h=2,
    eye_w=2, eye_h=3, eye_row=5, eye_dxl=-5, eye_dxr=3, mouth=True,
    feet_w=5, feet_h=3, feet_x0=-8, arm_len=4, arm_row=3,
    top_sand=6, bot_sand=10, crown=True,
)
STAGES = [
    ("egg", "Egg", 0.0, EGG),
    ("sprout", "Sprout", 0.1, SPROUT),
    ("runner", "Runner", 0.35, RUNNER),
    ("keeper", "Keeper", 0.75, KEEPER),
]


@dataclass(frozen=True)
class Pose:
    dy: int = 0
    dx: int = 0
    eyes: str = "open"        # open | wide | closed | happy | squint
    look: int = 0
    lean: int = 0
    feet: tuple = ("down", "down")   # per foot: down | up
    foot_dx: tuple = (0, 0)
    follow: bool = False      # feet travel with the body (airborne)
    sit: bool = False         # sideways foot pads, body on the ground
    mouth: Optional[str] = None      # None | "o"
    arms: bool = False
    trickle: bool = True
    grain: int = 0
    twinkle: int = 0
    top_sand: Optional[int] = None
    bot_sand: Optional[int] = None


def _row_shift(shape, r, lean):
    if lean == 0 or shape.body_h <= 1:
        return 0
    return round(lean * (shape.body_h - 1 - r) / (shape.body_h - 1))


def draw_eyes(cv, shape, pose, rows_y0, shifts):
    ey = rows_y0 + shape.eye_row           # first eye row (absolute y)
    r_abs = shape.cap_top_h + len(shape.upper) + shape.neck_h + shape.eye_row
    sh = shifts(r_abs)
    c = shape.eye_color
    for ex in (shape.cx + shape.eye_dxl + pose.look + sh,
               shape.cx + shape.eye_dxr + pose.look + sh):
        w, h = shape.eye_w, shape.eye_h
        if pose.eyes in ("open", "wide"):
            cv.rect(ex, ey, w, h, c)
            if pose.eyes == "wide" and w >= 2 and h >= 2:
                cv.px(ex + w - 1, ey, CREAM)
            elif pose.eyes == "open" and w >= 2 and h >= 3:
                cv.px(ex + w - 1, ey, CREAM)
        elif pose.eyes == "closed":
            cv.rect(ex - (1 if w >= 2 else 0), ey + h - 1, w + (1 if w >= 2 else 0) + 1, 1, c)
        elif pose.eyes == "squint":
            cv.rect(ex - (1 if w >= 2 else 0), ey + h // 2, w + (1 if w >= 2 else 0) + 1, 1, c)
        elif pose.eyes == "happy":
            if w >= 2:
                cv.px(ex - 1, ey + 2 if h >= 3 else ey + 1, c)
                cv.px(ex, ey + 1, c)
                cv.px(ex + 1, ey + 1, c)
                cv.px(ex + 2, ey + 2 if h >= 3 else ey + 1, c)
            else:
                cv.px(ex - 1, ey + 1, c)
                cv.px(ex, ey, c)
                cv.px(ex + 1, ey + 1, c)
    if pose.mouth == "o" and shape.mouth:
        my = ey + shape.eye_h
        mx = shape.cx - 1 + pose.look + sh
        cv.rect(mx, my, 2, 2, shape.eye_color)


def draw_body(cv, shape, pose):
    """Draw one standing creature into `cv`. Returns (top_y, bottom_y_of_body)."""
    cx = shape.cx
    top_sand = shape.top_sand if pose.top_sand is None else pose.top_sand
    bot_sand = shape.bot_sand if pose.bot_sand is None else pose.bot_sand
    H = shape.body_h
    ground = shape.frame - 1
    if pose.sit:
        top = ground - H + 1 + pose.dy
    else:
        top = shape.standing_top + pose.dy
    lean = pose.lean

    def shift(r):
        return _row_shift(shape, r, lean)

    # -- feet (drawn first so the base cap overlaps raised ones) -----------------
    if shape.feet_w > 0:
        if pose.sit:
            by = top + H - 2
            for side in (-1, 1):
                x0 = cx - shape.cap_w // 2 - 2 if side < 0 else cx + shape.cap_w // 2 - 1 + 1
                cv.rect(x0, by, 3, 2, BRASS_LO)
                cv.rect(x0, by, 3, 1, BRASS)
        else:
            for i in (0, 1):
                x0 = cx + shape.feet_x0 if i == 0 else cx - shape.feet_x0 - shape.feet_w
                x0 += pose.foot_dx[i]
                if pose.follow:
                    y0 = top + H
                else:
                    y0 = ground - shape.feet_h + 1
                if pose.feet[i] == "up":
                    y0 -= 1
                cv.rect(x0, y0, shape.feet_w, shape.feet_h, BRASS_LO)
                cv.rect(x0, y0, shape.feet_w, 1, BRASS)

    r = 0
    y = top

    def row_x(w, rr):
        s = shift(rr)
        return cx - w // 2 + s, cx + w // 2 - 1 + s

    # -- top cap / cork ----------------------------------------------------------
    for i in range(shape.cap_top_h):
        xl, xr = row_x(shape.cap_w, r)
        col = BRASS_HI if i == 0 else BRASS
        cv.rect(xl, y, xr - xl + 1, 1, col)
        r += 1
        y += 1

    def glass_row(w, rr, yy, fill, idx, n, kind, closed_bottom=False):
        xl, xr = row_x(w, rr)
        if closed_bottom:
            cv.rect(xl, yy, xr - xl + 1, 1, GLASS_OUT)
            return
        cv.px(xl, yy, GLASS_OUT)
        cv.px(xr, yy, GLASS_OUT)
        for xx in range(xl + 1, xr):
            cv.px(xx, yy, GLASS_IN)
        if kind == "up" and 1 <= idx <= 3 and xr - xl > 4:
            cv.px(xl + 1, yy, GLASS_HI)
        if kind == "low" and 2 <= idx <= 4 and xr - xl > 6:
            cv.px(xl + 1, yy, GLASS_HI)
        if fill:
            top_row = fill == "top"
            a, b = xl + 1, xr - 1
            if kind == "low" and top_row:
                a, b = a + 2, b - 2
            for xx in range(a, b + 1):
                col = SAND_HI if top_row else SAND
                if not top_row and xx == b and b - a >= 3:
                    col = SAND_LO
                cv.px(xx, yy, col)

    # -- upper bulb ---------------------------------------------------------------
    n_up = len(shape.upper)
    for i, w in enumerate(shape.upper):
        filled = i >= n_up - top_sand
        top_row = filled and i == n_up - top_sand
        glass_row(w, r, y, ("top" if top_row else True) if filled else False, i, n_up, "up")
        r += 1
        y += 1

    # -- neck ---------------------------------------------------------------------
    for i in range(shape.neck_h):
        xl, xr = row_x(shape.neck_w, r)
        cv.px(xl, y, GLASS_OUT)
        cv.px(xr, y, GLASS_OUT)
        for xx in range(xl + 1, xr):
            cv.px(xx, y, GLASS_IN)
        if pose.trickle and top_sand > 0:
            for xx in range(xl + 1, xr):
                cv.px(xx, y, SAND)
            if pose.grain % 2 == i % 2:
                cv.px(xl + 1, y, SAND_HI)
            else:
                cv.px(xr - 1, y, SAND_HI)
        r += 1
        y += 1

    # -- lower bulb ---------------------------------------------------------------
    n_low = len(shape.lower)
    low_y0 = y
    for i, w in enumerate(shape.lower):
        filled = i >= n_low - bot_sand
        top_row = filled and i == n_low - bot_sand
        closed = shape.cap_bot_h == 0 and i == n_low - 1
        glass_row(w, r, y, ("top" if top_row else True) if filled else False, i, n_low,
                  "low", closed_bottom=closed)
        r += 1
        y += 1

    # -- bottom cap ---------------------------------------------------------------
    for i in range(shape.cap_bot_h):
        xl, xr = row_x(shape.cap_w, r)
        col = BRASS if i < shape.cap_bot_h - 1 else BRASS_LO
        cv.rect(xl, y, xr - xl + 1, 1, col)
        r += 1
        y += 1

    # -- face ---------------------------------------------------------------------
    draw_eyes(cv, shape, pose, low_y0, shift)

    # -- arms ---------------------------------------------------------------------
    if pose.arms and shape.arm_len:
        ar = shape.cap_top_h + shape.arm_row
        ay = top + ar
        w = shape.upper[shape.arm_row]
        xl, xr = row_x(w, ar)
        for n in range(shape.arm_len):
            cv.px(xl - 1 - n, ay - n, BRASS)
            cv.px(xl - 1 - n, ay - n + 1, BRASS_LO)
            cv.px(xr + 1 + n, ay - n, BRASS)
            cv.px(xr + 1 + n, ay - n + 1, BRASS_LO)

    # -- crown of glass light -----------------------------------------------------
    if shape.crown:
        s = shift(0)
        cy = top - 3
        base = cx - 3 + s
        for off in (0, 3, 6):
            cv.px(base + off, cy, CROWN_HI)
        for off in range(7):
            cv.px(base + off, cy + 1, CROWN_HI)
            cv.px(base + off, cy + 2, CROWN_LO)
        if pose.twinkle:
            spots = {1: (base + 3, cy - 2), 2: (base, cy - 1), 3: (base + 6, cy - 1)}
            tx, ty = spots[pose.twinkle]
            cv.px(tx, ty, CREAM)
    return top, top + H - 1


# ---- accessories ------------------------------------------------------------------
def draw_z(cv, x, y, big):
    if big:
        for dx in range(3):
            cv.px(x + dx, y, ZZZ)
            cv.px(x + dx, y + 2, ZZZ)
        cv.px(x + 1, y + 1, ZZZ)
    else:
        cv.px(x, y, ZZZ)
        cv.px(x + 1, y, ZZZ)
        cv.px(x, y + 1, ZZZ)
        cv.px(x + 1, y + 1, ZZZ)


def draw_sweat(cv, x, y):
    for dx, dy in ((1, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2)):
        cv.px(x + dx, y + dy, SWEAT)


def draw_plus(cv, x, y, c):
    for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
        cv.px(x + dx, y + dy, c)


GLYPHS = [
    ("#.#", ".#.", "#.#"),
    ("##.", ".#.", ".##"),
    ("#..", "###", "..#"),
    (".#.", "###", ".#."),
]


def draw_glyph(cv, x, y, g, c):
    for gy, row in enumerate(GLYPHS[g]):
        for gx, ch in enumerate(row):
            if ch == "#":
                cv.px(x + gx, y + gy, c)


def fresh(shape):
    return Canvas(shape.frame, shape.frame)


def sparkles(cv, shape, cx, cy, frame, spread):
    pts = [(-spread, -spread // 2), (spread, -spread // 3), (-spread // 2, -spread - 2),
           (spread - 1, -spread - 3)]
    cols = [CREAM, SAND_HI, CROWN_HI, SAND_HI]
    for i, (dx, dy) in enumerate(pts):
        if (i + frame) % 3 == 0:
            cv.px(cx + dx, cy + dy, cols[i])
        else:
            draw_plus(cv, cx + dx, cy + dy, cols[i])


# ---- animations ---------------------------------------------------------------------
def anim_walk(shape):
    frames = []
    has_feet = shape.feet_w > 0
    leans = [1, 0, -1, 0]
    for f in range(4):
        if has_feet:
            if f == 0:
                pose = Pose(look=1, feet=("down", "up"), foot_dx=(2, -2), lean=leans[f] if shape is SPROUT else 0)
            elif f == 2:
                pose = Pose(look=1, feet=("up", "down"), foot_dx=(-2, 2), lean=leans[f] if shape is SPROUT else 0)
            else:
                pose = Pose(look=1, dy=-1, lean=leans[f] if shape is SPROUT else 0)
        else:
            pose = Pose(look=1, dy=-2 if f % 2 else 0, lean=leans[f])
        pose = replace(pose, grain=f)
        cv = fresh(shape)
        draw_body(cv, shape, pose)
        frames.append(cv)
    return frames


def anim_sit(shape):
    frames = []
    for f in range(2):
        cv = fresh(shape)
        sit = shape.feet_w > 0
        pose = Pose(sit=sit, eyes="open" if f == 0 else "closed", grain=f)
        draw_body(cv, shape, pose)
        frames.append(cv)
    return frames


def anim_nap(shape):
    frames = []
    for f in range(2):
        cv = fresh(shape)
        pose = Pose(sit=shape.feet_w > 0, eyes="closed", grain=f, lean=0)
        top, _ = draw_body(cv, shape, pose)
        zx = shape.cx + shape.cap_w // 2 + 1
        draw_z(cv, zx, max(0, top - 2 - f * 2), f == 1)
        if f == 1:
            draw_z(cv, zx + 4, max(0, top - 6), False)
        frames.append(cv)
    return frames


def anim_pop(shape):
    frames = []
    total = shape.extent + (3 if shape.crown else 0)
    dys = [total - 5, round(total * 0.55), round(total * 0.2), -2]
    fw = shape.frame
    cols = [round(fw * 0.14), round(fw * 0.30), round(fw * 0.72), round(fw * 0.86)]
    seeds = [(1, 0), (9, 1), (3, 2), (12, 3)]
    for f in range(4):
        cv = fresh(shape)
        # glyph rain falls behind the creature
        for i, x in enumerate(cols):
            y0, g = seeds[i]
            col = GLYPH_TEAL if i % 2 == 0 else GLYPH_AMBER
            draw_glyph(cv, x, y0 + 6 * f, g, col)
            draw_glyph(cv, x + 2, y0 + 6 * f - 11, (g + 1) % 4, GLYPH_AMBER if i % 2 == 0 else GLYPH_TEAL)
        pose = Pose(dy=dys[f], follow=True, eyes="wide" if f >= 2 else "open", look=0,
                    grain=f, twinkle=f if f else 0)
        draw_body(cv, shape, pose)
        frames.append(cv)
    return frames


def _airborne(shape, pose):
    """Render a standing pose, crop to its bounding box."""
    cv = fresh(shape)
    draw_body(cv, shape, pose)
    bb = cv.bbox()
    return cv.crop(*bb)


def anim_cheer(shape):
    frames = []
    head = shape.standing_top - (3 if shape.crown else 0)
    apex = max(2, min(head - 1, int(shape.body_h * 0.5)))
    dys = [2 if shape.feet_w else 1, -round(apex * 0.5), -apex, -round(apex * 0.25)]
    for f in range(4):
        cv = fresh(shape)
        airborne = f in (1, 2)
        pose = Pose(dy=dys[f], eyes="happy", arms=f in (1, 2, 3) and bool(shape.arm_len),
                    follow=airborne, feet=("down", "down"), grain=f, twinkle=f)
        top, _ = draw_body(cv, shape, pose)
        if f in (1, 2, 3):
            sparkles(cv, shape, shape.cx, top + shape.body_h // 2, f, shape.cap_w // 2 + 3)
        frames.append(cv)
    return frames


def anim_worry(shape):
    frames = []
    for f in range(2):
        cv = fresh(shape)
        pose = Pose(dx=0, eyes="wide", mouth="o", lean=-1 if f == 0 else 1, grain=f,
                    feet=("down", "down"))
        top, _ = draw_body(cv, shape, pose)
        draw_sweat(cv, shape.cx + shape.cap_w // 2 + 1, top + 2 + f * 3)
        frames.append(cv)
    return frames


def anim_focus(shape):
    frames = []
    for f in range(2):
        cv = fresh(shape)
        lean = 2 + f if shape.feet_w == 0 or shape.body_h > 14 else 1 + f
        pose = Pose(eyes="squint", look=1, lean=lean, grain=f)
        draw_body(cv, shape, pose)
        frames.append(cv)
    return frames


def anim_sleep(shape):
    frames = []
    for f in range(2):
        pose = Pose(eyes="closed", trickle=False, follow=True)
        cv = fresh(shape)
        draw_body(cv, shape, pose)
        bb = cv.bbox()
        body = cv.crop(*bb).rot90(1)
        out = fresh(shape)
        x0 = shape.cx - body.w // 2
        y0 = shape.frame - body.h
        out.blit(body, x0, y0)
        zx = x0 + body.w - 2
        zy = max(0, y0 - 5 - f * 3)
        draw_z(out, zx, zy, f == 1)
        if f == 1:
            draw_z(out, zx + 4, max(0, zy - 4), False)
        frames.append(out)
    return frames


def anim_celebrate(shape):
    frames = []
    head = shape.standing_top - (3 if shape.crown else 0)
    a = max(3, min(head - 1, 9))
    lifts = [0, round(a * 0.6), a, a, round(a * 0.6), 0]
    spins = [0, 0, 1, 2, 3, 0]
    for f in range(6):
        if f == 0:
            cv = fresh(shape)
            draw_body(cv, shape, Pose(dy=2 if shape.feet_w else 1, eyes="happy",
                                      arms=bool(shape.arm_len), twinkle=1))
            frames.append(cv)
            continue
        pose = Pose(eyes="happy", arms=bool(shape.arm_len) and spins[f] == 0, follow=True,
                    twinkle=f % 3 + 1)
        body = _airborne(shape, pose).rot90(spins[f])
        out = fresh(shape)
        lift = lifts[f]
        x0 = shape.cx - body.w // 2
        y0 = shape.frame - 1 - lift - body.h + 1
        out.blit(body, x0, max(0, y0))
        center_y = max(0, y0) + body.h // 2
        sparkles(out, shape, shape.cx, center_y, f, max(body.w, body.h) // 2 + 3)
        frames.append(out)
    return frames


BUILDERS = {
    "walk": anim_walk, "sit": anim_sit, "nap": anim_nap, "pop": anim_pop,
    "cheer": anim_cheer, "worry": anim_worry, "focus": anim_focus,
    "sleep": anim_sleep, "celebrate": anim_celebrate,
}


def stage_frames(shape):
    frames = []
    for name, count in ANIM_ORDER:
        built = BUILDERS[name](shape)
        assert len(built) == count, (name, len(built), count)
        frames.extend(built)
    return frames


def build_sheet(shape):
    frames = stage_frames(shape)
    rows = (len(frames) + COLS - 1) // COLS
    sheet = Canvas(COLS * shape.frame, rows * shape.frame)
    for i, fr in enumerate(frames):
        sheet.blit(fr, (i % COLS) * shape.frame, (i // COLS) * shape.frame)
    return sheet, frames


BG = (11, 11, 15, 255)


def over(bg, fg):
    a = fg[3] / 255.0
    return tuple(round(fg[i] * a + bg[i] * (1 - a)) for i in range(3)) + (255,)


def preview(all_frames):
    scale, cell = 3, 40
    cols, rows = 4, 2
    pad = 12
    cw = cell * scale + pad
    w, h = cols * cw, rows * cw
    cv = Canvas(w, h)
    for y in range(h):
        for x in range(w):
            cv.p[y][x] = BG

    def put(shape, fr, col, row):
        ox = col * cw + pad // 2 + (cell - shape.frame) * scale // 2
        oy = row * cw + pad // 2 + (cell - shape.frame) * scale
        for y in range(fr.h):
            for x in range(fr.w):
                c = fr.p[y][x]
                if c is None:
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        px, py = ox + x * scale + sx, oy + y * scale + sy
                        if 0 <= px < w and 0 <= py < h:
                            cv.p[py][px] = over(BG, c)

    idx = {}
    start = 0
    for name, count in ANIM_ORDER:
        idx[name] = start
        start += count
    for i, (sid, _, _, shape) in enumerate(STAGES):
        put(shape, all_frames[sid][idx["sit"]], i, 0)
    keeper = STAGES[3][3]
    runner = STAGES[2][3]
    put(runner, all_frames["runner"][idx["walk"]], 0, 1)
    put(runner, all_frames["runner"][idx["pop"] + 3], 1, 1)
    put(keeper, all_frames["keeper"][idx["celebrate"] + 2], 2, 1)
    put(keeper, all_frames["keeper"][idx["sleep"]], 3, 1)
    return cv, w, h


def main():
    os.makedirs(os.path.join(OUT, "sprites"), exist_ok=True)
    all_frames = {}
    for sid, _name, _g, shape in STAGES:
        sheet, frames = build_sheet(shape)
        all_frames[sid] = frames
        pngutil.write_rgba(os.path.join(OUT, "sprites", sid + ".png"),
                           sheet.w, sheet.h, sheet.rgba())
        print("wrote sprites/%s.png  %dx%d  %d frames of %dx%d"
              % (sid, sheet.w, sheet.h, len(frames), shape.frame, shape.frame))
    pv, w, h = preview(all_frames)
    pngutil.write_rgba(os.path.join(OUT, "preview.png"), w, h, pv.rgba())
    print("wrote preview.png  %dx%d" % (w, h))


if __name__ == "__main__":
    main()
