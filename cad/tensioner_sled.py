"""tensioner_sled.py — sliding wire carrier: wire channel + top set-screw clamp, a spring
   hook cross-hole at the back, and a terminal boss for the electrical lead.
   py cad/tensioner_sled.py -> build/tensioner_sled.stl
"""
import os
from build123d import Box, Cylinder, Pos, Align, export_stl, Location
import machine_params as M
from partlib import xhole, yhole, zhole

SX, SY, SZ = M.TENS_SLED_X, M.TENS_SLED_Y, M.TENS_SLED_Z
TERM_X, TERM_Y = SX * 0.72, SY / 2 - 5.0             # terminal boss location on top
HOOK_X = SX * 0.18                                    # spring-hook cross-pin location


def part():
    body = Box(SX, SY, SZ, align=(Align.MIN, Align.CENTER, Align.MIN))
    boss = Pos(TERM_X, TERM_Y, SZ - 1) * Cylinder(3.6, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = body.fuse(boss)                            # single additive fuse

    cuts = [
        xhole(M.TENS_WIRE_CH / 2, -1, SX + 1, 0, SZ / 2),          # wire channel through
        zhole(M.TENS_SET_TAP / 2, SX / 2, 0, SZ / 2 - 1, SZ + 1),  # top set-screw into channel
        yhole(3.2 / 2, HOOK_X, -(SY / 2 + 1), SY / 2 + 1, SZ / 2), # spring-hook cross-pin
        zhole(M.TENS_HEATSET / 2, TERM_X, TERM_Y, -1, SZ + 3 + 1), # terminal bore (through)
    ]
    return body.cut(*cuts)


MATES = {
    "spring_hook": Location((HOOK_X, 0, SZ / 2)),     # back cross-pin (spring pulls -X)
    "wire_out":    Location((SX, 0, SZ / 2)),         # wire exits toward the block (+X)
}


if __name__ == "__main__":
    _bd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
    os.makedirs(_bd, exist_ok=True)
    _stl = os.path.join(_bd, "tensioner_sled.stl")
    export_stl(part(), _stl)
    import trimesh
    m = trimesh.load(_stl)
    print("tensioner_sled:", (m.bounds[1] - m.bounds[0]).round(1),
          "bodies:", len(m.split(only_watertight=False)), "watertight:", m.is_watertight)
