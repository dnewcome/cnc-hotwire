"""One side's moving assembly: gantry beam (V axis) + Y carriage (U axis) + wire mount.

stage(U, V, side) returns (Compound, mount_point) where mount_point is the world
location of the wire attachment -- i.e. one end of the wire.
"""
from build123d import Box, Pos, Compound
import machine_params as M


def stage(U, V, side):
    """side: 'L' or 'R'. Returns (Compound, (x, y, z) mount point)."""
    sx = M.LX if side == 'L' else M.RX
    wire_x = M.WIRE_X_L if side == 'L' else M.WIRE_X_R

    beam = Pos(sx, M.BED_LEN / 2, V) * Box(M.EXTR, M.BEAM_LEN, M.EXTR)   # V axis
    carr = Pos(sx, U, V) * Box(M.CARR_X, M.CARR_Y, M.CARR_Z)             # U carriage

    arm_mid = (sx + wire_x) / 2                                          # reach to wire plane
    arm_len = abs(wire_x - sx) or M.EXTR
    arm = Pos(arm_mid, U, V) * Box(arm_len, M.MOUNT_W, M.MOUNT_W)

    return Compound(children=[beam, carr, arm]), (wire_x, U, V)
