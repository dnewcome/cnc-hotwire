"""Interactive MuJoCo bench for the 4-axis hot-wire cutter.

Geometry is DERIVED from cad/machine_params.py (single source of truth), in SI units
(CAD mm -> *0.001). The four slide axes (U_L, V_L, U_R, V_R) are position actuators, so
the viewer's Control pane gives you a slider per axis; the wire is a spatial TENDON
between the two carriage mount sites, so it follows the carriages automatically.

Modes:
  python3 sim/mujoco_sim.py             interactive viewer (glfw) — drive the 4 axes
  python3 sim/mujoco_sim.py --demo      headless scripted sweep -> sim/out/mujoco_sweep.gif
  python3 sim/mujoco_sim.py --selftest  build + step, print sanity, no window (CI-safe)

At concept stage the parts are primitives built from the same params as the CAD; swap
individual geoms for exported meshes (per the mujoco-sim skill) once real parts exist.
Gravity is off — this is a positioning/kinematics bench; turn it on + give the wire tendon
stiffness for a thermal-sag study later.
"""
import os
import sys

_MODE = "demo" if "--demo" in sys.argv else "selftest" if "--selftest" in sys.argv else "interactive"
# MUJOCO_GL must be set BEFORE importing mujoco: windowed backend for interactive, software for headless
os.environ.setdefault("MUJOCO_GL", "glfw" if _MODE == "interactive" else "osmesa")

import numpy as np                      # noqa: E402
import mujoco                           # noqa: E402
from dataclasses import dataclass       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
import machine_params as M              # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
mm = 0.001                              # CAD mm -> MuJoCo m


@dataclass
class Params:
    dt: float = 0.002
    kp: float = 4000.0                  # position-servo stiffness (N/m)
    damping: float = 60.0               # axis damping


def _box(name, full, pos, rgba):
    hx, hy, hz = (c / 2 * mm for c in full)
    px, py, pz = (c * mm for c in pos)
    return (f'<geom name="{name}" type="box" size="{hx:.5f} {hy:.5f} {hz:.5f}" '
            f'pos="{px:.5f} {py:.5f} {pz:.5f}" rgba="{rgba}"/>')


def _frame_geoms():
    g = []
    for sx in (M.LX, M.RX):
        s = "L" if sx == M.LX else "R"
        for y, ty in ((0, "a"), (M.BED_LEN, "b")):
            g.append(_box(f"up_{s}{ty}", (M.EXTR, M.EXTR, M.TOWER_H),
                          (sx, y, M.TOWER_H / 2), "0.62 0.63 0.66 1"))
        for z, tz in ((M.EXTR / 2, "lo"), (M.TOWER_H - M.EXTR / 2, "hi")):
            g.append(_box(f"yr_{s}{tz}", (M.EXTR, M.BED_LEN, M.EXTR),
                          (sx, M.BED_LEN / 2, z), "0.62 0.63 0.66 1"))
    for y, ty in ((0, "a"), (M.BED_LEN, "b")):
        g.append(_box(f"xr_{ty}", (M.CUT_WIDTH + 2 * M.EXTR, M.EXTR, M.EXTR),
                      (M.CUT_WIDTH / 2, y, M.EXTR / 2), "0.55 0.56 0.6 1"))
    return "\n      ".join(g)


def _tower(side):
    sx = M.LX if side == "L" else M.RX
    wire_x = M.WIRE_X_L if side == "L" else M.WIRE_X_R
    reach = wire_x - sx                                   # arm reach to wire plane (signed)
    beam = _box(f"{side}_beam", (M.EXTR, M.BEAM_LEN, M.EXTR), (0, M.BED_LEN / 2, 0),
                "0.42 0.50 0.60 1")
    carr = _box(f"{side}_carr", (M.CARR_X, M.CARR_Y, M.CARR_Z), (0, 0, 0),
                "0.30 0.40 0.52 1")
    arm = _box(f"{side}_arm", (abs(reach), M.MOUNT_W, M.MOUNT_W), (reach / 2, 0, 0),
               "0.30 0.40 0.52 1")
    return f"""
    <body name="{side}_z" pos="{sx * mm:.5f} 0 0">
      <joint name="{side}_z" type="slide" axis="0 0 1" range="0 {M.Z_TRAVEL * mm:.5f}" damping="{{damping}}"/>
      {beam}
      <body name="{side}_y" pos="0 0 0">
        <joint name="{side}_y" type="slide" axis="0 1 0" range="0 {M.BED_LEN * mm:.5f}" damping="{{damping}}"/>
        {carr}
        {arm}
        <site name="mount{side}" pos="{reach * mm:.5f} 0 0" size="0.005" rgba="0.9 0.1 0.05 1"/>
      </body>
    </body>"""


def make_xml(p: Params):
    U, V = M.BED_LEN / 2 * mm, M.Z_TRAVEL / 2 * mm       # home
    bed = _box("bed", (M.CUT_WIDTH, M.BED_LEN, M.BED_THK),
               (M.CUT_WIDTH / 2, M.BED_LEN / 2, M.BED_TOP - M.BED_THK / 2), "0.32 0.28 0.26 1")
    foam = _box("foam", (M.FOAM_X, M.FOAM_Y, M.FOAM_Z),
                (M.CUT_WIDTH / 2, M.BED_LEN / 2, M.BED_TOP + M.FOAM_Z / 2), "0.35 0.60 0.88 0.35")
    towers = (_tower("L") + _tower("R")).format(damping=p.damping)
    fcx, fcy = M.CUT_WIDTH / 2 * mm, M.BED_LEN / 2 * mm
    return f"""<mujoco model="cnc_hotwire">
  <option gravity="0 0 0" timestep="{p.dt}" integrator="implicitfast"/>
  <default><geom contype="0" conaffinity="0"/></default>
  <visual><global offwidth="1080" offheight="720"/><headlight ambient="0.45 0.45 0.45"/></visual>
  <worldbody>
    <light pos="{fcx} {fcy - 1.0} 1.4" dir="0 0.4 -1"/>
    <geom name="floor" type="plane" size="2 2 0.1" pos="{fcx} {fcy} 0" rgba="0.90 0.90 0.92 1"/>
    {_frame_geoms()}
    {bed}
    {foam}
    {towers}
  </worldbody>
  <tendon>
    <spatial name="wire" width="0.0022" rgba="1 0.32 0.06 1">
      <site site="mountL"/><site site="mountR"/>
    </spatial>
  </tendon>
  <actuator>
    <position name="U_L" joint="L_y" kp="{p.kp}" ctrlrange="0 {M.BED_LEN * mm:.5f}"/>
    <position name="V_L" joint="L_z" kp="{p.kp}" ctrlrange="0 {M.Z_TRAVEL * mm:.5f}"/>
    <position name="U_R" joint="R_y" kp="{p.kp}" ctrlrange="0 {M.BED_LEN * mm:.5f}"/>
    <position name="V_R" joint="R_z" kp="{p.kp}" ctrlrange="0 {M.Z_TRAVEL * mm:.5f}"/>
  </actuator>
  <keyframe>
    <key name="home" qpos="{V} {U} {V} {U}" ctrl="{U} {V} {U} {V}"/>
  </keyframe>
</mujoco>"""


def build(p: Params = Params()):
    model = mujoco.MjModel.from_xml_string(make_xml(p))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)          # home pose + seeded ctrl
    mujoco.mj_forward(model, data)
    return model, data


def _site(model, data, name):
    return data.site_xpos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, name)]


def run_interactive():
    import mujoco.viewer
    model, data = build()
    print("Interactive MuJoCo — open the Control pane and drag U_L / V_L / U_R / V_R.")
    print("Make the left and right axes differ to tilt the wire (the 4-axis taper).")
    mujoco.viewer.launch(model, data)


def run_demo(p: Params = Params(), seconds=8.0, fps=30):
    import imageio.v2 as imageio
    model, data = build(p)
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(model, cam)
    cam.lookat[:] = [M.CUT_WIDTH / 2 * mm, M.BED_LEN / 2 * mm, M.TOWER_H / 2 * mm]
    cam.distance, cam.azimuth, cam.elevation = 1.55, 48, -20
    ren = mujoco.Renderer(model, 720, 1080)
    U0, V0 = M.BED_LEN / 2 * mm, M.Z_TRAVEL / 2 * mm
    frames, steps, every = [], int(seconds / p.dt), max(1, int(1 / fps / p.dt))
    for k in range(steps):
        ph = 2 * np.pi * (k * p.dt) / seconds
        data.ctrl[:] = [U0 + 0.12 * np.sin(ph),          # U_L
                        V0 + 0.09 * np.sin(ph),          # V_L
                        U0 + 0.12 * np.sin(ph + 0.7),    # U_R
                        V0 - 0.09 * np.sin(ph)]          # V_R (opposite -> tilt)
        mujoco.mj_step(model, data)
        if k % every == 0:
            ren.update_scene(data, cam)
            frames.append(ren.render().copy())
    out = os.path.join(OUT, "mujoco_sweep.gif")
    imageio.mimsave(out, frames, fps=fps, loop=0)
    ren.close()
    print("wrote", out, "(%d frames)" % len(frames))
    return out


def selftest(p: Params = Params()):
    model, data = build(p)
    for _ in range(200):
        mujoco.mj_step(model, data)
    L, R = _site(model, data, "mountL"), _site(model, data, "mountR")
    print(f"bodies={model.nbody} joints={model.njnt} actuators={model.nu} tendons={model.ntendon}")
    print("mountL (m):", np.round(L, 3), " mountR (m):", np.round(R, 3))
    print("qpos:", np.round(data.qpos, 3))
    assert np.all(np.isfinite(data.qpos)), "NaN in qpos"
    # home: both ends level at mid-height, spanning the full cut width
    assert abs(L[0] - 0.0) < 1e-6 and abs(R[0] - M.CUT_WIDTH * mm) < 1e-6, "wire span wrong"
    print("SELFTEST OK")


if __name__ == "__main__":
    {"interactive": run_interactive, "demo": run_demo, "selftest": selftest}[_MODE]()
