"""tensioner_bracket.py — open-top channel that bolts to the carriage and guides the
   tensioner sled along the wire axis (+X). Back wall = carriage mount + spring anchor,
   front wall = wire exit.  py cad/tensioner_bracket.py -> build/tensioner_bracket.stl
"""
import os
from build123d import Box, Pos, Align, export_stl, Location, Rot
import machine_params as M
from partlib import xhole


def part():
    X, Y, H = M.TENS_X, M.TENS_Y, M.TENS_H
    floor = Box(X, Y, M.TENS_FLOOR, align=(Align.MIN, Align.CENTER, Align.MIN))
    back = Box(M.TENS_BACK, Y, H, align=(Align.MIN, Align.CENTER, Align.MIN))
    front = Pos(X, 0, 0) * Box(M.TENS_FRONT, Y, H, align=(Align.MAX, Align.CENTER, Align.MIN))
    sy = M.TENS_CAV_Y / 2 + M.TENS_WALL / 2
    side = Box(X, M.TENS_WALL, H, align=(Align.MIN, Align.CENTER, Align.MIN))
    body = floor.fuse(back, front, Pos(0, sy, 0) * side, Pos(0, -sy, 0) * side)

    holes = []
    for s in (1, -1):                                   # carriage mount (through back wall)
        holes.append(xhole(M.TENS_M3_CL / 2, -1, M.TENS_BACK + 1,
                           s * M.TENS_MOUNT_DY / 2, M.TENS_WIRE_ZC))
    holes.append(xhole(3.2 / 2, -1, M.TENS_BACK + 1, 0, M.TENS_WIRE_ZC))   # spring anchor
    holes.append(xhole(M.TENS_WIRE_CH / 2, X - M.TENS_FRONT - 1, X + 1, 0, M.TENS_WIRE_ZC))  # wire exit
    return body.cut(*holes)


# mate points (local frame): +Z of a mate points OUT along the joining direction
MATES = {
    "to_carriage": Location((0, 0, M.TENS_WIRE_ZC)) * Rot(0, -90, 0),   # back face -> carriage
    "wire_exit":   Location((M.TENS_X, 0, M.TENS_WIRE_ZC)),             # wire leaves here (+X)
    "cavity":      Location((M.TENS_BACK, 0, M.TENS_FLOOR)),            # inner back-bottom
}


if __name__ == "__main__":
    _bd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
    os.makedirs(_bd, exist_ok=True)
    _stl = os.path.join(_bd, "tensioner_bracket.stl")
    export_stl(part(), _stl)
    import trimesh
    m = trimesh.load(_stl)
    print("tensioner_bracket:", (m.bounds[1] - m.bounds[0]).round(1),
          "bodies:", len(m.split(only_watertight=False)), "watertight:", m.is_watertight)
