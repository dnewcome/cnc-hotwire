"""Bed platform + foam work block, centred between the towers."""
from build123d import Box, Pos
import machine_params as M


def bed():
    return Pos(M.CUT_WIDTH / 2, M.BED_LEN / 2, M.BED_TOP - M.BED_THK / 2) \
        * Box(M.CUT_WIDTH, M.BED_LEN, M.BED_THK)


def block():
    return Pos(M.CUT_WIDTH / 2, M.BED_LEN / 2, M.BED_TOP + M.FOAM_Z / 2) \
        * Box(M.FOAM_X, M.FOAM_Y, M.FOAM_Z)
