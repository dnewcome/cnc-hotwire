"""Assemble the cutter at a given 4-axis pose, export per-part STLs, render an iso PNG.

Run:  python3 cad/machine.py
Output: cad/build/cnc_hotwire_iso.png  (+ per-part STLs, cnc_hotwire.scad)
"""
import os
import subprocess
from build123d import export_stl
import machine_params as M
import frame
import stage
import wire
import foam

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")

COLORS = {                       # r, g, b in 0..1
    "frame":   (0.62, 0.63, 0.66),
    "stage_L": (0.42, 0.50, 0.60),
    "stage_R": (0.42, 0.50, 0.60),
    "bed":     (0.32, 0.28, 0.26),
    "wire":    (1.00, 0.32, 0.06),
    "foam":    (0.35, 0.60, 0.88),
}
ALPHA = {"foam": 0.3}


def assemble(pose):
    sL, pL = stage.stage(pose["UL"], pose["VL"], 'L')
    sR, pR = stage.stage(pose["UR"], pose["VR"], 'R')
    parts = {
        "frame":   frame.part(),
        "stage_L": sL,
        "stage_R": sR,
        "bed":     foam.bed(),
        "foam":    foam.block(),
        "wire":    wire.wire(pL, pR),
    }
    return parts, (pL, pR)


def manifest(parts, endpoints):
    print("=== manifest (part: bbox size, mm) ===")
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]
    for k, s in parts.items():
        bb = s.bounding_box()
        print(f"  {k:8s}  {bb.size.X:7.1f} x {bb.size.Y:7.1f} x {bb.size.Z:7.1f}")
        lo = [min(lo[0], bb.min.X), min(lo[1], bb.min.Y), min(lo[2], bb.min.Z)]
        hi = [max(hi[0], bb.max.X), max(hi[1], bb.max.Y), max(hi[2], bb.max.Z)]
    print(f"  {'overall':8s}  {hi[0]-lo[0]:7.1f} x {hi[1]-lo[1]:7.1f} x {hi[2]-lo[2]:7.1f}")
    pL, pR = endpoints
    print(f"  wire  L{tuple(round(v,1) for v in pL)} -> R{tuple(round(v,1) for v in pR)}")


def render(parts, name="cnc_hotwire", size=(1280, 900), rot=(58, 0, 28)):
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


if __name__ == "__main__":
    pose = M.demo_pose()
    parts, endpoints = assemble(pose)
    manifest(parts, endpoints)
    png = render(parts)
    print("rendered", png)
