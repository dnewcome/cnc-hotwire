# CNC hot-wire foam cutter — build & simulation
# Usage: `make` runs the sims; `make help` lists all targets.
PYTHON ?= python3
CAD    := cad
SIM    := sim
NOTE   ?= update

.DEFAULT_GOAL := sim
.PHONY: all sim machine cut nest wire driver tensioner mujoco mujoco-demo mujoco-selftest snap clean help

## sim:     run both simulations (cut + nest)            [default]
sim: cut nest

## all:     render the machine + run both sims
all: machine sim

## machine: assemble + render the machine -> cad/build/cnc_hotwire_iso.png
machine:
	$(PYTHON) $(CAD)/machine.py

## cut:     ruled-solid + swept-wire sim -> sim/out/{extrusion,taper}.png, cut_sweep.gif
cut:
	$(PYTHON) $(SIM)/cut_sim.py

## nest:    nesting cut sim -> sim/out/{nest_plan,nest_parts}.png, nest_cut.gif
nest:
	$(PYTHON) $(SIM)/nest_sim.py

## wire:    thermo-mechanical wire sizing -> sim/out/wire_analysis.png + sizing table
wire:
	$(PYTHON) $(SIM)/wire_analysis.py

## driver:  heater-driver electro-thermal sim -> sim/out/heater_driver.png + component table
driver:
	$(PYTHON) $(SIM)/heater_driver.py

## tensioner: verify printed parts (watertight) + render tensioner assembly/diagram
tensioner:
	$(PYTHON) $(CAD)/tensioner_bracket.py
	$(PYTHON) $(CAD)/tensioner_sled.py
	$(PYTHON) $(CAD)/tensioner.py

## mujoco:  INTERACTIVE MuJoCo viewer — drag sliders to drive the 4 axes, wire follows
mujoco:
	$(PYTHON) $(SIM)/mujoco_sim.py

## mujoco-demo: headless scripted sweep -> sim/out/mujoco_sweep.gif (no window)
mujoco-demo:
	$(PYTHON) $(SIM)/mujoco_sim.py --demo

## mujoco-selftest: build + step, print sanity, no window (CI-safe)
mujoco-selftest:
	$(PYTHON) $(SIM)/mujoco_sim.py --selftest

## snap:    log current machine render into the dated history (NOTE=... optional)
snap:
	MACHINE=cnc_hotwire NOTE=$(NOTE) bash $(CAD)/snap.sh

## clean:   remove generated build + sim outputs (keeps renders/ history)
clean:
	rm -f $(CAD)/build/* $(SIM)/out/*

## help:    list targets
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## //'
