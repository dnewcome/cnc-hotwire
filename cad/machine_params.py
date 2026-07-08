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

# ---- wire subsystem (sized in sim/wire_analysis.py) ---------------------
WIRE_MATERIAL = "Nichrome 80"     # NiCr 80/20
WIRE_DIA = 0.4                    # chosen diameter (mm) — kerf vs strength balance
WIRE_VIS_DIA = 4.5                # thicker in renders so it is visible
WIRE_OVERHANG = 50.0              # each end: tower face -> mount/tensioner (mm)
WIRE_SPAN = CUT_WIDTH + 2 * WIRE_OVERHANG   # heated length (mm)
WIRE_T_CUT = 250.0                # target cutting temperature (deg C) — clean EPS/XPS
WIRE_SAG_TOL = 0.15               # allowable mid-span bow (mm)
WIRE_TENSION = 5.0                # design tension (N): > 4.2 N min, ~x5 stress margin
WIRE_TENSIONER_TRAVEL = 5.0       # constant-force take-up (mm) > 2.2 mm hot elongation
WIRE_KERF = 0.7                   # indicative kerf (mm) -> nest pitch = part + WIRE_KERF
WIRE_PSU_V = 24.0                 # supply (V); PWM/constant-current, ~1.6 A / 16 W at temp

# ---- wire tensioner (constant-force sled; see cad/tensioner*.py) ---------
TENS_STROKE   = 15.0     # sled take-up travel (mm) > 2.2 mm hot elongation + setup
TENS_WALL     = 3.0      # channel side-wall thickness
TENS_FLOOR    = 3.0      # channel floor thickness
TENS_BACK     = 6.0      # back wall (carriage mount + spring anchor) thickness
TENS_FRONT    = 4.0      # front wall (wire exit) thickness
TENS_SLED_X   = 16.0     # sled length along the slide axis
TENS_SLED_Y   = 30.0     # sled width
TENS_SLED_Z   = 18.0     # sled height
TENS_SLIDE_CL = 0.4      # sled / channel slide clearance
TENS_MOUNT_DY = 22.0     # carriage bolt spacing (M3)
TENS_M3_CL    = 3.4      # M3 clearance
TENS_SET_TAP  = 2.6      # M3 self-tap into plastic (wire-clamp set screw)
TENS_HEATSET  = 4.6      # M3 heat-set / terminal bore (through, not blind)
TENS_WIRE_CH  = 2.0      # wire channel diameter through the sled
# real spring — a soft stainless EXTENSION spring, anchored to a post on the carriage
# ~30 mm behind the bracket so it is long enough that its rate barely changes the force over
# the tiny take-up travel. (A constant-force spring is the ideal but a specialty part.)
# Installed stretched to ~38 mm -> ~6 N nominal; over the 2.2 mm hot take-up it drops to
# ~5.3 N (<10%), keeping sag < 0.15 mm. Order to: OD/wire/free-length/rate below.
TENS_SPRING_OD      = 8.0    # extension spring OD (mm)
TENS_SPRING_WIRE    = 0.7    # spring wire diameter (mm), stainless 302
TENS_SPRING_FREE    = 25.0   # free length (mm)
TENS_SPRING_RATE    = 0.30   # spring rate (N/mm)
TENS_SPRING_IT      = 1.5    # initial tension / preload (N)
TENS_SPRING_INSTALL = 38.0   # installed (stretched) length (mm) -> ~6 N
TENS_SPRING_ANCHOR_D = 10.0  # back-wall pass-through for the spring (mm)
# derived
TENS_CAV_X = TENS_SLED_X + TENS_STROKE          # channel cavity length
TENS_CAV_Y = TENS_SLED_Y + TENS_SLIDE_CL        # channel cavity width
TENS_X = TENS_BACK + TENS_CAV_X + TENS_FRONT    # bracket overall length
TENS_Y = TENS_CAV_Y + 2 * TENS_WALL             # bracket overall width
TENS_H = TENS_FLOOR + TENS_SLED_Z               # channel wall height
TENS_WIRE_ZC = TENS_FLOOR + TENS_SLED_Z / 2     # wire centreline height above base

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
