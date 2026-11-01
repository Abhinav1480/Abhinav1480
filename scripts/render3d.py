"""render3d.py — software 3D renderer + animated SVG generator.

Real 3D math (rotation matrices, perspective projection, back-face culling,
painter's depth sort, Lambert + rim + specular shading), baked into SMIL
flipbooks inside the SVGs so animations actually play on GitHub (which strips
JS/CSS/iframe from rendered READMEs). Every text string is width-checked.

Run from the repo root:  python render3d.py --preview  (also writes PNGs)
"""
import math
import os
import xml.etree.ElementTree as ET

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
os.makedirs(ASSETS, exist_ok=True)

# ── palette (charcoal + crimson, from the master brief) ──────────────────────
WHITE = "#F5F6FA"
GRAY = "#9298AA"
CRIMSON = "#FF4D30"
CORAL = "#FF718A"
AMBER = "#FFC857"
TEAL = "#43C9B7"
BLUE = "#5B8DEF"
ORANGE = "#FF8A45"
BG0 = "#0B0B11"
BG1 = "#14141B"
LINE = "#2A2A33"
SANS = "Segoe UI, Verdana, DejaVu Sans, sans-serif"
MONO = "Consolas, SF Mono, DejaVu Sans Mono, monospace"

# ── tiny color helpers ───────────────────────────────────────────────────────
def hx(c):
    return tuple(int(c[i : i + 2], 16) for i in (1, 3, 5))

def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))

def to_hex(c):
    return "#%02X%02X%02X" % c

# ── rotation matrices ────────────────────────────────────────────────────────
def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def unit(v):
    n = np.linalg.norm(v)
    return v / n if n else v

# ── mesh builders (verts: Nx3 array, faces: list of index tuples) ────────────
def icosahedron(subdiv=0):
    phi = (1 + math.sqrt(5)) / 2
    v = [(-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
         (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
         (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
         (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
         (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    verts = [np.array(p, dtype=float) / math.sqrt(1 + phi * phi) for p in v]
    for _ in range(subdiv):
        nv, nf, cache = [], [], {}
        for a, b, c in f:
            def mid(p, q):
                key = (min(p, q), max(p, q))
                if key not in cache:
                    cache[key] = len(nv)
                    nv.append(unit((verts[p] + verts[q]) / 2))
                return cache[key]
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        verts, f = nv, nf
    return np.array(verts), f

def octahedron():
    v = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    f = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
         (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    return np.array(v, dtype=float), f

def tetrahedron():
    v = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
    f = [(0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2)]
    return np.array(v, dtype=float) / math.sqrt(3), f

def torus(seg=18, side=8, R=1.75, r=0.26):
    v, f = [], []
    for i in range(seg):
        u = 2 * math.pi * i / seg
        cu, su = math.cos(u), math.sin(u)
        for j in range(side):
            w = 2 * math.pi * j / side
            cw, sw = math.cos(w), math.sin(w)
            v.append(((R + r * cw) * cu, (R + r * cw) * su, r * sw))
    for i in range(seg):
        for j in range(side):
            a = i * side + j
            b = ((i + 1) % seg) * side + j
            c = ((i + 1) % seg) * side + (j + 1) % side
            d = i * side + (j + 1) % side
            f.append((a, b, c, d))
    return np.array(v, dtype=float), f

# ── renderer ─────────────────────────────────────────────────────────────────
CAM = np.array([0.0, 0.0, 0.0])
LIGHT = np.array([3.0, 5.0, 3.0])   # above, right, between camera and scene

def render_frame(objs, t, W, H, K):
    """objs: list of dicts {verts, faces, pos(3,), scale, spin(t)->3x3,
    base, dark, rim, spec}.  Returns list of (color_hex, stroke, pts, z)."""
    polys = []
    for o in objs:
        R = o["spin"](t)
        V = o["verts"] @ R.T * o["scale"] + np.array(o["pos"], dtype=float)
        for fidx in o["faces"]:
            pts = V[list(fidx)]
            n = unit(np.cross(pts[1] - pts[0], pts[2] - pts[0]))
            c = pts.mean(axis=0)
            view = unit(CAM - c)
            if float(np.dot(n, view)) <= 0.03:
                continue  # back-face cull
            ldir = unit(LIGHT - c)
            diff = max(0.0, float(np.dot(n, ldir)))
            half = unit(ldir + view)
            spec = max(0.0, float(np.dot(n, half))) ** 26
            rim = max(0.0, 1.0 - float(np.dot(n, view))) ** 3
            col = mix(hx(o["dark"]), hx(o["base"]), 0.14 + 0.86 * diff)
            col = mix(col, hx(o["rim"]), min(1.0, rim * 0.85))
            if o.get("specular"):
                col = mix(col, hx(WHITE), min(1.0, spec * 0.55))
            z = float(c[2])
            # project
            scr = []
            behind = False
            for p in pts:
                if p[2] <= 0.6:
                    behind = True
                    break
                scr.append((W / 2 + p[0] / p[2] * K, H / 2 - p[1] / p[2] * K))
            if behind:
                continue
            polys.append((to_hex(col), to_hex(mix(hx(o["base"]), hx(WHITE), 0.4)),
                          scr, z))
    polys.sort(key=lambda p: -p[3])  # painter's: far first
    return polys

def polys_to_svg(polys):
    out = []
    for fill, stroke, pts, _z in polys:
        pts_s = " ".join("%.1f,%.1f" % (x, y) for x, y in pts)
        out.append(f'<polygon points="{pts_s}" fill="{fill}" stroke="{stroke}" '
                   f'stroke-width="0.7" stroke-opacity="0.45" stroke-linejoin="round"/>')
    return "".join(out)

def flipbook(frames, T, N):
    """SMIL flipbook: frame i visible during [i/N, (i+1)/N) of each cycle."""
    out = []
    for i, frame in enumerate(frames):
        base = "1" if i == 0 else "0"
        begin = f"{i * T / N:.3f}s"
        kt = f"0;{1 / N:.4f};1"
        out.append(f'<g opacity="{base}">'
                   f'<animate attributeName="opacity" values="1;0;0" keyTimes="{kt}" '
                   f'dur="{T:.2f}s" begin="{begin}s" repeatCount="indefinite"/>'
                   f'{frame}</g>')
    return "".join(out)

COMMON_STYLE = ('<style>@media (prefers-reduced-motion:reduce){animate,'
                'animateTransform,animateMotion{display:none}*{animation:none!important}}'
                '</style>')

def write(name, svg):
    path = os.path.join(ASSETS, name)
    ET.fromstring(svg)  # hard fail on invalid XML
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"  wrote {name} ({len(svg) / 1024:.0f} KiB)")

# ── text width guard (approx Verdana metrics; rejects overflow) ──────────────
def tw(s, size, bold=True):
    w = 0.0
    for ch in s:
        if ch == " ":
            w += 0.28
        elif ch.isupper():
            w += 0.69 if bold else 0.63
        elif ch.isdigit() or ch in ".,:;-+/()":
            w += 0.58 if bold else 0.53
        else:
            w += 0.60 if bold else 0.55
    return w * size

def check(tag, s, size, limit, bold=True):
    w = tw(s, size, bold)
    assert w <= limit, f"{tag}: {w:.0f}px > {limit}px limit — shorten text"
    return w

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ── 1. HERO ──────────────────────────────────────────────────────────────────
def hero_scene(t, T=4.0, CYW=-2.20, CZ=7.0):
    """Object list for the hero at time t. Kept module-level so the QA bounds
    check can sample it without duplicating build_hero's parameters."""
    ico_v, ico_f = icosahedron(1)
    tor_v, tor_f = torus(18, 8)
    tet_v, tet_f = tetrahedron()

    def spin_crystal(t):
        return ry(t * 2 * math.pi / T) @ rx(0.30)

    def spin_torus(t):
        return rx(1.18) @ rz(t * 2 * math.pi / T)

    objs = [
        dict(verts=tor_v, faces=tor_f, pos=(0, CYW, CZ), scale=1.55,
             spin=spin_torus, base=TEAL, dark="#0B2624", rim="#C9FFF6",
             specular=True),
        dict(verts=ico_v, faces=ico_f, pos=(0, CYW, CZ), scale=1.6,
             spin=spin_crystal, base=CRIMSON, dark="#33100C", rim="#FFD9A0",
             specular=True),
    ]
    for phase, base, dark, rim in [(0.0, BLUE, "#101C3A", "#CFE2FF"),
                                   (0.5, AMBER, "#3A2C08", "#FFF3D6")]:
        a = t * 2 * math.pi / T + phase * math.pi
        pos = (math.cos(a) * 2.7, CYW + math.sin(a * 2.0) * 0.4,
               CZ + math.sin(a) * 2.7 - 0.3)
        objs.append(dict(
            verts=tet_v, faces=tet_f, pos=pos, scale=0.75,
            spin=lambda t, p=phase: ry(t * 2 * math.pi / T * 1.6 + p) @
            rx(t * 2 * math.pi / T * 1.1 + p),
            base=base, dark=dark, rim=rim, specular=False))
    return objs


def build_hero(N=36, T=4.0, K=340.0, CZ=7.0, CYW=-2.20, W=1280, H=600,
               horizon=380):
    print("hero")
    QT = "Abhinav Nakka"
    check("hero-name", QT, 70, 1180)
    caption = "FULL-STACK DEVELOPER  ·  3D WEB  ·  B.TECH CSE @ VJIT, HYDERABAD"
    check("hero-caption", caption, 17, 940, bold=False)

    def scene(t):
        return hero_scene(t, T=T, CYW=CYW, CZ=CZ)

    print(f"  rendering {N} 3D frames…")
    frames = [polys_to_svg(render_frame(scene(i * T / N), t, W, H, K))
              for i, t in enumerate([i * T / N for i in range(N)])]

    # static layers ------------------------------------------------------------
    # background
    bg = (f'<defs>'
          f'<linearGradient id="bgG" x1="0" y1="0" x2="0" y2="1">'
          f'<stop offset="0" stop-color="{BG0}"/><stop offset="0.72" stop-color="{BG1}"/>'
          f'<stop offset="1" stop-color="#1B1013"/></linearGradient>'
          f'<linearGradient id="sunG" x1="0" y1="0" x2="0" y2="1">'
          f'<stop offset="0" stop-color="{AMBER}"/><stop offset="0.55" stop-color="{CORAL}"/>'
          f'<stop offset="1" stop-color="{CRIMSON}"/></linearGradient>'
          f'<linearGradient id="nameG" x1="0" y1="0" x2="1" y2="0.25">'
          f'<stop offset="0" stop-color="{AMBER}"/><stop offset="0.6" stop-color="{CORAL}"/>'
          f'<stop offset="1" stop-color="{CRIMSON}"/></linearGradient>'
          f'<linearGradient id="gridG" x1="0" y1="0" x2="0" y2="1">'
          f'<stop offset="0" stop-color="{CRIMSON}" stop-opacity="0"/>'
          f'<stop offset="0.3" stop-color="{CRIMSON}" stop-opacity="0.5"/>'
          f'<stop offset="1" stop-color="{CORAL}" stop-opacity="0.85"/></linearGradient>'
          f'<radialGradient id="glowG" cx="0.5" cy="0.5" r="0.5">'
          f'<stop offset="0" stop-color="{CRIMSON}" stop-opacity="0.34"/>'
          f'<stop offset="0.55" stop-color="{CRIMSON}" stop-opacity="0.10"/>'
          f'<stop offset="1" stop-color="{CRIMSON}" stop-opacity="0"/></radialGradient>'
          f'<linearGradient id="sweepG" x1="0" y1="0" x2="1" y2="0">'
          f'<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
          f'<stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.16"/>'
          f'<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
          f'<filter id="soft" x="-40%" y="-40%" width="180%" height="180%">'
          f'<feGaussianBlur stdDeviation="7"/></filter>'
          f'<filter id="soft2" x="-60%" y="-60%" width="220%" height="220%">'
          f'<feGaussianBlur stdDeviation="16"/></filter>'
          f'</defs>'
          f'<rect width="{W}" height="{H}" fill="url(#bgG)"/>')

    # sun behind the name
    sun = (f'<g><circle cx="640" cy="150" r="95" fill="url(#sunG)" opacity="0.9">'
           f'<animate attributeName="opacity" values="0.78;0.95;0.78" dur="5s" '
           f'repeatCount="indefinite"/></circle>'
           f'<circle cx="640" cy="150" r="95" fill="url(#sunG)" filter="url(#soft2)" '
           f'opacity="0.45"/></g>'
           f'<g clip-path="url(#sunClip)">')
    bars = ""
    for i in range(7):
        yb = 150 - 12 + i * 15
        bh = 3 + i * 1.6
        bars += (f'<rect x="530" y="{yb}" width="220" height="{bh}" fill="{BG0}" '
                 f'opacity="0.85"/>')
    sun += f'<clipPath id="sunClip"><circle cx="640" cy="150" r="95"/></clipPath>'
    sun += bars + "</g>"

    # perspective grid floor, horizontal lines flying toward the viewer
    grid = ""
    NL = 12
    TG = 2.8
    for i in range(NL):
        u0 = i / NL
        ks = [k / 8 for k in range(9)]
        us = [((u0 + k / 8) % 1.0) for k in range(9)]
        p = 1.9
        ys = [horizon + (H - horizon) * u ** p for u in us]
        ws = [0.5 + 2.6 * u for u in us]
        ops = [min(1.0, u * 2.3) * 0.55 for u in us]
        kt = ";".join(f"{k:.3f}" for k in ks)
        vy = ";".join(f"{y:.1f}" for y in ys)
        vw = ";".join(f"{w:.2f}" for w in ws)
        vo = ";".join(f"{o:.2f}" for o in ops)
        grid += (f'<line x1="-160" y1="{ys[0]:.1f}" x2="1440" y2="{ys[0]:.1f}" '
                 f'stroke="url(#gridG)" stroke-width="{ws[0]:.2f}" '
                 f'opacity="{ops[0]:.2f}">'
                 f'<animate attributeName="y1" values="{vy}" keyTimes="{kt}" dur="{TG}s" '
                 f'repeatCount="indefinite"/>'
                 f'<animate attributeName="y2" values="{vy}" keyTimes="{kt}" dur="{TG}s" '
                 f'repeatCount="indefinite"/>'
                 f'<animate attributeName="stroke-width" values="{vw}" keyTimes="{kt}" '
                 f'dur="{TG}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values="{vo}" keyTimes="{kt}" '
                 f'dur="{TG}s" repeatCount="indefinite"/></line>')
    # vertical converging lines (static)
    for k in range(-8, 9):
        xb = 640 + k * 118
        grid += (f'<line x1="640" y1="{horizon}" x2="{xb}" y2="{H}" '
                 f'stroke="url(#gridG)" stroke-width="1" opacity="0.35"/>')
    # crimson haze along the horizon
    grid += (f'<ellipse cx="640" cy="{horizon}" rx="620" ry="34" fill="{CRIMSON}" '
             f'opacity="0.16" filter="url(#soft2)">'
             f'<animate attributeName="opacity" values="0.12;0.2;0.12" dur="5s" '
             f'repeatCount="indefinite"/></ellipse>')

    # glow + floor reflection behind the crystal cluster
    glow = (f'<circle cx="640" cy="434" r="230" fill="url(#glowG)">'
            f'<animate attributeName="r" values="170;195;170" dur="4s" '
            f'repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.75;1;0.75" dur="4s" '
            f'repeatCount="indefinite"/></circle>'
            f'<ellipse cx="640" cy="588" rx="160" ry="13" fill="{CRIMSON}" opacity="0.22">'
            f'<animate attributeName="opacity" values="0.15;0.28;0.15" dur="4s" '
            f'repeatCount="indefinite"/></ellipse>')

    # particles
    import random
    rng = random.Random(7)
    parts = ""
    for i in range(26):
        px = rng.uniform(30, W - 30)
        py = rng.uniform(60, H - 40)
        pr = rng.uniform(0.8, 2.1)
        pc = rng.choice([CORAL, AMBER, WHITE])
        po = rng.uniform(0.25, 0.7)
        dur = rng.uniform(3.4, 6.5)
        dy = rng.uniform(26, 52)
        delay = -rng.uniform(0, dur)
        parts += (f'<circle cx="{px:.0f}" cy="{py:.0f}" r="{pr:.1f}" fill="{pc}" '
                  f'opacity="{po:.2f}">'
                  f'<animate attributeName="cy" values="{py:.0f};{py - dy:.0f}" '
                  f'dur="{dur:.1f}s" begin="{delay:.2f}s" repeatCount="indefinite"/>'
                  f'<animate attributeName="opacity" values="{po * 0.3:.2f};{po:.2f};'
                  f'{po * 0.3:.2f}" dur="{dur:.1f}s" begin="{delay:.2f}s" '
                  f'repeatCount="indefinite"/></circle>')

    # name + caption + light sweep
    name_shadow = (f'<text x="640" y="178" text-anchor="middle" font-family="{SANS}" '
                   f'font-size="70" font-weight="700" letter-spacing="1.5" fill="{BG0}" '
                   f'opacity="0.55" filter="url(#soft)">{QT}</text>')
    name = (f'<text x="640" y="178" text-anchor="middle" font-family="{SANS}" '
            f'font-size="70" font-weight="700" letter-spacing="1.5" fill="url(#nameG)" '
            f'stroke="{BG0}" stroke-width="1.2" stroke-opacity="0.6" paint-order="stroke">'
            f'{QT}</text>')
    caption_t = (f'<text x="640" y="212" text-anchor="middle" font-family="{MONO}" '
                 f'font-size="16" letter-spacing="3.5" fill="{GRAY}">{caption}</text>')
    # light sweep: rotate via the group, translate via the rect's own transform
    sweep = (f'<g transform="rotate(-8 640 150)"><rect x="-300" y="30" width="320" '
             f'height="220" fill="url(#sweepG)">'
             f'<animateTransform attributeName="transform" type="translate" '
             f'values="-340 0; 1700 0" dur="7s" begin="1.5s" repeatCount="indefinite"/>'
             f'</rect></g>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="heroT">'
           f'<title id="heroT">Abhinav Nakka - Full-Stack Developer, 3D Web, '
           f'B.Tech CSE at VJIT Hyderabad - animated 3D hero</title>'
           f'{COMMON_STYLE}'
           f'<desc>A dark charcoal scene with a perspective grid floor, a crimson sun '
           f'behind the name, and a slowly rotating faceted crystal ringed by a tilted '
           f'torus and two orbiting shards.</desc>'
           f'{bg}'
           f'{sun}'
           f'{grid}'
           f'{glow}'
           f'{sweep}'
           f'{flipbook(frames, T, N)}'
           f'{parts}'
           f'{name_shadow}{name}{caption_t}'
           f'</svg>')
    write("hero.svg", svg)

# ── 2. DIVIDER ───────────────────────────────────────────────────────────────
def build_divider(N=24, T=3.0, W=780, H=76):
    print("divider")
    oct_v, oct_f = octahedron()

    def scene(t):
        return [dict(verts=oct_v, faces=oct_f, pos=(0, 0, 7.0), scale=1.3,
                     spin=lambda t: ry(t * 2 * math.pi / T) @ rx(0.5),
                     base=TEAL, dark="#0B2624", rim="#C9FFF6", specular=True)]

    frames = [polys_to_svg(render_frame(scene(i * T / N), t, W, H, 170))
              for i, t in enumerate([i * T / N for i in range(N)])]
    # flanking lines with marching dashes
    lines = ""
    for x0, x1, w in ((24, 300, 24), (480, 756, 24)):
        lines += (f'<line x1="{x0}" y1="38" x2="{x1}" y2="38" stroke="{LINE}" '
                  f'stroke-width="1.4" stroke-dasharray="{w} 10">'
                  f'<animate attributeName="stroke-dashoffset" values="0;-34" '
                  f'dur="2.2s" repeatCount="indefinite"/></line>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="divT">'
           f'<title id="divT">Section divider</title>{COMMON_STYLE}'
           f'<rect width="{W}" height="{H}" fill="none"/>'
           f'{lines}'
           f'{flipbook(frames, T, N)}'
           f'</svg>')
    write("divider.svg", svg)

# ── 3. 3D PORTAL BANNER ──────────────────────────────────────────────────────
def build_portal(N=24, T=4.0, W=840, H=240):
    print("portal")
    ico_v, ico_f = icosahedron(1)
    head = "ENTER THE 3D EXPERIENCE"
    check("portal-head", head, 32, 520)
    sub = "abhinav1480.github.io/Abhinav1480"
    check("portal-sub", sub, 15, 320, bold=False)
    note = ("INTERACTIVE WEBGL  ·  DRAG TO ORBIT  ·  WORKS ON DESKTOP "
            "&amp; MODERN MOBILE")
    check("portal-note", note, 11.5, 560, bold=False)

    def scene(t):
        return [dict(verts=ico_v, faces=ico_f, pos=(6.35, 0.2, 7.4), scale=1.9,
                     spin=lambda t: ry(t * 2 * math.pi / T) @ rx(0.35),
                     base=CRIMSON, dark="#33100C", rim="#FFD9A0", specular=True)]

    frames = [polys_to_svg(render_frame(scene(i * T / N), t, W, H, 300))
              for i, t in enumerate([i * T / N for i in range(N)])]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="portalT">'
           f'<title id="portalT">Enter the 3D experience - interactive WebGL</title>'
           f'{COMMON_STYLE}'
           f'<defs><linearGradient id="pnl" x1="0" y1="0" x2="1" y2="1">'
           f'<stop offset="0" stop-color="{BG1}"/><stop offset="1" stop-color="#201018"/>'
           f'</linearGradient>'
           f'<linearGradient id="pbd" x1="0" y1="0" x2="1" y2="0">'
           f'<stop offset="0" stop-color="{CRIMSON}"/><stop offset="0.5" stop-color="{AMBER}"/>'
           f'<stop offset="1" stop-color="{TEAL}"/></linearGradient>'
           f'<radialGradient id="pgl" cx="0.5" cy="0.5" r="0.5">'
           f'<stop offset="0" stop-color="{CRIMSON}" stop-opacity="0.3"/>'
           f'<stop offset="1" stop-color="{CRIMSON}" stop-opacity="0"/></radialGradient>'
           f'</defs>'
           f'<rect width="{W}" height="{H}" rx="20" fill="url(#pnl)"/>'
           f'<rect x="3" y="3" width="{W - 6}" height="{H - 6}" rx="18" fill="none" '
           f'stroke="url(#pbd)" stroke-width="2" stroke-dasharray="30 12">'
           f'<animate attributeName="stroke-dashoffset" values="0;-42" dur="2.6s" '
           f'repeatCount="indefinite"/></rect>'
           f'<rect x="3" y="3" width="{W - 6}" height="{H - 6}" rx="18" fill="none" '
           f'stroke="{CRIMSON}" stroke-width="5" opacity="0.10">'
           f'<animate attributeName="opacity" values="0.06;0.16;0.06" dur="4s" '
           f'repeatCount="indefinite"/></rect>'
           f'<circle cx="680" cy="120" r="130" fill="url(#pgl)"/>'
           f'<text x="48" y="98" font-family="{SANS}" font-size="32" font-weight="700" '
           f'letter-spacing="1.5" fill="url(#pbd)">{head}</text>'
           f'<text x="48" y="132" font-family="{MONO}" font-size="15" fill="{GRAY}">'
           f'{sub}</text>'
           f'<text x="48" y="164" font-family="{MONO}" font-size="11.5" '
           f'letter-spacing="1.4" fill="{GRAY}" opacity="0.75">{note}</text>'
           f'<text x="48" y="200" font-family="{MONO}" font-size="13" '
           f'fill="{CRIMSON}">▸ LAUNCH</text>'
           f'{flipbook(frames, T, N)}'
           f'</svg>')
    write("portal-3d.svg", svg)

# ── 4. PROJECT CARDS ────────────────────────────────────────────────────────
def build_card(fname, num, name, chip, desc_lines, accent, slug, W=840, H=280):
    print(f"card {name}")
    check(f"card-name[{fname}]", name, 30, 520)
    for i, ln in enumerate(desc_lines):
        check(f"card-desc[{fname}][{i}]", ln, 16.5, W - 240, bold=False)
    check(f"card-chip[{fname}]", chip, 11.5, 150, bold=False)
    check(f"card-slug[{fname}]", slug, 12.5, 640, bold=False)

    ac = accent
    # extruded 3D number: dark offset copies + gradient face
    num_g = ""
    for k in range(6, 0, -1):
        num_g += (f'<text x="{43 + k * 1.1:.1f}" y="{94 + k * 1.1:.1f}" '
                  f'font-family="{SANS}" font-size="52" font-weight="700" '
                  f'fill="{BG0}" opacity="0.5">{num}</text>')
    num_g += (f'<text x="43" y="94" font-family="{SANS}" font-size="52" '
              f'font-weight="700" fill="url(#numG_{num})" stroke="{BG0}" '
              f'stroke-width="0.8" stroke-opacity="0.5" paint-order="stroke">{num}</text>')

    descs = "".join(
        f'<text x="44" y="{y}" font-family="{SANS}" font-size="16.5" fill="{GRAY}">'
        f'{esc(ln)}</text>'
        for y, ln in zip((162, 188, 214), desc_lines))

    chipw = tw(chip, 11.5, bold=False) + 26
    chipx = W - 40 - chipw

    # right-side orbiting rings decoration
    rings = (f'<g>'
             f'<ellipse cx="748" cy="116" rx="56" ry="20" fill="none" stroke="{ac}" '
             f'stroke-width="1.3" opacity="0.55">'
             f'<animateTransform attributeName="transform" type="rotate" '
             f'from="0 748 116" to="360 748 116" dur="9s" repeatCount="indefinite"/>'
             f'</ellipse>'
             f'<circle cx="748" cy="96" r="3.4" fill="{ac}">'
             f'<animateTransform attributeName="transform" type="rotate" '
             f'from="0 748 116" to="360 748 116" dur="9s" repeatCount="indefinite"/>'
             f'</circle>'
             f'<circle cx="748" cy="116" r="30" fill="none" stroke="{ac}" '
             f'stroke-width="1" opacity="0.3" stroke-dasharray="4 6">'
             f'<animate attributeName="stroke-dashoffset" values="0;-20" dur="3s" '
             f'repeatCount="indefinite"/></circle>'
             f'</g>')

    # corner brackets
    br = 22
    corners = ""
    for cx, cy, dx, dy in ((16, 16, 1, 1), (W - 16, 16, -1, 1),
                           (16, H - 16, 1, -1), (W - 16, H - 16, -1, -1)):
        corners += (f'<path d="M {cx + dx * br} {cy} L {cx} {cy} L {cx} {cy + dy * br}" '
                    f'fill="none" stroke="{ac}" stroke-width="2" opacity="0.6"/>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="{fname}T">'
           f'<title id="{fname}T">{esc(name)} - {esc(chip)}</title>{COMMON_STYLE}'
           f'<defs>'
           f'<linearGradient id="numG_{num}" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0" stop-color="{mix(hx(ac), hx(WHITE), 0.35) and to_hex(mix(hx(ac), hx(WHITE), 0.35))}"/>'
           f'<stop offset="1" stop-color="{ac}"/></linearGradient>'
           f'<linearGradient id="edge_{fname}" x1="0" y1="0" x2="1" y2="0">'
           f'<stop offset="0" stop-color="{ac}" stop-opacity="0.85"/>'
           f'<stop offset="0.5" stop-color="{mix(hx(WHITE), hx(ac), 0.25) and to_hex(mix(hx(WHITE), hx(ac), 0.25))}"/>'
           f'<stop offset="1" stop-color="{ac}" stop-opacity="0.85"/></linearGradient>'
           f'<linearGradient id="sheen_{fname}" x1="0" y1="0" x2="1" y2="0">'
           f'<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
           f'<stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.09"/>'
           f'<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
           f'<clipPath id="clip_{fname}"><rect width="{W}" height="{H}" rx="20"/></clipPath>'
           f'</defs>'
           f'<rect width="{W}" height="{H}" rx="20" fill="{BG1}"/>'
           f'<g clip-path="url(#clip_{fname})">'
           f'<path d="M 0 0 H {W} V 4 H 0 Z" fill="{ac}" opacity="0.5"/>'
           f'{rings}'
           f'<g transform="rotate(-18 720 140)"><rect x="-200" y="30" width="170" '
           f'height="{H}" fill="url(#sheen_{fname})">'
           f'<animateTransform attributeName="transform" type="translate" '
           f'values="-260 0; 1120 0" dur="8s" begin="2s" repeatCount="indefinite"/>'
           f'</rect></g>'
           f'</g>'
           f'{corners}'
           f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="19" fill="none" '
           f'stroke="url(#edge_{fname})" stroke-width="1.6" stroke-dasharray="28 10" '
           f'opacity="0.9">'
           f'<animate attributeName="stroke-dashoffset" values="0;-38" dur="2.4s" '
           f'repeatCount="indefinite"/></rect>'
           f'{num_g}'
           f'<text x="44" y="130" font-family="{SANS}" font-size="30" font-weight="700" '
           f'letter-spacing="0.5" fill="{WHITE}">{esc(name)}</text>'
           f'{descs}'
           f'<text x="44" y="252" font-family="{MONO}" font-size="12.5" fill="{ac}" '
           f'opacity="0.9">{esc(slug)}</text>'
           f'<rect x="{chipx}" y="34" width="{chipw}" height="24" rx="12" '
           f'fill="{ac}" fill-opacity="0.14" stroke="{ac}" stroke-opacity="0.45" '
           f'stroke-width="1"/>'
           f'<text x="{chipx + chipw / 2}" y="50.5" text-anchor="middle" '
           f'font-family="{MONO}" font-size="11.5" letter-spacing="1.6" fill="{ac}">'
           f'{chip}</text>'
           f'</svg>')
    write(fname, svg)

# ── PIL previews (geometry QA before pushing) ────────────────────────────────
def previews():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL missing — skipping previews")
        return
    print("previews")
    # re-render hero + divider + portal frames to PNG with the same engine
    specs = [
        ("hero.png", build_hero_for_preview, {}),
        ("divider.png", build_divider_for_preview, {}),
        ("portal.png", build_portal_for_preview, {}),
    ]
    for fname, fn, kw in specs:
        img, note = fn()
        img.save(os.path.join(HERE, fname))
        print(f"  wrote {fname} {img.size} — {note}")

def build_hero_for_preview(t=0.9):
    from PIL import Image, ImageDraw
    W, H, K, horizon = 1280, 600, 340.0, 380
    T = 4.0
    objs = hero_scene(t, T=T)
    polys = render_frame(objs, t, W, H, K)
    img = Image.new("RGB", (W, H), (11, 11, 17))
    d = ImageDraw.Draw(img)
    # sun
    d.ellipse([545, 55, 735, 245], fill=(255, 113, 138))
    # grid
    for k in range(-8, 9):
        xb = 640 + k * 118
        d.line([(640, horizon), (xb, H)], fill=(60, 22, 26), width=1)
    for i in range(12):
        u = (i / 12 + t / 4.0) % 1.0
        y = horizon + (H - horizon) * u ** 1.9
        d.line([(-160, y), (1440, y)], fill=(140, 50, 45), width=1)
    # 3d polys
    for fill, stroke, pts, _z in polys:
        col = hx(fill)
        d.polygon([tuple(p) for p in pts], fill=col, outline=hx(stroke))
    # name + caption placement boxes (rough)
    d.rectangle([640 - tw("Abhinav Nakka", 70) / 2, 178 - 56,
                 640 + tw("Abhinav Nakka", 70) / 2, 178], outline=(255, 200, 120))
    d.rectangle([640 - 480, 200, 640 + 480, 218], outline=(120, 120, 130))
    return img, f"t={t:.2f} polys={len(polys)}"

def build_divider_for_preview(t=0.5):
    from PIL import Image, ImageDraw
    W, H = 780, 76
    oct_v, oct_f = octahedron()
    objs = [dict(verts=oct_v, faces=oct_f, pos=(0, 0, 7.0), scale=1.3,
                 spin=lambda t: ry(t) @ rx(0.5), base=TEAL, dark="#0B2624",
                 rim="#C9FFF6", specular=True)]
    polys = render_frame(objs, t, W, H, 170)
    img = Image.new("RGB", (W, H), (20, 20, 27))
    d = ImageDraw.Draw(img)
    d.line([(24, 38), (300, 38)], fill=(60, 60, 75))
    d.line([(480, 38), (756, 38)], fill=(60, 60, 75))
    for fill, stroke, pts, _z in polys:
        d.polygon([tuple(p) for p in pts], fill=hx(fill), outline=hx(stroke))
    return img, f"polys={len(polys)}"

def build_portal_for_preview(t=0.6):
    from PIL import Image, ImageDraw
    W, H = 840, 240
    ico_v, ico_f = icosahedron(1)
    objs = [dict(verts=ico_v, faces=ico_f, pos=(6.35, 0.2, 7.4), scale=1.9,
                 spin=lambda t: ry(t) @ rx(0.35), base=CRIMSON, dark="#33100C",
                 rim="#FFD9A0", specular=True)]
    polys = render_frame(objs, t, W, H, 300)
    img = Image.new("RGB", (W, H), (20, 20, 27))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=20, outline=(255, 77, 48))
    for fill, stroke, pts, _z in polys:
        d.polygon([tuple(p) for p in pts], fill=hx(fill), outline=hx(stroke))
    d.rectangle([48, 70, 560, 200], outline=(110, 110, 125))
    return img, f"polys={len(polys)}"

if __name__ == "__main__":
    import sys
    build_hero()
    build_divider()
    build_portal()
    build_card("card-examos.svg", "01", "ExamOS", "STUDY PLATFORM",
               ["Study productivity platform centralizing PDFs, notes and timetables,",
                "with a built-in PDF viewer and Pomodoro timer."],
               CRIMSON, "github.com/Abhinav1480/ExamOS")
    build_card("card-gymbeast.svg", "02", "Gym Beast", "FITNESS PROJECT",
               ["Fitness / gym-related software project.",
                "Repo link and further details coming soon."],
               ORANGE, "repo link coming soon")
    build_card("card-sutradhar.svg", "03", "Sutradhar", "COLLABORATIVE",
               ["A collaborative project, built together with other developers."],
               TEAL, "github.com/vedant7007/sutradhar")
    build_card("card-clinicdesk.svg", "04", "Clinic Desk", "HACKATHON PROJECT",
               ["Hackathon project focused on healthcare and clinic management."],
               BLUE, "github.com/vedant7007/clinic-desk")
    if "--preview" in sys.argv:
        previews()
    print("done")
