# CNC hot-wire foam cutter — build & simulation
# Usage: `make` runs the sims; `make help` lists all targets.
PYTHON ?= python3
CAD    := cad
SIM    := sim
NOTE   ?= update

.DEFAULT_GOAL := sim
.PHONY: all sim machine cut nest snap clean help

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

## snap:    log current machine render into the dated history (NOTE=... optional)
snap:
	MACHINE=cnc_hotwire NOTE=$(NOTE) bash $(CAD)/snap.sh

## clean:   remove generated build + sim outputs (keeps renders/ history)
clean:
	rm -f $(CAD)/build/* $(SIM)/out/*

## help:    list targets
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## //'
