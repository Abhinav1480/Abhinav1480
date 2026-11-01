"""Numeric QA for render3d.py — measures 3D-cluster bounding boxes across a
full rotation cycle and flags anything leaving the canvas or colliding with
the text zones. Run:  python qa_bounds.py"""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("r3", os.path.join(HERE, "render3d.py"))
r3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r3)
render_frame = r3.render_frame
hero_scene = r3.hero_scene


def scan(name, scene, T, W, H, K, samples=12, zones=None):
    x0, y0, x1, y1 = W, H, 0, 0
    worst = None
    for i in range(samples):
        t = T * i / samples
        polys = render_frame(scene(t), t, W, H, K)
        for _f, _s, pts, _z in polys:
            for px, py in pts:
                x0 = min(x0, px); y0 = min(y0, py)
                x1 = max(x1, px); y1 = max(y1, py)
                out = px < -2 or px > W + 2 or py < -2 or py > H + 2
                if out:
                    worst = worst or (round(px), round(py), round(t, 2))
    msg = (f"{name}: bbox = ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})  "
           f"size = {x1 - x0:.0f} x {y1 - y0:.0f}")
    if worst:
        msg += f"  *** OVERFLOW at {worst}"
    if zones:
        for zname, (zx0, zy0, zx1, zy1) in zones.items():
            if not (x1 < zx0 or x0 > zx1 or y1 < zy0 or y0 > zy1):
                msg += f"  *** OVERLAPS zone '{zname}'"
    print(msg)
    return worst is None


ok = True

# HERO: canvas 1280x600, text occupies the band y in [120..218]
ok &= scan("hero  ", lambda t: hero_scene(t, T=4.0), 4.0, 1280, 600, 340.0,
           zones={"caption-band": (0, 120, 1280, 218)})

# DIVIDER: 780x76
def div_scene(t):
    oct_v, oct_f = r3.octahedron()
    return [dict(verts=oct_v, faces=oct_f, pos=(0, 0, 7.0), scale=1.3,
                 spin=lambda t: r3.ry(t) @ r3.rx(0.5), base=r3.TEAL,
                 dark="#0B2624", rim="#C9FFF6", specular=True)]
ok &= scan("divider", div_scene, 3.0, 780, 76, 170.0)

# PORTAL: 840x240, crystal sits right of the text column (x > ~470)
def por_scene(t):
    tet_v, tet_f = r3.tetrahedron()
    ico_v, ico_f = r3.icosahedron(0)
    return [dict(verts=tet_v, faces=tet_f, pos=(6.35, 0.2, 7.4), scale=1.9,
                 spin=lambda t: r3.ry(t * 1.4) @ r3.rx(0.4), base=r3.CRIMSON,
                 dark="#33100C", rim="#FFD9A0", specular=True)]
ok &= scan("portal ", por_scene, 4.0, 840, 240, 300.0,
           zones={"text-column": (0, 0, 470, 240)})

print("\nALL WITHIN BOUNDS" if ok else "\nISSUES FOUND")
