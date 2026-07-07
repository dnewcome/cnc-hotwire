"""Single source of truth for the CNC hot-wire foam cutter.

Coordinate convention (mm):
  X  wire axis   -- spans left tower (x=0) to right tower (x=CUT_WIDTH)
  Y  foam length / horizontal carriage travel   (the per-side "U" axis)
  Z  vertical / carriage height                 (the per-side "V" axis)

Four independent axes drive the two wire ends:
  left  end at (0,          U_L, V_L)
  right end at (CUT_WIDTH,   U_R, V_R)

When (U_L,V_L) == (U_R,V_R) the wire is square across  -> straight extrusion.
When they differ, the wire tilts  -> ruled loft between two face profiles.
That tilt IS the 4-axis capability.
"""
from build123d import Location

# ---- extrusion / stock --------------------------------------------------
EXTR = 40.0                       # aluminium extrusion cross-section (40x40)

# ---- work envelope ------------------------------------------------------
CUT_WIDTH = 600.0                 # usable wire span between tower inner faces (X)
BED_LEN   = 500.0                 # foam length / U-axis travel (Y)
Z_TRAVEL  = 300.0                 # vertical V-axis travel (Z)
TOWER_H   = Z_TRAVEL + 2 * EXTR   # upright height

# ---- side-frame X planes (extrusion centre-lines) -----------------------
LX = -EXTR / 2                    # left frame: inner face at x=0
RX = CUT_WIDTH + EXTR / 2         # right frame: inner face at x=CUT_WIDTH
WIRE_X_L = 0.0
WIRE_X_R = CUT_WIDTH

# ---- moving stage stand-ins ---------------------------------------------
BEAM_LEN = BED_LEN                        # gantry beam spans the bed in Y
CARR_X, CARR_Y, CARR_Z = 60.0, 60.0, 70.0  # Y-carriage block
MOUNT_W = 16.0                            # wire-mount arm cross-section

# ---- wire ---------------------------------------------------------------
WIRE_DIA = 0.8                    # real nichrome wire diameter
WIRE_VIS_DIA = 4.5                # thicker in renders so it is visible

# ---- bed + foam ---------------------------------------------------------
BED_TOP = 40.0
BED_THK = 20.0
FOAM_X, FOAM_Y, FOAM_Z = 400.0, 350.0, 150.0

# ---- axis limits & poses ------------------------------------------------
U_MIN, U_MAX = 0.0, BED_LEN
V_MIN, V_MAX = 0.0, Z_TRAVEL


def home_pose():
    return dict(UL=BED_LEN / 2, VL=Z_TRAVEL / 2, UR=BED_LEN / 2, VR=Z_TRAVEL / 2)


def demo_pose():
    """A deliberately skewed pose so the tilted-wire (4-axis) nature is visible."""
    return dict(UL=BED_LEN * 0.42, VL=Z_TRAVEL * 0.62,
                UR=BED_LEN * 0.58, VR=Z_TRAVEL * 0.42)


def wire_endpoints(UL, VL, UR, VR):
    return (WIRE_X_L, UL, VL), (WIRE_X_R, UR, VR)


def place(solid, frm: Location, onto: Location):
    """Snap a part so its local mate `frm` coincides with world target `onto`."""
    return (onto * frm.inverse()) * solid
