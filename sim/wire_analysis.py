"""Thermo-mechanical sizing for the hot-wire subsystem — simulate before selecting parts.

Answers the three questions that size the whole subsystem:
  1. THERMAL   — current / voltage / power to hold the wire at cutting temperature
                 (I^2 R heating balanced against radiation + natural convection).
  2. SAG       — mid-span bow of a tensioned wire (catenary), vs the nesting tolerance,
                 and the tension window between "too slack" and the wire's stress limit.
  3. EXPANSION — how much the wire lengthens when hot -> why tensioning MUST be
                 constant-force (fixed ends go slack instantly) + the tensioner travel budget.

Material: Nichrome 80 (NiCr 80/20). SI units throughout.
Run:  python3 sim/wire_analysis.py   ->  sim/out/wire_analysis.png  + printed sizing table.
"""
import os
import sys
from dataclasses import dataclass

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
import machine_params as M               # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
SIG = 5.67e-8                            # Stefan-Boltzmann
G = 9.81
TAMB = 293.15                           # 20 C ambient (K)


@dataclass
class Wire:
    # --- Nichrome 80 material ---
    rho_e: float = 1.10e-6              # electrical resistivity @20C (ohm*m)
    a_r: float = 1.1e-4                # resistivity tempco (/K) — nichrome is nearly flat
    dens: float = 8400.0               # kg/m^3
    E: float = 200e9                   # Young's modulus (Pa)
    cte: float = 13.4e-6               # thermal expansion (/K)
    emiss: float = 0.7                 # emissivity (oxidized)
    sig_allow: float = 200e6           # allowable working stress at temp (Pa), creep-conservative
    # --- geometry / operating point (from machine_params — single source of truth) ---
    dia: float = M.WIRE_DIA * 1e-3     # wire diameter (m)
    span: float = M.WIRE_SPAN * 1e-3   # heated length (m)
    T_cut: float = M.WIRE_T_CUT        # target cutting temperature (C) — clean EPS/XPS
    sag_tol: float = M.WIRE_SAG_TOL * 1e-3   # allowable mid-span bow (m)

    @property
    def area(self):
        return np.pi * self.dia ** 2 / 4

    @property
    def w_lin(self):                   # weight per length (N/m)
        return self.dens * self.area * G


# ---------- thermal ----------
def air_props(Tf):
    """Rough temperature-dependent air properties at film temperature Tf (K)."""
    k = 0.0262 * (Tf / 300) ** 0.86
    nu = 1.57e-5 * (Tf / 300) ** 1.72
    Pr = 0.71
    return k, nu, Pr, nu / Pr, 1.0 / Tf   # k, nu, Pr, alpha, beta


def h_conv(D, Ts_K):
    """Natural-convection coefficient for a horizontal cylinder (Churchill-Chu)."""
    Tf = 0.5 * (Ts_K + TAMB)
    k, nu, Pr, a, beta = air_props(Tf)
    Ra = max(G * beta * (Ts_K - TAMB) * D ** 3 / (nu * a), 1e-9)
    Nu = (0.60 + 0.387 * Ra ** (1 / 6) / (1 + (0.559 / Pr) ** (9 / 16)) ** (8 / 27)) ** 2
    return Nu * k / D


def p_loss(D, Ts_K, emiss):
    """Heat loss per unit length (W/m): radiation + natural convection."""
    p_rad = emiss * SIG * np.pi * D * (Ts_K ** 4 - TAMB ** 4)
    p_conv = h_conv(D, Ts_K) * np.pi * D * (Ts_K - TAMB)
    return p_rad, p_conv


def rho_at(w, Tc):
    return w.rho_e * (1 + w.a_r * (Tc - 20))


def current_for_temp(w, Tc, D=None):
    """Direct: current (A) to hold temperature Tc (C). p_elec/len = I^2 rho/A = losses."""
    D = w.dia if D is None else D
    A = np.pi * D ** 2 / 4
    Ts_K = Tc + 273.15
    p_rad, p_conv = p_loss(D, Ts_K, w.emiss)
    P_len = p_rad + p_conv
    I = np.sqrt(P_len * A / rho_at(w, Tc))
    return I, P_len, p_rad, p_conv


def temp_for_current(w, I, D=None):
    """Invert: steady temperature (C) for current I (A), by bisection."""
    D = w.dia if D is None else D
    A = np.pi * D ** 2 / 4

    def f(Tc):
        Ts_K = Tc + 273.15
        p_rad, p_conv = p_loss(D, Ts_K, w.emiss)
        return I ** 2 * rho_at(w, Tc) / A - (p_rad + p_conv)

    lo, hi = 20.0, 1400.0
    if f(hi) > 0:            # even at hi the wire still gains heat -> clamp (root above hi)
        return hi
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:      # f decreases with Tc: f>0 means too cold -> raise floor
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ---------- mechanical ----------
def sag(w, T):
    return w.w_lin * w.span ** 2 / (8 * T)          # catenary small-sag (m)


def tension_for_sag(w, delta):
    return w.w_lin * w.span ** 2 / (8 * delta)      # N


def elong(w, dT):
    return w.cte * w.span * dT                       # m


def fixed_end_tension(w, T_pre, dT):
    """Tension left in a FIXED-length wire after heating by dT (clamped at 0 = slack)."""
    return max(T_pre - w.E * w.area * w.cte * dT, 0.0)


# ---------- report ----------
def report(w: Wire):
    I, P_len, p_rad, p_conv = current_for_temp(w, w.T_cut)
    R = rho_at(w, w.T_cut) * w.span / w.area
    P = I ** 2 * R
    V = I * R
    T_target = tension_for_sag(w, w.sag_tol)
    stress = T_target / w.area
    Tmax = w.sig_allow * w.area
    dT = w.T_cut - 20
    dL = elong(w, dT)
    kerf = w.dia + 0.3e-3                            # dia + ~0.3mm melt halo (indicative)

    print("=" * 66)
    print(f"  HOT-WIRE SIZING  —  Nichrome 80, dia {w.dia*1e3:.2f} mm, span {w.span*1e3:.0f} mm")
    print("=" * 66)
    print(f"  Resistance (hot)        {R:6.2f} ohm")
    print(f"  THERMAL @ {w.T_cut:.0f} C   current {I:6.2f} A   voltage {V:6.1f} V   power {P:6.1f} W")
    print(f"    loss split           radiation {p_rad*w.span:5.1f} W | convection {p_conv*w.span:5.1f} W")
    print(f"  MECH   tension target   {T_target:6.2f} N ({T_target/G*1e3:.0f} gf)  for sag <= {w.sag_tol*1e3:.2f} mm")
    print(f"    wire stress          {stress*1e-6:6.1f} MPa   vs allowable {w.sig_allow*1e-6:.0f} MPa"
          f"  (x{w.sig_allow/stress:.0f} margin)")
    print(f"    max safe tension     {Tmax:6.1f} N  ->  min sag {sag(w,Tmax)*1e6:.0f} um")
    print(f"  EXPANSION dT={dT:.0f}C     elongation {dL*1e3:5.2f} mm  -> tensioner travel budget")
    print(f"    fixed ends: {T_target:.1f} N pre-tension -> {fixed_end_tension(w,T_target,dT):.1f} N after heat"
          f"  (SLACK — must use constant-force)")
    print(f"  KERF (indicative)       ~{kerf*1e3:.2f} mm  -> nest pitch >= part + {kerf*1e3:.2f} mm")
    print("=" * 66)
    return dict(I=I, V=V, P=P, R=R, T_target=T_target, dL=dL, Tmax=Tmax, kerf=kerf)


def figure(w: Wire, r):
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6), dpi=120)

    # 1) temperature vs current, several gauges
    Ivec = np.linspace(0.2, 6, 120)
    for D in (0.3e-3, 0.4e-3, 0.5e-3, 0.6e-3):
        Tc = [temp_for_current(w, I, D) for I in Ivec]
        ax[0].plot(Ivec, Tc, label=f"{D*1e3:.1f} mm")
    ax[0].axhspan(200, 320, color="#ffd9b3", alpha=0.5, label="EPS/XPS cut band")
    ax[0].axhline(w.T_cut, color="#b00020", ls="--", lw=1)
    ax[0].axvline(r["I"], color="#b00020", ls=":", lw=1)
    ax[0].set(xlabel="current (A)", ylabel="wire temperature (°C)",
              title="Thermal: temperature vs current", ylim=(0, 700))
    ax[0].legend(title="dia", fontsize=8)
    ax[0].grid(alpha=0.3)

    # 2) sag vs tension (+ stress axis)
    Tvec = np.linspace(0.5, r["Tmax"], 200)
    sags = sag(w, Tvec) * 1e3
    ax[1].plot(Tvec, sags, color="#2f6da8", lw=2)
    ax[1].axhline(w.sag_tol * 1e3, color="#0a7d2c", ls="--", lw=1, label=f"tol {w.sag_tol*1e3:.2f} mm")
    ax[1].axvline(r["T_target"], color="#b00020", ls=":", lw=1, label=f"target {r['T_target']:.1f} N")
    ax[1].set(xlabel="tension (N)", ylabel="mid-span sag (mm)",
              title="Sag: bow vs tension", ylim=(0, min(1.0, sags.max())))
    ax[1].legend(fontsize=8)
    ax[1].grid(alpha=0.3)
    axb = ax[1].twiny()
    axb.set_xlim(ax[1].get_xlim()[0] / w.area * 1e-6, ax[1].get_xlim()[1] / w.area * 1e-6)
    axb.set_xlabel("wire stress (MPa)", fontsize=9)

    # 3) why constant-force: tension vs temperature (fixed vs constant-force) + elongation
    dTv = np.linspace(0, w.T_cut - 20, 100)
    fixed = [fixed_end_tension(w, r["T_target"], dt) for dt in dTv]
    ax[2].plot(dTv, fixed, color="#b00020", lw=2, label="fixed ends → slack")
    ax[2].plot(dTv, [r["T_target"]] * len(dTv), color="#0a7d2c", lw=2, label="constant-force")
    ax[2].set(xlabel="temperature rise ΔT (°C)", ylabel="wire tension (N)",
              title="Why constant-force tensioning")
    ax[2].legend(fontsize=8, loc="center right")
    ax[2].grid(alpha=0.3)
    axe = ax[2].twinx()
    axe.plot(dTv, elong(w, dTv) * 1e3, color="#8a5a00", ls="--", lw=1.3)
    axe.set_ylabel("elongation (mm)", color="#8a5a00", fontsize=9)

    fig.suptitle("Hot-wire subsystem sizing — Nichrome 80, "
                 f"{w.dia*1e3:.1f} mm × {w.span*1e3:.0f} mm span", fontsize=12)
    fig.tight_layout()
    p = os.path.join(OUT, "wire_analysis.png")
    fig.savefig(p)
    plt.close(fig)
    return p


if __name__ == "__main__":
    w = Wire()
    r = report(w)
    print("figure:", figure(w, r))
