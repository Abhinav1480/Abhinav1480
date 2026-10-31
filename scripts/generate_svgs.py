#!/usr/bin/env python3
"""Generate every SVG asset for the Abhinav1480/Abhinav1480 profile README.

Design system: dark charcoal + crimson accent, slow purposeful motion only.
GitHub renders READMEs with JS and external CSS stripped, so all animation
lives inside the SVG files themselves (SMIL <animate> + transform). Every SVG
paints its own background rect so it reads correctly in GitHub light mode too.

Every drawing call runs through an overflow check (measured with Verdana, a
wider fallback font, so nothing clips in a browser that lacks Segoe UI) and an
XML well-formedness check.
"""

import os
import random
from xml.etree import ElementTree

from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))

# ---------------------------------------------------------------- palette ---
INK = "#101014"
CARD = "#14141B"
CARD_ALT = "#1B1B26"
BORDER = "#2A2A33"
BORDER_SOFT = "#333340"
WHITE = "#F5F5F5"
GRAY = "#9298AA"
GRAY_DIM = "#4A4D57"
CRIMSON = "#FF4D30"
CORAL = "#FF718A"
ORANGE = "#FF8A45"
AMBER = "#FFC857"
TEAL = "#43C9B7"
BLUE = "#5B8DEF"

SANS = "'Segoe UI', Inter, 'Helvetica Neue', Arial, sans-serif"
MONO = "'ui-monospace', 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

FONT_BOLD = "C:/Windows/Fonts/verdanab.ttf"
FONT_REG = "C:/Windows/Fonts/verdana.ttf"

_checks = []


def text_w(s, size, bold=True):
    """Measure text width with a wide fallback font (conservative)."""
    path = FONT_BOLD if bold else FONT_REG
    font = ImageFont.truetype(path, size)
    return font.getlength(s)


def check(label, text, size, max_w, bold=True):
    """Record an overflow check; returns the measured width."""
    w = text_w(text, size, bold)
    _checks.append((label, text, size, int(w), int(max_w), w <= max_w))
    return w


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write(name, svg):
    path = os.path.join(ASSETS, name)
    ElementTree.fromstring(svg)  # explode now rather than ship broken markup
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg)
    print("  wrote", name, f"({len(svg) / 1024:.1f} KiB)")


# ------------------------------------------------------------------ hero ---
def build_hero():
    W, H = 1200, 470
    rng = random.Random(7)

    # --- perspective grid floor (the "3D" stage) ---
    vx, vy = 600, 250  # vanishing point
    rays = []
    for x in range(-360, 1561, 120):
        rays.append(f'<line x1="{x}" y1="{H}" x2="{vx}" y2="{vy}" stroke="{BLUE}" stroke-width="1" opacity="0.07"/>')
    horizontals = [318, 344, 376, 414, 460]
    for y in horizontals:
        rays.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="{CRIMSON}" stroke-width="1" opacity="0.09"/>')

    # --- floating particles (ambient, slow drift) ---
    parts = []
    for _ in range(14):
        x = rng.randint(70, 1130)
        y = rng.randint(46, 360)
        r = round(rng.uniform(1.4, 2.8), 1)
        col = rng.choice([CRIMSON, CORAL, ORANGE, AMBER, TEAL, BLUE])
        op = round(rng.uniform(0.16, 0.40), 2)
        dx, dy = rng.randint(-5, 5), rng.randint(-4, 4)
        dur, beg = rng.randint(9, 14), round(rng.uniform(0, 8), 1)
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}" opacity="{op}">'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;{dx} {dy};0 0" keyTimes="0;0.5;1" dur="{dur}s" begin="-{beg}s" '
            f'repeatCount="indefinite"/></circle>'
        )

    # --- isometric cubes (real depth, three shaded faces each) ---
    def cube(cx, cy, s, top, left, right, dur, beg):
        w = s * 0.866
        return (
            f'<g>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;0 -6;0 0" keyTimes="0;0.5;1" dur="{dur}s" begin="-{beg}s" '
            f'repeatCount="indefinite"/>'
            f'<polygon points="{cx},{cy - s} {cx + w},{cy - s / 2} {cx},{cy} {cx - w},{cy - s / 2}" fill="{top}"/>'
            f'<polygon points="{cx - w},{cy - s / 2} {cx},{cy} {cx},{cy + s} {cx - w},{cy + s / 2}" fill="{left}"/>'
            f'<polygon points="{cx + w},{cy - s / 2} {cx},{cy} {cx},{cy + s} {cx + w},{cy + s / 2}" fill="{right}"/>'
            f'<polygon points="{cx},{cy - s} {cx + w},{cy - s / 2} {cx},{cy} {cx - w},{cy - s / 2}" '
            f'fill="none" stroke="{INK}" stroke-width="0.6" opacity="0.35"/>'
            f'</g>'
        )

    cubes = (
        cube(150, 398, 26, CORAL, "#B32E1E", CRIMSON, 12, 0)
        + cube(1055, 402, 22, "#63D9C9", "#1E6B62", TEAL, 13, 4)
        + cube(1095, 118, 18, "#FFD98A", "#8A6420", AMBER, 11, 6.5)
        + cube(92, 118, 18, "#9CC0FF", "#2E4B9A", BLUE, 14, 2)
    )

    # --- rotating roles (three texts, 12s loop, gentle rise + fade) ---
    roles = ["Full-Stack Developer", "UI Engineer", "Creative Developer"]
    role_svgs = []
    for i, role in enumerate(roles):
        check(f"hero-role[{i}]", role, 27, 360)
        begin = i * 4
        # role 1 carries base opacity=1 so non-SMIL renderers still show it
        base_op = "1" if i == 0 else "0"
        role_svgs.append(
            f'<text x="600" y="272" text-anchor="middle" font-family="{SANS}" font-size="27" '
            f'font-weight="600" letter-spacing="1.4" fill="#E9ECF2" opacity="{base_op}">{esc(role)}'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.29;0.34" '
            f'dur="12s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 10;0 0;0 0;0 -8" keyTimes="0;0.05;0.29;0.34" '
            f'dur="12s" begin="{begin}s" repeatCount="indefinite"/></text>'
        )

    # --- name with vertical white->gray gradient ---
    check("hero-name", "Abhinav Nakka", 76, 1080)
    name = (
        f'<text x="600" y="216" text-anchor="middle" font-family="{SANS}" font-size="76" '
        f'font-weight="700" letter-spacing="1" fill="url(#nameGrad)">Abhinav Nakka</text>'
    )

    # --- crimson accent line (draws in once, then the glow breathes) ---
    accent = (
        f'<line x1="512" y1="304" x2="688" y2="304" stroke="{CRIMSON}" stroke-width="6" '
        f'opacity="0.22" stroke-linecap="round" filter="url(#soft)">'
        f'<animate attributeName="opacity" values="0.12;0.3;0.12" dur="9s" repeatCount="indefinite"/></line>'
        f'<line x1="512" y1="304" x2="688" y2="304" stroke="{CRIMSON}" stroke-width="3" '
        f'stroke-linecap="round" stroke-dasharray="176" stroke-dashoffset="0">'
        f'<animate attributeName="stroke-dashoffset" from="176" to="0" dur="1.2s" begin="0.2s" fill="freeze"/></line>'
        f'<rect x="596" y="299" width="8" height="8" rx="1.5" fill="{CRIMSON}" transform="rotate(45 600 303)"/>'
    )

    caption = "B.TECH CSE &#183; 3RD YEAR &#183; VJIT, HYDERABAD"
    check("hero-caption", "B.TECH CSE · 3RD YEAR · VJIT, HYDERABAD", 15, 700, bold=False)

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="heroTitle">
  <title id="heroTitle">Abhinav Nakka - Full-Stack Developer, UI Engineer, Creative Developer</title>
  <defs>
    <linearGradient id="nameGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{WHITE}"/>
      <stop offset="1" stop-color="#AEB6C4"/>
    </linearGradient>
    <radialGradient id="glowGrad" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{CRIMSON}" stop-opacity="0.16"/>
      <stop offset="1" stop-color="{CRIMSON}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="gridFade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{INK}" stop-opacity="1"/>
      <stop offset="1" stop-color="{INK}" stop-opacity="0"/>
    </linearGradient>
    <filter id="soft" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="5"/>
    </filter>
    <clipPath id="gridClip"><rect x="0" y="286" width="{W}" height="184"/></clipPath>
  </defs>

  <rect width="{W}" height="{H}" fill="{INK}"/>

  <g clip-path="url(#gridClip)">
    {''.join(rays)}
    <rect x="0" y="286" width="{W}" height="184" fill="url(#gridFade)"/>
  </g>

  <ellipse cx="600" cy="196" rx="390" ry="150" fill="url(#glowGrad)">
    <animate attributeName="opacity" values="0.7;1;0.7" dur="10s" repeatCount="indefinite"/>
  </ellipse>

  {''.join(parts)}
  {cubes}

  <line x1="296" y1="266" x2="404" y2="266" stroke="{BORDER}" stroke-width="1.5" stroke-linecap="round"/>
  <line x1="796" y1="266" x2="904" y2="266" stroke="{BORDER}" stroke-width="1.5" stroke-linecap="round"/>

  {name}
  {''.join(role_svgs)}
  {accent}

  <text x="600" y="356" text-anchor="middle" font-family="{MONO}" font-size="15"
        letter-spacing="3" fill="{GRAY}">{caption}</text>
</svg>'''
    write("hero.svg", svg)


# --------------------------------------------------------------- buttons ---
def build_button(fname, label, accent):
    fs = 15
    tw = check(f"btn-{fname}", label, fs, 240) + 1.6 * len(label)
    w = int(tw + 78)
    h = 46
    ax = w - 27  # external-link arrow, 11x11
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{fname}Title">
  <title id="{fname}Title">{esc(label)}</title>
  <rect width="{w}" height="{h}" rx="{h // 2}" fill="{CARD}" stroke="{BORDER}" stroke-width="1.2"/>
  <circle cx="24" cy="23" r="4.5" fill="{accent}"/>
  <text x="42" y="29" font-family="{MONO}" font-size="{fs}" font-weight="700" letter-spacing="1.6"
        fill="#E8EAF0">{esc(label)}</text>
  <g transform="translate({ax}, 17)" stroke="{accent}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M0 11 L11 0 M0 0 H11 V11"/>
  </g>
</svg>'''
    write(fname, svg)


# ----------------------------------------------------------------- cards ---
def build_card(fname, num, name, chip, desc_lines, accent, slug):
    W, H = 780, 230
    check(f"card-name[{fname}]", name, 28, 560)
    for i, line in enumerate(desc_lines):
        check(f"card-desc[{fname}][{i}]", line, 15, W - 68, bold=False)
    check(f"card-chip[{fname}]", chip, 11, 170, bold=False)
    check(f"card-slug[{fname}]", slug, 11, W - 68, bold=False)

    chip_w = int(text_w(chip, 11) + 8 * len(chip) * 0 + 30)
    chip_x = W - 34 - chip_w

    descs = "".join(
        f'<text x="34" y="{y}" font-family="{SANS}" font-size="15" fill="{GRAY}">{esc(line)}</text>'
        for y, line in zip((142, 166, 190), desc_lines)
    )

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="{fname}Title">
  <title id="{fname}Title">{esc(name)}</title>
  <defs>
    <clipPath id="clip_{fname}"><rect x="0" y="0" width="{W}" height="{H}" rx="16"/></clipPath>
  </defs>

  <rect width="{W}" height="{H}" rx="16" fill="{CARD}" stroke="{BORDER}" stroke-width="1"/>

  <g clip-path="url(#clip_{fname})">
    <rect x="0" y="0" width="{W}" height="{H}" fill="none" stroke="{accent}" stroke-width="1.5"
          stroke-dasharray="16 28" opacity="0.3">
      <animate attributeName="stroke-dashoffset" from="0" to="880" dur="14s" repeatCount="indefinite"/>
    </rect>
  </g>

  <text x="34" y="54" font-family="{MONO}" font-size="13" letter-spacing="2" fill="{accent}">{num}</text>
  <text x="34" y="94" font-family="{SANS}" font-size="28" font-weight="700" letter-spacing="0.5" fill="{WHITE}">{esc(name)}</text>
  <rect x="34" y="106" width="34" height="3" rx="1.5" fill="{accent}"/>

  <rect x="{chip_x}" y="42" width="{chip_w}" height="24" rx="12" fill="{CARD_ALT}" stroke="{BORDER_SOFT}" stroke-width="1"/>
  <text x="{chip_x + chip_w / 2}" y="58" text-anchor="middle" font-family="{MONO}" font-size="11"
        letter-spacing="1.2" fill="{accent}">{esc(chip)}</text>

  {descs}

  <text x="34" y="212" font-family="{MONO}" font-size="11" letter-spacing="0.6" fill="{GRAY_DIM}">{esc(slug)}</text>
</svg>'''
    write(fname, svg)


# --------------------------------------------------------------- divider ---
def build_divider():
    W, H = 780, 16
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="divTitle">
  <title id="divTitle">Section divider</title>
  <defs>
    <linearGradient id="divGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{TEAL}"/>
      <stop offset="0.45" stop-color="{CRIMSON}"/>
      <stop offset="0.75" stop-color="{ORANGE}"/>
      <stop offset="1" stop-color="{AMBER}"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="{INK}"/>
  <line x1="30" y1="8" x2="750" y2="8" stroke="{BORDER}" stroke-width="1.25"/>
  <line x1="30" y1="8" x2="750" y2="8" stroke="url(#divGrad)" stroke-width="2" stroke-linecap="round"
        stroke-dasharray="70 690">
    <animate attributeName="stroke-dashoffset" from="760" to="0" dur="9s" repeatCount="indefinite"/>
  </line>
</svg>'''
    write("divider.svg", svg)


# ---------------------------------------------- snake placeholders (pre-run) ---
def build_snake_placeholders():
    """Static placeholders the snake workflow overwrites on its first run."""
    for fname, palette_note in (("github-snake.svg", "light"), ("github-snake-dark.svg", "dark")):
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="480" height="120" viewBox="0 0 480 120" role="img" aria-labelledby="snakeTitle">
  <title id="snakeTitle">Contribution snake placeholder</title>
  <rect width="480" height="120" rx="14" fill="{'#F6F8FA' if palette_note == 'light' else CARD}" stroke="{BORDER}" stroke-width="1"/>
  <text x="240" y="58" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{'#57606A' if palette_note == 'light' else GRAY}">contribution snake</text>
  <text x="240" y="78" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{'#8B949E' if palette_note == 'light' else GRAY_DIM}">appears after the first workflow run</text>
</svg>'''
        write(fname, svg)


def report():
    print("\n  overflow checks (measured with Verdana, a wide fallback font):")
    fails = 0
    for label, text, size, w, mx, ok in _checks:
        status = "ok " if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"  [{status}] {label:<26} {size:>3}px w={w:<5} max={mx}  {text[:52]!r}")
    if fails:
        raise SystemExit(f"\n  {fails} text overflow(s) - shorten copy or widen the canvas.")
    print(f"\n  all {len(_checks)} overflow checks passed; XML well-formed for every file.")


if __name__ == "__main__":
    os.makedirs(ASSETS, exist_ok=True)
    print("generating assets ->", ASSETS)
    build_hero()
    build_button("btn-portfolio.svg", "PORTFOLIO", CRIMSON)
    build_button("btn-linkedin.svg", "LINKEDIN", BLUE)
    build_button("btn-github.svg", "GITHUB", TEAL)
    build_card(
        "card-examos.svg", "01", "ExamOS", "STUDY PLATFORM",
        ["Study productivity platform centralizing PDFs, notes and timetables,",
         "with a built-in PDF viewer and Pomodoro timer."],
        CRIMSON, "github.com/Abhinav1480/ExamOS",
    )
    build_card(
        "card-gymbeast.svg", "02", "Gym Beast", "FITNESS PROJECT",
        ["Fitness / gym-related software project.",
         "Repo link and further details coming soon."],
        ORANGE, "repo link coming soon",
    )
    build_card(
        "card-sutradhar.svg", "03", "Sutradhar", "COLLABORATIVE",
        ["A collaborative project, built together with other developers."],
        TEAL, "github.com/vedant7007/sutradhar",
    )
    build_card(
        "card-clinicdesk.svg", "04", "Clinic Desk", "HACKATHON PROJECT",
        ["Hackathon project focused on healthcare and clinic management."],
        BLUE, "github.com/vedant7007/clinic-desk",
    )
    build_divider()
    build_snake_placeholders()
    report()
