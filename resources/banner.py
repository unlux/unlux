#!/usr/bin/env python3
"""Generate the animated pixel-art profile banners: hero-dark.svg and hero-light.svg.

An endless runner that plays itself. A small dinosaur runs left to right across a
desert and hops the cacti. At night it does this asleep, in a nightcap, and the
counter counts sheep. Everything is drawn on one 300x100 pixel grid.

    python3 banner.py <out-dir>            write the two banners
    python3 banner.py <out-dir> --sheet    also write sheet.html, a zoomed sprite sheet
"""
import math
import os
import random
import sys

U = 4                 # one art pixel in SVG units
W, H = 300, 100       # visible grid
GROUND = 84           # top row of the ground
SPEED = 60.0          # ground scroll, grid pixels per second
PERIOD = 12.0         # seconds for one ground tile
TILE = int(SPEED * PERIOD)
GRAVITY = 190.0       # grid pixels per second squared
DINO_X, DINO_H = 138, 44
FRAME_S = 0.08        # seconds per run frame
NIGHT_PACE = 0.6      # the night run is the day run played at this fraction of full speed
# (seconds into the loop when the cactus is under the dino, cactus kind)
OBSTACLES = [(1.3, "small"), (4.1, "big"), (6.6, "small"), (9.3, "pair")]

FONT = {
    "u": [".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"],
    "l": ["#", "#", "#", "#", "#", "#", "#"],
    "i": ["#", ".", "#", "#", "#", "#", "#"],
    "b": ["#....", "#....", "#.##.", "##..#", "#...#", "#...#", "####."],
    "d": ["....#", "....#", ".##.#", "#..##", "#...#", "#...#", ".####"],
    "s": [".....", ".....", ".####", "#....", ".###.", "....#", "####."],
    "h": ["#....", "#....", "#.##.", "##..#", "#...#", "#...#", "#...#"],
    "o": [".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."],
    "m": [".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"],
    "e": [".....", ".....", ".###.", "#...#", "#####", "#....", ".###."],
    "t": [".#..", ".#..", "####", ".#..", ".#..", ".#..", "..##"],
    "c": [".....", ".....", ".###.", "#....", "#....", "#....", ".###."],
    "a": [".....", ".....", ".###.", "....#", ".####", "#...#", ".####"],
    "p": [".....", ".....", "#.##.", "##..#", "#...#", "##..#", "#.##.", "#....", "#...."],
    " ": ["...", "...", "...", "...", "...", "...", "..."],
}
DIGITS = [
    [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    [".###.", "#...#", "....#", "..##.", "....#", "#...#", ".###."],
    ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
]
TITLE = {
    "u": ["......."] * 4 + ["##...##"] * 7 + ["#######", ".#####."],
    "n": ["......."] * 4 + [".#####.", "#######"] + ["##...##"] * 7,
    "l": ["##"] * 13,
    "x": ["......."] * 4 + ["##...##", "##...##", ".##.##.", "..###..", "..###..", "..###..", ".##.##.", "##...##", "##...##"],
}
Z_S = ["####", "..#.", ".#..", "####"]
Z_M = ["#####", "...#.", "..#..", ".#...", "#####"]
Z_L = ["######", "....#.", "...#..", "..#...", ".#....", "######"]
CACTI = {
    "big": [
        "....###....", "...#####...", "...#####...", "...#####...", "...#####.##", "##.#####.##",
        "##.#####.##", "##.#####.##", "##.########", "##.#######.", "#########..", ".#######...",
        "...#####...", "...#####...", "...#####...", "...#####...", "...#####...", "...#####...",
    ],
    "small": [
        "..###..", "..###..", "..###.#", "#.###.#", "#.#####", "#####..", ".####..", "..###..", "..###..", "..###..",
    ],
    "pair": [
        "..###.........", "..###.....##..", "#.###.#...##.#", "#.###.#.#.##.#", "#.#####.#.####",
        "#####...####..", ".####....###..", "..###.....##..", "..###.....##..", "..###.....##..",
    ],
}
CACTUS_FLOWERS = {"big": [(5, -1), (0, 4), (10, 3)], "small": [(3, -1)], "pair": [(3, -1), (10, 0)]}
BUSH = ["..#..#..", ".##.###.", "########"]
ROCK = [".###.", "#####"]
FAR_CACTUS = [".#.", "###", ".#.", ".#."]
CLOUD = ["......#####.......", "...##########.....", ".###############..", "##################"]
PUFFS = [[".##.##.", "#######"], [".#...#.", "#.###.#", ".#####."], ["#..#..#", ".......", ".#...#."]]

# ---- rasterisers ---------------------------------------------------------------------------


def ellipse(cx, cy, rx, ry):
    return {(x, y) for y in range(int(cy - ry) - 1, int(cy + ry) + 2) for x in range(int(cx - rx) - 1, int(cx + rx) + 2)
            if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1}


def disc(cx, cy, r):
    return ellipse(cx, cy, r, r)


def rrect(x0, y0, x1, y1, r):
    """Rounded rectangle over inclusive pixel bounds."""
    out = set()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            px, py = x + .5, y + .5
            qx = min(max(px, x0 + r), x1 + 1 - r)
            qy = min(max(py, y0 + r), y1 + 1 - r)
            if (px - qx) ** 2 + (py - qy) ** 2 <= r * r:
                out.add((x, y))
    return out


def tube(fn, r0, r1, n=48):
    """Union of discs along a curve. Returns {pixel: t of the nearest sample}."""
    out = {}
    for i in range(n + 1):
        t = i / n
        cx, cy = fn(t)
        for p in disc(cx, cy, r0 + (r1 - r0) * t):
            out.setdefault(p, t)
    return out


def capsule(p0, p1, r0, r1):
    return set(tube(lambda t: (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t), r0, r1, 16))


def bezier(p0, p1, p2):
    return lambda t: ((1 - t) ** 2 * p0[0] + 2 * t * (1 - t) * p1[0] + t * t * p2[0],
                      (1 - t) ** 2 * p0[1] + 2 * t * (1 - t) * p1[1] + t * t * p2[1])


def cells(rows):
    return {(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == "#"}


def text_cells(s, font=None, gap=1):
    pts, x = set(), 0
    for ch in s:
        g = (font or FONT)[ch]
        pts |= {(x + dx, y) for y, r in enumerate(g) for dx, c in enumerate(r) if c == "#"}
        x += len(g[0]) + gap
    return pts, x - gap


# ---- the dinosaur --------------------------------------------------------------------------

HIP, HIP_FAR = (20, 33), (23, 33)
# Run cycle, hip-relative (knee, ankle, toe). Six frames, far leg is three frames ahead.
POSES = [
    ((3.5, 3.5), (5.5, 8.2), (9.0, 8.6)),     # contact, leg forward
    ((1.5, 4.5), (0.5, 8.6), (4.0, 8.8)),     # mid stance
    ((-1.5, 4.5), (-5.0, 7.0), (-3.5, 9.0)),  # push off
    ((-2.5, 3.5), (-7.0, 3.5), (-8.5, 6.0)),  # lift behind
    ((1.5, 3.0), (-1.5, 5.5), (0.0, 8.0)),    # passing
    ((4.5, 2.0), (6.5, 5.5), (9.5, 4.5)),     # reach
]
BOB = [0, 1, 0, 0, 1, 0]
CAP_LAG = [0, 0, 1, 0, 0, 1]


def leg(hip, pose):
    k, a, t = [(hip[0] + dx, hip[1] + dy) for dx, dy in pose]
    return capsule(hip, k, 2.7, 2.1) | capsule(k, a, 1.6, 1.3) | capsule(a, t, 1.3, 1.0)


def dino_frame(i, night):
    """One run frame as {(x, y): colour key}. Faces right; feet rest on row DINO_H - 1."""
    far = leg(HIP_FAR, POSES[(i + 3) % 6])
    near = leg(HIP, POSES[i])
    tail = set(tube(bezier((13, 30), (5, 33), (0, 20)), 5.0, 1.2))
    torso = ellipse(19, 29, 10, 7.5) | ellipse(26, 23, 5.5, 6)
    head = rrect(25, 9, 38, 21, 4) | rrect(33, 14, 42, 21, 3)
    body = tail | torso | head | near
    col = {p: "F" for p in far - body}

    top = {}
    for x, y in body:
        top[x] = min(top.get(x, 99), y)
    for (x, y) in body:
        up = 0
        while (x, y - up - 1) in body:
            up += 1
        down = 0
        while (x, y + down + 1) in body:
            down += 1
        col[(x, y)] = "l" if up == 0 else "D" if down == 0 else "d" if down == 1 else "g"

    belly = (ellipse(24, 32, 7.5, 5) | ellipse(29, 24.5, 3.5, 4.5)) & (torso | head)
    belly |= {(x, y) for (x, y) in head if y >= 20 and x >= 28}
    for p in belly - near:
        down = 0
        while (p[0], p[1] + down + 1) in body:
            down += 1
        col[p] = "c" if down == 0 else "b"
    for p in ((12, 26), (15, 24), (18, 25), (9, 28), (21, 23)):
        if col.get(p) == "g":
            col[p] = "d"
    for p in capsule((28, 27), (31.5, 29.5), 1.1, 0.9):
        col[p] = "d"
    col[(32, 30)] = "D"

    # face
    if night:
        for p in ((32, 13), (36, 13), (33, 14), (34, 14), (35, 14)):
            col[p] = "k"
        col[(36, 20)] = "y"   # drool
    else:
        for p in rrect(33, 11, 35, 14, 0.6):
            col[p] = "w"
        for p in ((34, 12), (35, 12), (34, 13), (35, 13)):
            col[p] = "k"
    for x in range(36, 43):
        col[(x, 19)] = "k"
    col[(35, 18)] = "k"
    col[(41, 15)] = "k"
    col[(31, 17)] = col[(32, 17)] = "p"

    # spikes along the back
    for sx in ([3, 8, 13, 18] if night else [3, 8, 13, 18, 23, 28]):
        t = min(top[c] for c in (sx - 1, sx, sx + 1))
        for c in (sx - 1, sx, sx + 1):
            for y in range(t - 1, top[c]):
                col[(c, y)] = "s"
        col[(sx, t - 2)] = "S"

    if night:
        lag = CAP_LAG[i]
        cone = tube(bezier((31.5, 9), (22, -3), (14.5, 9 + lag)), 5.2, 1.6)
        cone = {p: t for p, t in cone.items() if p[1] <= 8 or p[0] < 25}
        for (x, y), t in cone.items():
            stripe = int(t * 7) % 2 == 0
            under = (x, y + 1) not in cone and (x, y + 1) not in body
            col[(x, y)] = ("q" if under else "r") if stripe else ("V" if under else "W")
        for (x, y) in head:
            if y <= 10 and x <= 38:
                col[(x, y)] = "q" if y == 10 else "u"
        for x in range(27, 37):
            col[(x, 8)] = "U"
        pom = disc(14.5, 11.6 + lag, 2.5)
        low = max(y for _, y in pom)
        for (x, y) in pom:
            col[(x, y)] = "X" if y == low else "Y"

    dy = BOB[i]
    col = {(x, y + dy): k for (x, y), k in col.items() if y + dy < DINO_H}
    for (x, y) in list(col):
        for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if q not in col and q[1] < DINO_H:
                col[q] = "o"
    return col


DINO_COLOURS = dict(
    g="#7fd45f", l="#c6f291", d="#4dab5c", D="#2f7d57", F="#2a6b52", b="#fbf3c4", c="#d7cc92",
    s="#ff9d3c", S="#ffd774", w="#ffffff", k="#14213d", p="#ff8fa3", y="#9fd8ff",
    r="#8f6be8", q="#5f43b0", W="#fff7e6", V="#d6c8b0", u="#6f4fd0", U="#b79cff", Y="#ffd774", X="#e0a83c",
)

# ---- scenery -------------------------------------------------------------------------------


def mesa(tile, base, buttes):
    """Skyline of flat-topped buttes. Returns top[x] and a per-pixel shade function."""
    def signed(x, cx):
        d = (x - cx) % tile
        return d - tile if d > tile / 2 else d

    def column(x):
        a = 2 * math.pi * x / tile
        best = (base + round(1.4 * math.sin(3 * a) + math.sin(7 * a + 1)), None, 0)
        for b in buttes:
            cx, half, yt, cliff = b
            d = signed(x, cx)
            if abs(d) <= half:
                y = yt + (1 if abs(d) > half - 2 else 0)
            else:
                y = yt + cliff + int((abs(d) - half) * 0.9)
            if y < best[0]:
                best = (y, b, d)
        return best

    cols = [column(x) for x in range(tile)]

    def shade(x, y):
        top, b, d = cols[x % tile]
        if y == top:
            return "rim"
        if b:
            cx, half, yt, cliff = b
            if abs(d) <= half and y < yt + cliff:
                if d >= half - 2:
                    return "lit"
                if d <= -(half - 2):
                    return "dark"
                if (y - yt) % 4 == 2 and (x * 7 + y * 3) % 5 < 3:
                    return "dark"
            elif d < 0:
                return "dark"
        return "base"

    return [c[0] for c in cols], shade


def cactus_colours(kind):
    """{(x, y): key} with light from the upper right."""
    px = cells(CACTI[kind])
    out = {}
    for (x, y) in px:
        if (x + 1, y) not in px or (x, y - 1) not in px:
            out[(x, y)] = "L"
        elif (x - 1, y) not in px:
            out[(x, y)] = "D"
        else:
            out[(x, y)] = "G"
    for p in CACTUS_FLOWERS[kind]:
        out[p] = "P"
    return out


# ---- timing --------------------------------------------------------------------------------


def dino_hitbox():
    """Every pixel the dino can occupy in any run frame, grown by one pixel."""
    solid = set()
    for i in range(6):
        solid |= {p for p, k in dino_frame(i, False).items() if k != "o"}
    return {(x + dx, y + dy) for x, y in solid for dx in (-1, 0, 1) for dy in (-1, 0, 1)}


def fit_jumps():
    """Smallest hop that clears each cactus under fixed gravity. Returns [(tc, T, apex, kind)]."""
    box = dino_hitbox()
    centre = HIP[0] + 1.5
    out = []
    for tc, kind in OBSTACLES:
        px = cells(CACTI[kind]) | set(CACTUS_FLOWERS[kind])
        w, h = len(CACTI[kind][0]), len(CACTI[kind])
        for apex in range(8, 60):
            T = math.sqrt(8 * apex / GRAVITY)
            clear = True
            for step in range(-250, 251):
                dt = step / 100
                tau = dt / (T / 2)
                lift = round(apex * (1 - tau * tau)) if abs(tau) < 1 else 0
                ox = round(centre - w / 2 - SPEED * dt)
                if any((x + ox, y + DINO_H - h + lift) in box for x, y in px):
                    clear = False
                    break
            if clear:
                out.append((tc, T, apex + 2, kind))   # two pixels of headroom
                break
        else:
            raise SystemExit(f"no jump clears the {kind} cactus")
    out = [(tc, math.sqrt(8 * a / GRAVITY), a, k) for tc, _, a, k in out]
    for (t0, T0, _, _), (t1, T1, _, _) in zip(out, out[1:] + [(out[0][0] + PERIOD,) + out[0][1:]]):
        assert t0 + T0 / 2 + 0.25 < t1 - T1 / 2, "jumps overlap"
    return out


def pct(t, period):
    return f"{100 * t / period:.6f}".rstrip("0").rstrip(".") + "%"


def jump_keyframes(jumps, period):
    up, down = "cubic-bezier(.33,.67,.67,1)", "cubic-bezier(.33,0,.67,.33)"
    out = ["0%{transform:translateY(0)}"]
    for tc, T, apex, _ in jumps:
        out.append(f"{pct(tc - T / 2, period)}{{transform:translateY(0);animation-timing-function:{up}}}")
        out.append(f"{pct(tc, period)}{{transform:translateY({-apex * U}px);animation-timing-function:{down}}}")
        out.append(f"{pct(tc + T / 2, period)}{{transform:translateY(0)}}")
    out.append("100%{transform:translateY(0)}")
    return "@keyframes jump{" + "".join(out) + "}"


def counter_keyframes(jumps, place, pitch, loop):
    """Digit strip for 10**place. The count goes up by one each time the dino lands."""
    lands = [tc + T / 2 for tc, T, _, _ in jumps]
    per, step = len(lands), 10 ** place
    total = 10 * step * per // math.gcd(10 * step, per)
    period = total / per * loop
    out = ["0%{transform:translateY(0)}"]
    for n in range(step, total + 1, step):
        t = loop * ((n - 1) // per) + lands[(n - 1) % per]
        out.append(f"{pct(t, period)}{{transform:translateY({-(n // step % 10) * pitch * U}px)}}")
    out.append("100%{transform:translateY(0)}")
    return f"@keyframes c{place}{{" + "".join(out) + "}", period


def puff_keyframes(jumps, k, period, hold):
    out = ["0%{opacity:0}"]
    for tc, T, _, _ in jumps:
        t = tc + T / 2 + k * hold
        out.append(f"{pct(t, period)}{{opacity:1}}{pct(t + hold, period)}{{opacity:0}}")
    out.append("100%{opacity:0}")
    return f"@keyframes p{k}{{" + "".join(out) + "}"


# ---- drawing -------------------------------------------------------------------------------


class Canvas:
    def __init__(self):
        self.parts = []

    def raw(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill):
        self.parts.append(f'<rect x="{x * U}" y="{y * U}" width="{w * U}" height="{h * U}" fill="{fill}"/>')

    def pixels(self, pts, fill, scale=1, ox=0, oy=0):
        rows = {}
        for x, y in set(pts):
            rows.setdefault(y, []).append(x)
        d = []
        for y, xs in sorted(rows.items()):
            xs.sort()
            start = prev = xs[0]
            for x in xs[1:] + [None]:
                if x is not None and x == prev + 1:
                    prev = x
                    continue
                X, Y = (ox + start * scale) * U, (oy + y * scale) * U
                d.append(f"M{X} {Y}h{(prev - start + 1) * scale * U}v{scale * U}H{X}z")
                if x is not None:
                    start = prev = x
        if d:
            self.parts.append(f'<path fill="{fill}" d="{"".join(d)}"/>')

    def coloured(self, col, palette, ox=0, oy=0):
        by = {}
        for p, k in col.items():
            by.setdefault(k, []).append(p)
        for k in sorted(by):
            self.pixels(by[k], palette[k], 1, ox, oy)


def dither(c, pid, color, sparse=False):
    n = 4 if sparse else 2
    dots = f'<rect width="{U}" height="{U}" fill="{color}"/>'
    if sparse:
        dots += f'<rect x="{2 * U}" y="{2 * U}" width="{U}" height="{U}" fill="{color}"/>'
    else:
        dots += f'<rect x="{U}" y="{U}" width="{U}" height="{U}" fill="{color}"/>'
    c.raw(f'<pattern id="{pid}" width="{n * U}" height="{n * U}" patternUnits="userSpaceOnUse">{dots}</pattern>')


NIGHT = dict(
    sky=["#0a1030", "#0e1740", "#132152", "#1a2d63", "#233c73", "#2c4a80", "#38598e"],
    stars=["#ffffff", "#bcd4ff", "#ffe6a8"], star_dim="#5d76ad",
    orb=dict(light="#fdf3c7", mid="#ecd9a0", dark="#d1b674"), halo=["#2c4a80", "#233c73"],
    wisp=dict(base="#1a2d63", rim="#2c4a80"),
    far=dict(base="#2a4479", rim="#4266a0", lit="#33528a", dark="#223a6b"),
    near=dict(base="#1b2f5e", rim="#34558f", lit="#27407a", dark="#15254d"),
    mid=dict(base="#132248", rim="#243d72", bush="#16304e", bush_hi="#24506e", rock="#1d2f5c", rock_hi="#34558f"),
    ground=dict(base="#0b1433", top="#3b5d99", second="#1c2f60", grit="#18284f", crack="#070d24"),
    cactus=dict(G="#1f7a5a", L="#4cc07c", D="#135245", P="#ff7aa2"),
    outline="#060a1e", puff="#3b5d99",
    title=dict(base="#fdf3c7", hi="#ffffff", shade="#dcb466", drop="#070d24"), cap="#a9c0ea", hud="#8fa9d8", z="#cfe3ff",
)
DAY = dict(
    sky=["#6cc5ee", "#86d2f2", "#a3dff5", "#c2ebf6", "#def4f1", "#f3f3da", "#fde9bd"],
    stars=[], star_dim="",
    orb=dict(light="#fffbe0", mid="#ffe27a", dark="#ffd24d"), halo=["#fff3b8", "#fff8d6"],
    wisp=dict(base="#ffffff", rim="#dff1f8"),
    far=dict(base="#e8b08c", rim="#f6cfad", lit="#efbd9a", dark="#da9d7c"),
    near=dict(base="#cf7f5c", rim="#eaa57d", lit="#dd8f68", dark="#b5674c"),
    mid=dict(base="#e6bf7c", rim="#f5dba0", bush="#6f9f55", bush_hi="#9cc56c", rock="#c98f66", rock_hi="#eaa57d"),
    ground=dict(base="#d9a45c", top="#f8dc98", second="#e9bd72", grit="#bd8946", crack="#a37238"),
    cactus=dict(G="#3c9a55", L="#84d46d", D="#2a6f48", P="#ff6f9c"),
    outline="#1d3b3a", puff="#f8dc98",
    title=dict(base="#243b63", hi="#5179b0", shade="#14264a", drop="#fff6dc"), cap="#3d5a80", hud="#7a5226", z="",
)


def hero(night, jumps):
    P = NIGHT if night else DAY
    label = "sheep" if night else "cacti"
    pitch = 9
    c = Canvas()
    alt = ("unlux. A small pixel-art dinosaur in a nightcap runs across a desert at night, asleep, hopping cacti."
           if night else "unlux. A small pixel-art dinosaur runs across a desert, hopping cacti.")
    c.raw(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W * U} {H * U}" role="img" '
          f'aria-label="{alt}" shape-rendering="crispEdges">')
    c.raw(f"<title>{alt}</title>")

    # Night is the same run in slow motion: every clock is stretched by the same factor, so the
    # cacti sit in the same places and the hops fitted for the day run still clear them.
    pace = NIGHT_PACE if night else 1.0
    period, frame_s = PERIOD / pace, FRAME_S / pace
    timed = [(tc / pace, T / pace, apex, kind) for tc, T, apex, kind in jumps]

    layers = dict(ground=(TILE, SPEED), mid=(420, 30.0), near=(360, 12.0), far=(300, 5.0), sky=(300, 2.5))
    css = []
    for name, (tile, speed) in layers.items():
        css.append(f"@keyframes {name}{{to{{transform:translateX({-tile * U}px)}}}}")
        css.append(f".{name}{{animation:{name} {tile / (speed * pace):g}s linear infinite}}")
    css += [
        jump_keyframes(timed, period), f".jump{{animation:jump {period:g}s linear infinite}}",
        f"@keyframes fr{{0%{{opacity:1}}{100 / 6:.4f}%,100%{{opacity:0}}}}",
        f".f{{opacity:0;animation:fr {6 * frame_s:g}s step-end infinite}}.f0{{opacity:1}}",
    ]
    css += [f".f{i}{{animation-delay:{i * frame_s:g}s}}" for i in range(1, 6)]
    css += [
        "@keyframes z{0%,55%{opacity:1;transform:translate(0,0)}80%{opacity:0;transform:translate(-16px,-18px)}"
        "81%{opacity:0;transform:translate(8px,10px)}100%{opacity:1;transform:translate(0,0)}}",
        ".z{animation:z 5s ease-in-out infinite}.z2{animation-delay:.7s}.z3{animation-delay:1.4s}",
        "@keyframes tw{0%,100%{opacity:1}50%{opacity:.15}}",
        ".tw{animation:tw 3.2s steps(2,end) infinite}.tw2{animation-delay:1.1s}.tw3{animation-delay:2.1s}",
        "@keyframes shoot{0%,93%{opacity:0;transform:translate(0,0)}94%{opacity:1}100%{opacity:0;transform:translate(-150px,75px)}}",
        ".shoot{opacity:0;animation:shoot 17s linear infinite}",
    ]
    for k in range(3):
        css.append(puff_keyframes(timed, k, period, 0.09 / pace))
        css.append(f".p{k}{{opacity:0;animation:p{k} {period:g}s step-end infinite}}")
    for place in range(4):
        kf, digit_period = counter_keyframes(timed, place, pitch, period)
        css.append(kf)
        css.append(f".c{place}{{animation:c{place} {digit_period:g}s step-end infinite}}")
    css.append("@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
    c.raw("<style>" + "".join(css) + "</style>")

    label_px, lw = text_cells(label + " ")
    hx, hy = W - 6 - (lw + 1 + 4 * 6 - 1), GROUND + 5
    c.raw("<defs>")
    for i, colour in enumerate(P["sky"][1:], 1):
        dither(c, f"d{i}", colour)
    dither(c, "h0", P["halo"][0])
    dither(c, "h1", P["halo"][1], sparse=True)
    c.raw(f'<clipPath id="r"><rect width="{W * U}" height="{H * U}" rx="20"/></clipPath>')
    for place in range(4):
        x = hx + lw + 1 + (3 - place) * 6
        c.raw(f'<clipPath id="k{place}"><rect x="{x * U}" y="{hy * U}" width="{5 * U}" height="{7 * U}"/></clipPath>')
    c.raw("</defs>")
    c.raw('<g clip-path="url(#r)">')

    # sky
    bands = [0, 16, 30, 42, 52, 62, 72, GROUND]
    for i, colour in enumerate(P["sky"]):
        c.rect(0, bands[i], W, bands[i + 1] - bands[i], colour)
    for i in range(1, 7):
        c.rect(0, bands[i] - 2, W, 2, f"url(#d{i})")

    mx, my, mr = 252, 24, 15
    if night:
        rnd = random.Random(21)
        stars = []
        while len(stars) < 70:
            x, y = rnd.randrange(3, W - 3), rnd.randrange(2, 58)
            if (x - mx) ** 2 + (y - my) ** 2 < (mr + 11) ** 2 or (10 < x < 136 and 4 < y < 62):
                continue
            stars.append((x, y))
        c.pixels(stars[:28], P["star_dim"])
        for k, colour in enumerate(P["stars"]):
            c.pixels(stars[28 + k * 10:38 + k * 10], colour)
        for k, cls in enumerate(("tw", "tw tw2", "tw tw3")):
            c.raw(f'<g class="{cls}">')
            c.pixels(stars[58 + k * 4:62 + k * 4], P["stars"][k])
            c.raw("</g>")
        for x, y in ((146, 9), (203, 38), (286, 52), (176, 16)):
            c.pixels([(x, y - 1), (x - 1, y), (x, y), (x + 1, y), (x, y + 1)], "#ffffff")
        c.raw('<g class="shoot">')
        c.pixels([(196, 6), (197, 5)], "#ffffff")
        c.raw('<g opacity=".5">')
        c.pixels([(198, 5), (199, 4), (200, 4)], "#ffffff")
        c.raw("</g></g>")

    # moon or sun
    c.pixels(disc(mx, my, mr + 9), "url(#h1)")
    c.pixels(disc(mx, my, mr + 4), "url(#h0)")
    orb = disc(mx, my, mr)
    c.pixels(orb, P["orb"]["light"])
    if night:
        limb = {(x, y) for (x, y) in orb if (x + .5 - mx) + (y + .5 - my) < -3
                and (x + .5 - mx) ** 2 + (y + .5 - my) ** 2 > (mr - 3.2) ** 2}
        limb = {(2 * mx - x - 1, 2 * my - y - 1) for x, y in limb}   # shade the lower right
        c.pixels(limb, P["orb"]["mid"])
        for dx, dy, r in ((-5, -4, 2.6), (4, 3, 3.1), (-3, 6, 1.9), (6, -6, 1.6), (-9, 2, 1.5), (0, -9, 1.3)):
            crater = disc(mx + dx, my + dy, r) & orb
            c.pixels(crater, P["orb"]["mid"])
            c.pixels({(x, y) for (x, y) in crater if (x - 1, y) not in crater or (x, y - 1) not in crater}, P["orb"]["dark"])
    else:
        c.pixels(disc(mx, my, mr - 1) - disc(mx - 1.5, my - 1.5, mr - 4), P["orb"]["mid"])

    # drifting cloud layer
    c.raw('<g class="sky">')
    shapes = [] if night else [(30, 2, CLOUD), (150, 20, CLOUD), (268, 36, CLOUD), (205, 6, CLOUD)]
    for x, y, rows in shapes:
        for base in (0, 300):
            px = {(a + x + base, b + y) for a, b in cells(rows)}
            c.pixels(px, P["wisp"]["base"])
            edge = {(a, b) for (a, b) in px if (a, b + 1) not in px} if not night else {(a, b) for (a, b) in px if (a, b - 1) not in px}
            c.pixels(edge, P["wisp"]["rim"])
    c.raw("</g>")

    # mesas
    for name, base, buttes in (
        ("far", 76, [(40, 14, 64, 8), (118, 8, 61, 11), (152, 5, 67, 6), (215, 18, 63, 9), (268, 6, 68, 5)]),
        ("near", 80, [(70, 20, 71, 5), (190, 10, 68, 7), (300, 26, 72, 4)]),
    ):
        tile = layers[name][0]
        tops, shade = mesa(tile, base, buttes)
        by = {}
        for x in range(tile + W):
            for y in range(tops[x % tile], GROUND):
                by.setdefault(shade(x, y), []).append((x, y))
        c.raw(f'<g class="{name}">')
        for k in ("base", "dark", "lit", "rim"):
            c.pixels(by.get(k, []), P[name][k])
        c.raw("</g>")

    # low dune with scrub, just behind the running lane
    tile = layers["mid"][0]
    M = P["mid"]

    def dune(x):
        a = 2 * math.pi * (x % tile) / tile
        return 81 + round(1.3 * math.sin(2 * a) + 0.9 * math.sin(5 * a + 2))

    c.raw('<g class="mid">')
    c.pixels([(x, y) for x in range(tile + W) for y in range(dune(x), GROUND)], M["base"])
    c.pixels([(x, dune(x)) for x in range(tile + W)], M["rim"])
    for x, rows, lo, hi in ((24, BUSH, "bush", "bush_hi"), (96, ROCK, "rock", "rock_hi"), (150, FAR_CACTUS, "bush", "bush_hi"),
                            (205, BUSH, "bush", "bush_hi"), (262, ROCK, "rock", "rock_hi"), (318, FAR_CACTUS, "bush", "bush_hi"),
                            (372, BUSH, "bush", "bush_hi")):
        for base in (0, tile):
            if x + base > tile + W:
                continue
            px = {(a + x + base, b + dune(x + len(rows[0]) // 2) - len(rows) + 1) for a, b in cells(rows)}
            c.pixels(px, M[lo])
            c.pixels({(a, b) for (a, b) in px if (a, b - 1) not in px}, M[hi])
    c.raw("</g>")

    # ground and cacti
    G = P["ground"]
    world_w = TILE + W
    c.raw('<g class="ground">')
    c.rect(0, GROUND, world_w, H - GROUND, G["base"])
    c.rect(0, GROUND, world_w, 1, G["top"])
    c.rect(0, GROUND + 1, world_w, 1, G["second"])
    rnd = random.Random(5)
    grit, crack, glint = [], [], []
    for _ in range(110):
        x, y, n = rnd.randrange(TILE), rnd.randrange(GROUND + 3, H - 1), rnd.choice((1, 2, 2, 3, 4))
        bucket = rnd.choice((grit, grit, grit, crack))
        for k in range(n):
            for base in (0, TILE):
                if x + k + base < world_w:
                    bucket.append((x + k + base, y))
    for _ in range(26):
        x = rnd.randrange(TILE)
        for base in (0, TILE):
            if x + base < world_w:
                glint.append((x + base, GROUND + 2))
    c.pixels(grit, G["grit"])
    c.pixels(crack, G["crack"])
    c.pixels(glint, G["second"])
    centre = DINO_X + HIP[0] + 1.5
    for tc, T, apex, kind in jumps:
        colours = cactus_colours(kind)
        w, h = len(CACTI[kind][0]), len(CACTI[kind])
        wx = round(centre - w / 2 + SPEED * tc) % TILE
        for base in (0, TILE):
            if wx + base < world_w:
                c.coloured(colours, P["cactus"], wx + base, GROUND - h)
                c.pixels({(x + wx + base - 1, GROUND) for x in range(w + 2)}, G["second"])
    c.raw("</g>")

    # landing dust
    for k, rows in enumerate(PUFFS):
        c.raw(f'<g class="p{k}">')
        c.pixels({(x + DINO_X + 14 - 4 * k, y + GROUND - len(rows)) for x, y in cells(rows)}, P["puff"])
        c.raw("</g>")

    # the dino
    oy = GROUND - DINO_H
    palette = dict(DINO_COLOURS, o=P["outline"])
    c.raw('<g class="jump">')
    if night:
        for rows, x, y, cls in ((Z_S, DINO_X + 19, oy + 2, "z"), (Z_M, DINO_X + 11, oy - 8, "z z2"), (Z_L, DINO_X + 2, oy - 19, "z z3")):
            c.raw(f'<g class="{cls}">')
            c.pixels({(a + x, b + y) for a, b in cells(rows)}, P["z"])
            c.raw("</g>")
    for i in range(6):
        c.raw(f'<g class="f f{i}">')
        c.coloured(dino_frame(i, night), palette, DINO_X, oy)
        c.raw("</g>")
    c.raw("</g>")

    # title, bevelled
    T = P["title"]
    tp, _ = text_cells("unlux", TITLE, 2)
    big = {(16 + x * 3 + a, 8 + y * 3 + b) for x, y in tp for a in range(3) for b in range(3)}
    c.pixels({(x + 2, y + 2) for x, y in big}, T["drop"])
    c.pixels(big, T["base"])
    c.pixels({(x, y) for (x, y) in big if (x, y + 1) not in big or (x + 1, y) not in big}, T["shade"])
    c.pixels({(x, y) for (x, y) in big if (x, y - 1) not in big}, T["hi"])
    cp, _ = text_cells("i build shi sometimes")
    c.pixels({(x + 17, y + 54) for x, y in cp}, P["title"]["drop"])
    c.pixels({(x + 16, y + 53) for x, y in cp}, P["cap"])

    # counter
    c.pixels(label_px, P["hud"], 1, hx, hy)
    for place in range(4):
        x = hx + lw + 1 + (3 - place) * 6
        c.raw(f'<g clip-path="url(#k{place})"><g class="c{place}">')
        for d in range(10):
            c.pixels(cells(DIGITS[d]), P["hud"], 1, x, hy + d * pitch)
        c.raw("</g></g>")

    c.raw("</g></svg>")
    return "\n".join(c.parts)


def sheet():
    """Zoomed sprite sheet for eyeballing the dino."""
    out = ['<!doctype html>\n<html><body style="background:#1a2d63;margin:12px">']
    for night in (True, False):
        c = Canvas()
        palette = dict(DINO_COLOURS, o=(NIGHT if night else DAY)["outline"])
        bg = "#1a2d63" if night else "#a3dff5"
        c.raw(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {6 * 52 * U} {50 * U}" shape-rendering="crispEdges" '
              f'style="display:block;width:100%;margin-bottom:12px"><rect width="100%" height="100%" fill="{bg}"/>')
        for i in range(6):
            c.coloured(dino_frame(i, night), palette, 4 + i * 52, 4)
        c.rect(0, 48, 6 * 52, 2, "#000000")
        c.raw("</svg>")
        out.append("\n".join(c.parts))
    out.append("</body></html>")
    return "\n".join(out)


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    jumps = fit_jumps()
    for tc, T, apex, kind in jumps:
        print(f"  {kind:6} at {tc:4.1f}s  hop {apex}px over {T:.2f}s")
    for name, svg in (("hero-dark.svg", hero(True, jumps)), ("hero-light.svg", hero(False, jumps))):
        with open(os.path.join(out, name), "w") as f:
            f.write(svg)
        print(name, len(svg), "bytes")
    if "--sheet" in sys.argv:
        with open(os.path.join(out, "sheet.html"), "w") as f:
            f.write(sheet())
