"""Kinematic cut simulation for the 4-axis hot-wire cutter.

Two deliverables:
  1. The RULED SOLIDS the machine can actually produce -- rendered via OpenSCAD:
       - extrusion  (identical L/R face profiles)  -> straight prism
       - taper/loft (different  L/R face profiles)  -> the 4-axis payoff
  2. An animated GIF of the wire sweeping the perimeter, painting the ruled
     surface as it goes (matplotlib).

Run:  python3 sim/cut_sim.py
Out:  sim/out/extrusion.png, sim/out/taper.png, sim/out/cut_sweep.gif
"""
import os
import sys
import subprocess

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # noqa: E402
import imageio.v2 as imageio             # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(os.path.dirname(HERE), "cad")
sys.path.insert(0, CAD)                  # so we share the single source of truth
import machine_params as M               # noqa: E402

from build123d import (BuildPart, BuildSketch, BuildLine, Polyline,  # noqa: E402
                       make_face, loft, Plane, export_stl)

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

# profiles are centred on the foam block face
CY = M.BED_LEN / 2
CZ = M.BED_TOP + M.FOAM_Z / 2


def rect(w, h, cy=CY, cz=CZ):
    """Rectangle profile as (Y, Z) corners, CCW."""
    return [(cy - w / 2, cz - h / 2), (cy + w / 2, cz - h / 2),
            (cy + w / 2, cz + h / 2), (cy - w / 2, cz + h / 2)]


# --- 1. ruled solids -----------------------------------------------------
def loft_solid(profL, profR):
    """Loft a solid across X between the left-face and right-face profiles."""
    with BuildPart() as bp:
        with BuildSketch(Plane.YZ.offset(M.WIRE_X_L)):
            with BuildLine():
                Polyline(*profL, profL[0])          # closed
            make_face()
        with BuildSketch(Plane.YZ.offset(M.WIRE_X_R)):
            with BuildLine():
                Polyline(*profR, profR[0])
            make_face()
        loft()
    return bp.part


def render_solid(solid, name, rot=(60, 0, 30)):
    stl = os.path.join(OUT, f"{name}.stl")
    export_stl(solid, stl)
    scad = os.path.join(OUT, f"{name}.scad")
    with open(scad, "w") as f:
        f.write(f'color([0.35,0.6,0.88]) import("{name}.stl");\n')
    png = os.path.join(OUT, f"{name}.png")
    cam = f"0,0,0,{rot[0]},{rot[1]},{rot[2]},0"
    subprocess.run(
        ["openscad", "-o", png, "--imgsize=900,720", "--autocenter", "--viewall",
         "--projection=p", "--colorscheme=Tomorrow", f"--camera={cam}", f"{name}.scad"],
        check=True, cwd=OUT,
    )
    return png


# --- 2. animated sweep ---------------------------------------------------
def perimeter(poly, n):
    """n points evenly along the closed polygon perimeter, param by arc-length."""
    P = np.array(poly + [poly[0]], float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    ts = np.linspace(0, cum[-1], n, endpoint=False)
    out = []
    for t in ts:
        k = min(max(np.searchsorted(cum, t) - 1, 0), len(seg) - 1)
        f = (t - cum[k]) / seg[k] if seg[k] > 0 else 0.0
        out.append(P[k] + f * (P[k + 1] - P[k]))
    return np.array(out)                              # (n, 2) as (Y, Z)


def frame_segments():
    """Line segments (p0, p1) drawing the static machine frame."""
    segs = []
    for sx in (M.LX, M.RX):
        for y in (0, M.BED_LEN):
            segs.append([(sx, y, 0), (sx, y, M.TOWER_H)])            # uprights
        for z in (M.EXTR / 2, M.TOWER_H - M.EXTR / 2):
            segs.append([(sx, 0, z), (sx, M.BED_LEN, z)])            # y-rails
    for y in (0, M.BED_LEN):
        segs.append([(M.LX, y, M.EXTR / 2), (M.RX, y, M.EXTR / 2)])  # base ties
    return segs


def box_edges(cx, cy, cz, sx, sy, sz):
    c = np.array([[cx - sx / 2, cx + sx / 2], [cy - sy / 2, cy + sy / 2],
                  [cz - sz / 2, cz + sz / 2]])
    pts = [(c[0][i], c[1][j], c[2][k]) for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    idx = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7),
           (0, 4), (1, 5), (2, 6), (3, 7)]
    return [[pts[a], pts[b]] for a, b in idx]


def animate(profL, profR, name="cut_sweep", n=64):
    ptsL = perimeter(profL, n)
    ptsR = perimeter(profR, n)
    fr = frame_segments()
    foam = box_edges(M.CUT_WIDTH / 2, M.BED_LEN / 2, M.BED_TOP + M.FOAM_Z / 2,
                     M.FOAM_X, M.FOAM_Y, M.FOAM_Z)
    frames = []
    for i in range(n + 1):
        fig = plt.figure(figsize=(7.5, 6.0), dpi=100)
        ax = fig.add_subplot(111, projection="3d")
        ax.add_collection3d(Line3DCollection(fr, colors="#8a8f98", linewidths=1.2))
        ax.add_collection3d(Line3DCollection(foam, colors="#3a86c8", linewidths=0.8,
                                             alpha=0.4))
        # ruled surface painted so far
        swept = [[(M.WIRE_X_L, ptsL[j][0], ptsL[j][1]),
                  (M.WIRE_X_R, ptsR[j][0], ptsR[j][1])] for j in range(min(i, n))]
        if swept:
            ax.add_collection3d(Line3DCollection(swept, colors="#ff7a2f",
                                                 linewidths=0.6, alpha=0.28))
        # current wire + carriages
        if i < n:
            L = (M.WIRE_X_L, ptsL[i][0], ptsL[i][1])
            R = (M.WIRE_X_R, ptsR[i][0], ptsR[i][1])
            ax.add_collection3d(Line3DCollection([[L, R]], colors="#ff4d0a",
                                                 linewidths=2.4))
            ax.scatter(*zip(L, R), color="#243b53", s=22)
        ax.set_xlim(M.LX, M.RX)
        ax.set_ylim(0, M.BED_LEN)
        ax.set_zlim(0, M.TOWER_H)
        ax.set_box_aspect((M.RX - M.LX, M.BED_LEN, M.TOWER_H))
        ax.view_init(elev=22, azim=-58)
        ax.set_xlabel("X  (wire axis)")
        ax.set_ylabel("Y  (U)")
        ax.set_zlabel("Z  (V)")
        ax.set_title("4-axis hot-wire sweep — wire paints a ruled loft")
        fig.tight_layout()
        fig.canvas.draw()
        frames.append(np.asarray(fig.canvas.buffer_rgba()).copy())
        plt.close(fig)
    gif = os.path.join(OUT, f"{name}.gif")
    imageio.mimsave(gif, frames, duration=0.06, loop=0)
    return gif


if __name__ == "__main__":
    # extrusion: identical profiles -> straight prism
    prism = loft_solid(rect(200, 150), rect(200, 150))
    p1 = render_solid(prism, "extrusion")
    print("rendered", p1)

    # taper/loft: different profiles -> ruled 4-axis solid
    profL = rect(220, 150, CY, CZ)
    profR = rect(120, 90, CY + 60, CZ + 30)
    taper = loft_solid(profL, profR)
    p2 = render_solid(taper, "taper")
    print("rendered", p2)

    gif = animate(profL, profR)
    print("animated", gif)
