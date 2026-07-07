"""Nesting cut simulation -- the real target workflow.

Carve many prismatic parts from ONE foam block and part them off. Demonstrates the
governing constraint: a hot wire has no pen-up. The wire spans the full block width
and always cuts where it passes through foam, so:

  * TRAVEL between parts = route the path BELOW the block (in air -> no cut).
  * each interior part needs a LEAD-IN SLIT from an edge (cut in, trace, back out).

The whole nest is ONE continuous path: through-foam segments are cuts, in-air
segments are free travel.

Run:  python3 sim/nest_sim.py
Out:  sim/out/nest_plan.png   (2D cut plan: cuts solid, travel dashed)
      sim/out/nest_parts.png  (3D tray of prismatic parts)
      sim/out/nest_cut.gif    (animated continuous cut)
"""
import os
import sys
import subprocess

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402
from matplotlib.patches import Rectangle, Polygon as MPoly  # noqa: E402
import imageio.v2 as imageio                             # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(os.path.dirname(HERE), "cad")
sys.path.insert(0, CAD)
import machine_params as M                               # noqa: E402
from build123d import (BuildPart, BuildSketch, BuildLine, Polyline,  # noqa: E402
                       make_face, extrude, Plane, Pos, export_stl)

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

# foam block cross-section in the Y-Z (cut) plane
Y0, Y1 = M.BED_LEN / 2 - M.FOAM_Y / 2, M.BED_LEN / 2 + M.FOAM_Y / 2   # 75 .. 425
Z0, Z1 = M.BED_TOP, M.BED_TOP + M.FOAM_Z                              # 40 .. 190
ZC = (Z0 + Z1) / 2
Z_AIR = Z0 - 18.0            # travel line, below the block -> wire in air, no cut


# --- shape library (returns list of (Y, Z) verts, CCW) -------------------
def reg_poly(cy, cz, r, n, rot=0.0):
    a = np.deg2rad(rot) + np.linspace(0, 2 * np.pi, n, endpoint=False)
    return [(cy + r * np.cos(t), cz + r * np.sin(t)) for t in a]


def star(cy, cz, ro, ri, n=5, rot=90.0):
    pts = []
    for k in range(2 * n):
        r = ro if k % 2 == 0 else ri
        t = np.deg2rad(rot) + k * np.pi / n
        pts.append((cy + r * np.cos(t), cz + r * np.sin(t)))
    return pts


# a row of geometric parts nested across the block
SHAPES = [
    reg_poly(125, ZC, 42, 6, rot=90),     # hexagon
    reg_poly(210, ZC, 46, 3, rot=90),     # triangle
    reg_poly(292, ZC, 40, 4, rot=45),     # diamond
    star(370, ZC, 46, 20, 5, rot=90),     # star
]


def roll_to_lowest(loop):
    """Rotate a closed loop so it starts at its lowest (min-Z) vertex."""
    k = int(np.argmin([p[1] for p in loop]))
    return loop[k:] + loop[:k]


# --- continuous single-path toolpath -------------------------------------
def build_path():
    """Ordered vertices with a per-segment cut flag (segment ENDING at vertex i)."""
    verts = [(Y0 - 20, Z_AIR)]        # enter from the left, in air
    cut = [False]

    def go(pt, is_cut):
        verts.append(pt)
        cut.append(is_cut)

    for loop in SHAPES:
        lp = roll_to_lowest(loop)
        ly, lz = lp[0]
        go((ly, Z_AIR), False)        # travel under the part (air)
        go((ly, lz), True)            # lead-in slit up into the part
        for p in lp[1:] + [lp[0]]:    # trace the closed profile
            go(p, True)
        go((ly, Z_AIR), True)         # back out the same slit
    go((Y1 + 20, Z_AIR), False)       # exit right, in air
    return np.array(verts), np.array(cut, bool)


# --- 2D cut plan ---------------------------------------------------------
def plot_plan(verts, cut, name="nest_plan"):
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=120)
    ax.add_patch(Rectangle((Y0, Z0), Y1 - Y0, Z1 - Z0,
                           fc="#dfeaf5", ec="#3a86c8", lw=1.4, zorder=0))
    for loop in SHAPES:
        ax.add_patch(MPoly(loop, closed=True, fc="#b9d4ec", ec="#2f6da8",
                           lw=1.0, zorder=1))
    for i in range(1, len(verts)):
        y = [verts[i - 1][0], verts[i][0]]
        z = [verts[i - 1][1], verts[i][1]]
        if cut[i]:
            ax.plot(y, z, "-", color="#ff4d0a", lw=2.0, zorder=3)
        else:
            ax.plot(y, z, "--", color="#8a8f98", lw=1.2, zorder=2)
    ax.plot(*verts[0], "o", color="#0a7d2c", ms=8, zorder=4)
    ax.plot(*verts[-1], "s", color="#b00020", ms=7, zorder=4)
    ax.annotate("start", verts[0], textcoords="offset points", xytext=(-6, -14))
    ax.annotate("exit", verts[-1], textcoords="offset points", xytext=(-4, -14))
    ax.set_aspect("equal")
    ax.set_xlim(Y0 - 35, Y1 + 35)
    ax.set_ylim(Z_AIR - 8, Z1 + 12)
    ax.set_xlabel("Y  (U axis)")
    ax.set_ylabel("Z  (V axis)")
    ax.set_title("Nesting cut plan — one continuous path  "
                 "(solid = cut through foam, dashed = travel in air)")
    fig.tight_layout()
    p = os.path.join(OUT, f"{name}.png")
    fig.savefig(p)
    plt.close(fig)
    return p


# --- 3D tray of prismatic parts ------------------------------------------
def render_parts(name="nest_parts", rot=(62, 0, 28)):
    palette = [(0.90, 0.49, 0.13), (0.20, 0.63, 0.79),
               (0.55, 0.34, 0.64), (0.30, 0.69, 0.31)]
    lines = []
    x0 = M.CUT_WIDTH / 2 - M.FOAM_X / 2
    for i, loop in enumerate(SHAPES):
        with BuildPart() as bp:
            with BuildSketch(Plane.YZ):
                with BuildLine():
                    Polyline(*loop, loop[0])
                make_face()
            extrude(amount=M.FOAM_X)
        part = Pos(x0, 0, 0) * bp.part
        stl = f"{name}_{i}.stl"
        export_stl(part, os.path.join(OUT, stl))
        r, g, b = palette[i % len(palette)]
        lines.append(f'color([{r},{g},{b}]) import("{stl}");')
    scad = os.path.join(OUT, f"{name}.scad")
    with open(scad, "w") as f:
        f.write("\n".join(lines) + "\n")
    png = os.path.join(OUT, f"{name}.png")
    cam = f"0,0,0,{rot[0]},{rot[1]},{rot[2]},0"
    subprocess.run(
        ["openscad", "-o", png, "--imgsize=1100,760", "--autocenter", "--viewall",
         "--projection=p", "--colorscheme=Tomorrow", f"--camera={cam}", f"{name}.scad"],
        check=True, cwd=OUT,
    )
    return png


# --- animation of the continuous cut -------------------------------------
def animate(verts, cut, name="nest_cut", steps_per_seg=4):
    # densify path for smooth motion, carrying the cut flag
    P, C = [], []
    for i in range(1, len(verts)):
        a, b = verts[i - 1], verts[i]
        for s in np.linspace(0, 1, steps_per_seg, endpoint=False):
            P.append(a + (b - a) * s)
            C.append(cut[i])
    P.append(verts[-1]); C.append(cut[-1])
    P = np.array(P)

    frames = []
    stride = 2
    for f in range(0, len(P), stride):
        fig, ax = plt.subplots(figsize=(9, 4.2), dpi=100)
        ax.add_patch(Rectangle((Y0, Z0), Y1 - Y0, Z1 - Z0,
                               fc="#eef4fa", ec="#3a86c8", lw=1.3, zorder=0))
        for loop in SHAPES:
            ax.add_patch(MPoly(loop, closed=True, fc="#dbe8f4", ec="#9db8d2",
                               lw=0.8, zorder=1))
        # draw path traced so far
        for i in range(1, f + 1):
            if C[i]:
                ax.plot([P[i - 1][0], P[i][0]], [P[i - 1][1], P[i][1]],
                        "-", color="#ff4d0a", lw=2.0, zorder=3)
        # current cut point (the wire's YZ position; wire itself spans X)
        ax.plot(*P[f], "o", color="#ff2a00", ms=9, zorder=5)
        ax.set_aspect("equal")
        ax.set_xlim(Y0 - 35, Y1 + 35)
        ax.set_ylim(Z_AIR - 8, Z1 + 12)
        ax.set_xlabel("Y  (U)")
        ax.set_ylabel("Z  (V)")
        ax.set_title("Continuous nest cut — no pen-up (travel goes below the block)")
        fig.tight_layout()
        fig.canvas.draw()
        frames.append(np.asarray(fig.canvas.buffer_rgba()).copy())
        plt.close(fig)
    gif = os.path.join(OUT, f"{name}.gif")
    imageio.mimsave(gif, frames, duration=0.05, loop=0)
    return gif


if __name__ == "__main__":
    verts, cut = build_path()
    print("plan:", plot_plan(verts, cut))
    print("parts:", render_parts())
    print("anim:", animate(verts, cut))
