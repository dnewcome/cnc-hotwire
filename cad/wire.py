"""The heated wire -- a derived cylinder between the two carriage mount points.

Its pose is entirely determined by the four axis positions, exactly as on the
real machine: give it two endpoints and it spans them.
"""
import numpy as np
from build123d import Plane, Solid
import machine_params as M


def wire(p0, p1, dia=None):
    dia = M.WIRE_VIS_DIA if dia is None else dia
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    v = p1 - p0
    L = float(np.linalg.norm(v)) or 1e-6
    vn = v / L
    pl = Plane(origin=tuple(p0), z_dir=tuple(vn))   # cylinder grows +z_dir from p0
    return Solid.make_cylinder(dia / 2, L, pl)
