"""Electro-thermal design + simulation for the hot-wire heater driver.

Topology: low-side logic-level N-MOSFET PWM from a 24 V supply, with a current-sense shunt
for CLOSED-LOOP constant-power (≈ constant-current, since nichrome's resistance barely drifts).
The load is a pure resistor -> NO flyback diode needed (the #1 simplification vs a motor).

Why constant-power control: wire temperature (hence kerf) is set by power = losses. Holding
power rejects supply sag and resistance drift; open-loop fixed duty lets temperature wander.

Two-timescale simulation:
  1. slow thermal envelope (heat-up + supply-sag rejection) -- PWM averaged, dt = 1 ms
  2. fast PWM ripple -- resolves the switching waveform, shows the wire's thermal mass makes
     temperature ripple negligible (=> stable kerf) even at modest PWM frequency.

Run:  python3 sim/heater_driver.py  ->  sim/out/heater_driver.png  + component / operating table.
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
sys.path.insert(0, HERE)
import machine_params as M               # noqa: E402
import wire_analysis as wa               # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

W = wa.Wire()
C_P = 450.0                              # J/kgK nichrome specific heat
C_TH = C_P * W.dens * W.area * W.span    # J/K  wire heat capacity (thermal mass)
V_SUP = M.WIRE_PSU_V                     # supply voltage (V)
RDS = 0.010                              # MOSFET on-resistance (ohm), logic-level FET
F_PWM = 1000.0                           # PWM frequency (Hz)


def R_at(Tc):
    return wa.rho_at(W, Tc) * W.span / W.area


def p_loss_total(Tc):
    pr, pc = wa.p_loss(W.dia, Tc + 273.15, W.emiss)
    return (pr + pc) * W.span


# --- operating point -----------------------------------------------------
I_op, P_len, p_rad, p_conv = wa.current_for_temp(W, W.T_cut)
P_OP = P_len * W.span
R_OP = R_at(W.T_cut)
DUTY_OP = P_OP / (V_SUP ** 2 / (R_OP + RDS))
I_PEAK = V_SUP / (R_OP + RDS)
I_RMS = np.sqrt(DUTY_OP) * I_PEAK


# --- controllers (return duty from measured T, R, V) ---------------------
def duty_power(P_set, dmax=1.0):
    return lambda T, R, V: min(P_set * (R + RDS) / V ** 2, dmax)


def duty_fixed(d):
    return lambda T, R, V: d


# --- slow thermal envelope (PWM averaged) --------------------------------
def run_slow(duty_fn, T0=20.0, t_end=12.0, dt=1e-3, v_of_t=None):
    n = int(t_end / dt)
    T = T0
    ts = np.empty(n)
    Ts = np.empty(n)
    dd = np.empty(n)
    for k in range(n):
        t = k * dt
        V = V_SUP if v_of_t is None else v_of_t(t)
        R = R_at(T)
        d = duty_fn(T, R, V)
        P = d * V ** 2 / (R + RDS) * (R / (R + RDS))     # power in the wire (not the FET)
        T += (P - p_loss_total(T)) / C_TH * dt
        ts[k], Ts[k], dd[k] = t, T, d
    return ts, Ts, dd


# --- fast PWM ripple -----------------------------------------------------
def run_ripple(duty, T0, f=F_PWM, cycles=6, dt=2e-6):
    t_end = cycles / f
    n = int(t_end / dt)
    T = T0
    ts = np.empty(n)
    Ts = np.empty(n)
    on = np.empty(n)
    period = 1.0 / f
    for k in range(n):
        t = k * dt
        is_on = (t % period) < duty * period
        R = R_at(T)
        P = (V_SUP ** 2 / (R + RDS) * (R / (R + RDS))) if is_on else 0.0
        T += (P - p_loss_total(T)) / C_TH * dt
        ts[k], Ts[k], on[k] = t, T, is_on
    return ts, Ts, on


def tau_estimate():
    ts, Ts, _ = run_slow(duty_power(P_OP), t_end=20.0)
    Tf = Ts[-1]
    target = 20.0 + 0.632 * (Tf - 20.0)
    i = int(np.argmax(Ts >= target))
    return ts[i], Tf


def report():
    tau, Tf = tau_estimate()
    p_fet = I_RMS ** 2 * RDS + 0.5 * V_SUP * I_PEAK * 100e-9 * F_PWM   # cond + switching
    print("=" * 68)
    print(f"  HOT-WIRE HEATER DRIVER — {V_SUP:.0f} V supply, low-side N-MOSFET PWM + CC")
    print("=" * 68)
    print(f"  wire            {W.dia*1e3:.1f} mm nichrome, {W.span*1e3:.0f} mm, R_hot {R_OP:.2f} ohm")
    print(f"  operating pt    {P_OP:.1f} W to hold {W.T_cut:.0f} C   (duty {DUTY_OP*100:.0f}% @ {F_PWM:.0f} Hz)")
    print(f"    currents      peak {I_PEAK:.2f} A | RMS {I_RMS:.2f} A | avg {DUTY_OP*I_PEAK:.2f} A")
    print(f"  thermal mass    C = {C_TH:.3f} J/K  ->  time constant ~{tau:.1f} s (63%); ~{3*tau:.0f} s to heat")
    print(f"  MOSFET loss     ~{p_fet*1e3:.0f} mW (I_rms^2*Rds + switching) -> runs cold, tiny FET ok")
    print(f"  NO flyback diode — the load is resistive (non-inductive nichrome).")
    print("-" * 68)
    print("  COMPONENTS")
    print(f"    supply    {V_SUP:.0f} V DC, >= 4 A (e.g. 24 V/5 A brick); 12 V works (halves peak I)")
    print( "    MOSFET    logic-level N-ch, Vds>=40 V, Rds<=20 mOhm  (IRLZ44N / IRLB8721 / IRLR7843)")
    print( "    gate      100 ohm series + 10k pulldown; MCU PWM 0.5-2 kHz (3.3/5 V drives it)")
    print( "    sense     0.05 ohm shunt (low-side) + INA180/INA240 -> ADC   (or ACS712 hall)")
    print( "    protect   ~5 A fuse; TVS (SMBJ30A) across supply; open-wire detect (duty>0 & I~0)")
    print( "    control   PID on measured current/power -> duty (constant-power); e-stop cuts gate")
    print( "    standalone alt: an off-the-shelf CC buck (XL4015 / DPS5015) set to I_set")
    print("=" * 68)
    print("  ASCII schematic")
    print(r"""
     +Vsup ──[FUSE]──┬──────────────┐
                     │            [HOT WIRE]  (nichrome, ~6.3 Ω)   << no flyback diode
                     │              │
                    TVS          D│ MOSFET  (low-side, logic level)
                     │           G┤◄── 100Ω ── MCU PWM
     GND ────────────┴──[SHUNT]──S┘
                          │
                          └── INA180 ── MCU ADC   (current -> constant-power loop)
""")


def figure():
    fig, ax = plt.subplots(2, 2, figsize=(13, 8), dpi=120)

    # 1) heat-up (constant-power) with an overdrive option
    ts, Ts, _ = run_slow(duty_power(P_OP), t_end=14.0)
    tso, Tso, _ = run_slow(duty_power(2.0 * P_OP, dmax=0.6), t_end=14.0)  # overdrive, duty-capped
    ax[0, 0].plot(ts, Ts, label="constant-power (Pset)")
    ax[0, 0].plot(tso, Tso, "--", label="overdrive start (2×Pset, duty≤0.6)")
    ax[0, 0].axhline(W.T_cut, color="#b00020", ls=":", lw=1)
    ax[0, 0].set(xlabel="time (s)", ylabel="wire temperature (°C)",
                 title="Heat-up — thermal mass sets the pace")
    ax[0, 0].legend(fontsize=8)
    ax[0, 0].grid(alpha=0.3)

    # 2) supply-sag rejection: open-loop vs constant-power
    def sag(t):
        return V_SUP if t < 6 else V_SUP * 0.8       # 20% supply droop at t=6 s
    tp, Tp, _ = run_slow(duty_power(P_OP), t_end=12.0, v_of_t=sag)
    to, To, _ = run_slow(duty_fixed(DUTY_OP), t_end=12.0, v_of_t=sag)
    ax[0, 1].plot(tp, Tp, label="constant-power (holds)")
    ax[0, 1].plot(to, To, "--", label="open-loop fixed duty (drifts)")
    ax[0, 1].axvline(6, color="#8a8f98", ls=":", lw=1)
    ax[0, 1].text(6.1, ax[0, 1].get_ylim()[0] + 8, "−20% supply", fontsize=8, color="#555")
    ax[0, 1].set(xlabel="time (s)", ylabel="wire temperature (°C)",
                 title="Constant-power rejects supply sag")
    ax[0, 1].legend(fontsize=8)
    ax[0, 1].grid(alpha=0.3)

    # 3) PWM ripple (fast) — negligible temperature ripple
    tr, Tr, on = run_ripple(DUTY_OP, T0=W.T_cut)
    ax[1, 0].plot(tr * 1e3, Tr, color="#b00020")
    ax[1, 0].set(xlabel="time (ms)", ylabel="wire temperature (°C)",
                 title=f"PWM ripple @ {F_PWM:.0f} Hz — Δ = {1e3*(Tr.max()-Tr.min()):.1f} m°C")
    axb = ax[1, 0].twinx()
    axb.fill_between(tr * 1e3, on, step="pre", color="#3a86c8", alpha=0.15)
    axb.set_yticks([0, 1]); axb.set_yticklabels(["off", "on"]); axb.set_ylim(-0.1, 4)
    ax[1, 0].grid(alpha=0.3)

    # 4) duty -> steady temperature map
    duties = np.linspace(0.02, 1.0, 60)
    Tsteady = []
    for d in duties:
        _, Td, _ = run_slow(duty_fixed(d), t_end=40.0, dt=2e-3)
        Tsteady.append(Td[-1])
    ax[1, 1].plot(np.array(duties) * 100, Tsteady, color="#2f6da8")
    ax[1, 1].axhline(W.T_cut, color="#b00020", ls=":", lw=1)
    ax[1, 1].axvline(DUTY_OP * 100, color="#b00020", ls=":", lw=1)
    ax[1, 1].plot(DUTY_OP * 100, W.T_cut, "o", color="#b00020")
    ax[1, 1].set(xlabel="duty (%)", ylabel="steady temperature (°C)",
                 title="Duty → steady temperature", ylim=(0, 700))
    ax[1, 1].grid(alpha=0.3)

    fig.suptitle(f"Hot-wire heater driver — {V_SUP:.0f} V low-side PWM + constant-power "
                 f"(op: {P_OP:.0f} W, {DUTY_OP*100:.0f}% duty)", fontsize=12)
    fig.tight_layout()
    p = os.path.join(OUT, "heater_driver.png")
    fig.savefig(p)
    plt.close(fig)
    return p


if __name__ == "__main__":
    report()
    print("figure:", figure())
