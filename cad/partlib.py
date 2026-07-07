"""Small shared helpers for axis-aligned through-holes (cut cylinders that overshoot)."""
from build123d import Pos, Rot, Cylinder


def xhole(r, x0, x1, y, z):
    """Cylinder along +X spanning [x0, x1] at (y, z)."""
    return Pos((x0 + x1) / 2, y, z) * Rot(0, 90, 0) * Cylinder(r, x1 - x0)


def yhole(r, x, y0, y1, z):
    """Cylinder along +Y spanning [y0, y1] at (x, z)."""
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(r, y1 - y0)


def zhole(r, x, y, z0, z1):
    """Cylinder along +Z spanning [z0, z1] at (x, y)."""
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)
