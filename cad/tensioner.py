"""tensioner.py — constant-force wire tensioner subassembly.

Places the printed bracket + sled, an extension-spring stand-in pulling the sled toward the
back wall (-X), the clamped wire exiting the front (+X toward the block), and a set-screw
stand-in. Renders an iso.  py cad/tensioner.py -> build/tensioner_iso.png

The sled floats between the back wall and the front wall; the spring holds ~5 N and takes up
the wire's hot growth by sliding the sled -X. Shown mid-stroke.
"""
import os
import subprocess
from build123d import (Box, Cylinder, Pos, Rot, Align, export_stl,
                       Helix, sweep, Circle, Plane)
import machine_params as M
import tensioner_bracket as bracket
import tensioner_sled as sled
import wire as wire_mod


def _spring(x0, x1, z, od):
    """Helical extension-spring stand-in along +X from x0 to x1 (cylinder fallback)."""
    L = max(x1 - x0, 0.5)
    try:
        turns = max(int(L / 2.0), 3)
        h = Helix(pitch=L / turns, height=L, radius=od / 2)      # coil along +Z
        prof = Plane(origin=h @ 0.0, z_dir=h % 0.0) * Circle(0.55)
        coil = sweep(prof, path=h)
        return Pos(x0, 0, z) * Rot(0, 90, 0) * coil
    except Exception:
        return Pos((x0 + x1) / 2, 0, z) * Rot(0, 90, 0) * Cylinder(od / 2, L)

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")

COLORS = {
    "bracket":  (0.60, 0.62, 0.66),
    "sled":     (0.33, 0.45, 0.60),
    "spring":   (0.74, 0.76, 0.82),
    "wire":     (1.00, 0.35, 0.06),
    "setscrew": (0.22, 0.22, 0.25),
    "terminal": (0.80, 0.70, 0.25),
}
ALPHA = {"sled": 0.45}          # translucent so the spring + take-up gap read through it


def assembly(takeup=0.35):
    """takeup in [0,1]: fraction of stroke already consumed (0 = fully forward/taut)."""
    x_start = M.TENS_BACK + M.TENS_STROKE * (1 - takeup)    # sled back-face x (forward at takeup=0)
    z = M.TENS_WIRE_ZC
    sled_solid = Pos(x_start, 0, M.TENS_FLOOR) * sled.part()

    spring = _spring(M.TENS_BACK, x_start, z, M.TENS_SPRING_OD)   # back wall -> sled back

    wire_out_x = x_start + M.TENS_SLED_X
    wire = wire_mod.wire((wire_out_x, 0, z), (M.TENS_X + 45, 0, z), dia=1.5)

    ss_x = x_start + M.TENS_SLED_X / 2
    setscrew = Pos(ss_x, 0, M.TENS_FLOOR + M.TENS_SLED_Z) \
        * Cylinder(M.TENS_SET_TAP / 2 + 0.3, 8, align=(Align.CENTER, Align.CENTER, Align.MIN))

    term_x = x_start + M.TENS_SLED_X * 0.72
    terminal = Pos(term_x, M.TENS_SLED_Y / 2 - 5.0, M.TENS_FLOOR + M.TENS_SLED_Z + 3) \
        * Cylinder(M.TENS_HEATSET / 2 + 0.6, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))

    return {
        "bracket": bracket.part(),
        "sled": sled_solid,
        "spring": spring,
        "wire": wire,
        "setscrew": setscrew,
        "terminal": terminal,
    }


def render(parts, name="tensioner", size=(1200, 860), rot=(72, 0, 26)):
    os.makedirs(BUILD, exist_ok=True)
    lines = []
    for key, sol in parts.items():
        stl = f"{name}_{key}.stl"
        export_stl(sol, os.path.join(BUILD, stl))
        r, g, b = COLORS.get(key, (0.7, 0.7, 0.7))
        a = ALPHA.get(key, 1.0)
        lines.append(f'color([{r},{g},{b},{a}]) import("{stl}");')
    scad = os.path.join(BUILD, f"{name}.scad")
    with open(scad, "w") as f:
        f.write("\n".join(lines) + "\n")
    png = os.path.join(BUILD, f"{name}_iso.png")
    cam = f"0,0,0,{rot[0]},{rot[1]},{rot[2]},0"
    subprocess.run(
        ["openscad", "-o", png, f"--imgsize={size[0]},{size[1]}",
         "--autocenter", "--viewall", "--projection=p",
         "--colorscheme=Tomorrow", f"--camera={cam}", f"{name}.scad"],
        check=True, cwd=BUILD,
    )
    return png


def clip_y(s, cy=1.0):
    """Keep the y < cy half of a solid (mid-plane section)."""
    return s - Pos(0, cy, 0) * Box(600, 400, 600, align=(Align.CENTER, Align.MIN, Align.CENTER))


def schematic(name="tensioner_diagram", takeup=0.35):
    """Labeled cross-section (X-Z mid-plane) explaining how the tensioner works."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    X, H, F = M.TENS_X, M.TENS_H, M.TENS_FLOOR
    z = M.TENS_WIRE_ZC
    x0 = M.TENS_BACK + M.TENS_STROKE * (1 - takeup)      # sled back
    x1 = x0 + M.TENS_SLED_X                              # sled front
    grey, blue, stl, orn = "#8a8f98", "#3a6ea5", "#b0b3ba", "#ff4d0a"

    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=120)
    ax.add_patch(Rectangle((0, 0), X, F, fc=grey, ec="k", lw=0.8))                    # floor
    ax.add_patch(Rectangle((0, 0), M.TENS_BACK, H, fc=grey, ec="k", lw=0.8))          # back wall
    ax.add_patch(Rectangle((X - M.TENS_FRONT, 0), M.TENS_FRONT, H, fc=grey, ec="k", lw=0.8))  # front
    ax.add_patch(Rectangle((x0, F), M.TENS_SLED_X, M.TENS_SLED_Z, fc=blue, ec="k",
                           lw=0.8, alpha=0.85))                                        # sled
    # spring coil (back wall -> sled)
    xs = np.linspace(M.TENS_BACK, x0, 70)
    ax.plot(xs, z + 2.4 * np.sin(np.linspace(0, 7 * 2 * np.pi, 70)), color=stl, lw=1.6)
    # set screw + terminal on the sled
    ax.add_patch(Rectangle((x0 + M.TENS_SLED_X / 2 - 1.4, F + M.TENS_SLED_Z), 2.8, 5,
                           fc="#333", ec="k", lw=0.6))
    ax.add_patch(Rectangle((x0 + M.TENS_SLED_X * 0.72 - 2.3, F + M.TENS_SLED_Z), 4.6, 3,
                           fc="#c8ae2e", ec="k", lw=0.6))
    # wire through the sled and out the front
    ax.plot([x0, X + 42], [z, z], color=orn, lw=2.6)
    # force arrows
    ax.annotate("", xy=(M.TENS_BACK - 0.5, z), xytext=(x0, z),
                arrowprops=dict(arrowstyle="->", color="#5b5f66", lw=2))
    ax.text((M.TENS_BACK + x0) / 2, F + 3.0, "spring ≈5 N", color="#4a4e55", ha="center", fontsize=9)
    ax.annotate("", xy=(X + 30, z + 6), xytext=(x1, z + 6),
                arrowprops=dict(arrowstyle="->", color=orn, lw=2))
    ax.text((x1 + X + 30) / 2, z + 7.5, "wire tension", color=orn, ha="center", fontsize=9)
    # take-up gap dimension
    ax.annotate("", xy=(x1, F - 3.5), xytext=(X - M.TENS_FRONT, F - 3.5),
                arrowprops=dict(arrowstyle="<->", color="#0a7d2c", lw=1.3))
    ax.text((x1 + X - M.TENS_FRONT) / 2, F - 6.5, f"take-up (stroke {M.TENS_STROKE:.0f} mm;\nhot growth 2.2 mm)",
            color="#0a7d2c", ha="center", va="top", fontsize=8)
    # labels
    for tx, tz, s, ha in [
        (M.TENS_BACK / 2, H + 2, "back wall\n(carriage mount +\nspring anchor)", "center"),
        (x0 + M.TENS_SLED_X / 2, H + 2, "sled", "center"),
        (x0 + M.TENS_SLED_X / 2 + 1, F + M.TENS_SLED_Z + 6, "M3 set screw\n(wire clamp)", "center"),
        (x0 + M.TENS_SLED_X * 0.72, F + M.TENS_SLED_Z + 4.5, "terminal", "left"),
        (X + 20, z - 3, "0.4 mm nichrome → to block", "center"),
    ]:
        ax.text(tx, tz, s, ha=ha, va="bottom", fontsize=8)

    ax.set_xlim(-6, X + 50)
    ax.set_ylim(-14, H + 16)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Constant-force wire tensioner — cross-section (sled slides on X; "
                 "spring takes up hot growth)")
    fig.tight_layout()
    p = os.path.join(BUILD, f"{name}.png")
    fig.savefig(p)
    plt.close(fig)
    return p


if __name__ == "__main__":
    parts = assembly()
    print("=== tensioner manifest (bbox mm) ===")
    for k, s in parts.items():
        bb = s.bounding_box()
        print(f"  {k:9s} {bb.size.X:6.1f} {bb.size.Y:6.1f} {bb.size.Z:6.1f}")
    print("stroke:", M.TENS_STROKE, "mm  | wire elongation budget: 2.2 mm hot")
    print("rendered", render(parts))                                  # translucent iso
    section = {k: clip_y(v) for k, v in parts.items()}
    print("rendered", render(section, name="tensioner_section"))
    print("rendered", schematic())
