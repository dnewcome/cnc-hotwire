"""Static structure: base + two facing vertical gantry frames (extrusion stand-ins).

The moving carriages ride these frames; their positions are owned by the axis
parameters in the assembly, not by fixed mates here.
"""
from build123d import Box, Pos, Compound
import machine_params as M


def _upright(x, y):
    return Pos(x, y, M.TOWER_H / 2) * Box(M.EXTR, M.EXTR, M.TOWER_H)


def _yrail(x, z):
    return Pos(x, M.BED_LEN / 2, z) * Box(M.EXTR, M.BED_LEN, M.EXTR)


def _xrail(y):
    w = M.CUT_WIDTH + 2 * M.EXTR
    return Pos(M.CUT_WIDTH / 2, y, M.EXTR / 2) * Box(w, M.EXTR, M.EXTR)


def part():
    solids = []
    for sx in (M.LX, M.RX):                       # left & right vertical frames
        solids += [_upright(sx, 0), _upright(sx, M.BED_LEN)]
        solids += [_yrail(sx, M.EXTR / 2), _yrail(sx, M.TOWER_H - M.EXTR / 2)]
    solids += [_xrail(0), _xrail(M.BED_LEN)]       # base cross-ties
    return Compound(children=solids)


MATES = {}  # static; carriages placed by axis params in the assembly
