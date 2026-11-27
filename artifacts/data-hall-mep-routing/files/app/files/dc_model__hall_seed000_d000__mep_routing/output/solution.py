#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dc_model  hall_seed000_d000  --  coordinated overhead MEP model, IFC4.

Rebuilds the data hall exactly as the seven-sheet drawing set describes it and
routes the three overhead services (telecom cable tray, power busway, chilled
water) through the plenum so that

  * nothing clashes (hard gate),
  * each service is one connected network that reaches its service entry,
  * every rack row is served by all three services,
  * every CRAH (including the perimeter units) is reached by chilled water,
  * the code rules hold (2600 headroom, 460 clear under every sprinkler
    deflector, 25.4 mm pipe insulation inside the clash envelope, 300 mm
    tray/busway separation, no CHW in the 1800 mm dedicated space above a PDU).

Everything that was read off the drawings is baked in as a literal below --
the script never opens the PNGs.

Usage
-----
    python3 solution.py [output.ifc]
"""

import hashlib
import json
import math
import os
import sys

import numpy as np

import ifcopenshell
import ifcopenshell.guid
import ifcopenshell.validate

# =============================================================================
# 1.  DRAWING-DERIVED LITERALS  (all values in millimetres unless stated)
# =============================================================================
#
# Sheet frame / raster facts (all seven sheets are 1600 x 1100 px, 13.0 px/m on
# the 1:100 sheets A-101/A-301 and 26.3 px/m on the 1:50 sheets M/E/F-101).
#
# A-101 equipment plan: interior wall faces at px x 463..818, y 194..470
#   -> 355 x 276 px  ==  27 000 x 21 000 mm  (scale 13.15 px/m)
# A-301 building section: FFL at px y 524, structural soffit at y 240,
#   roof slab 212..240, structural slab 596..620, access floor void 524..592.
# A-601 cabinet schedule: 128 cabinets, 600 wide x 1200 deep footprint.
# A-602 containment / pathway / construction data: 300 mm tray-busway
#   separation, 2600 mm headroom, 25.4 mm CHW insulation, hanger spacing.
# M-101 / E-101: service entries in the west wall at y ~ 10 000.
# F-101 sprinkler grid: 9 x 7 heads at 3000 mm both ways, centred on the hall.
#
HALL_X = 27000.0            # A-101 interior width  (E-W)
HALL_Y = 21000.0            # A-101 interior depth  (N-S)
WALL_T = 300.0              # A-101 wall build-up
SOFFIT_Z = 4800.0           # A-301 clear height, FFL -> structural soffit
ROOF_T = 300.0              # A-301 roof slab
SLAB_TOP = -700.0           # A-301 structural slab top (under-floor plenum)
SLAB_T = 300.0              # A-301 structural slab
ACCESS_FLOOR_T = 30.0       # access floor panel (FFL = 0)
TILE = 600.0                # A-101 access-floor tile pitch (7.87 px)

# --- vertical tiers, from the A-301 section callouts ----------------------
DEFLECTOR_Z = 4400.0        # F-101/A-301 sprinkler deflector elevation
TRAY_BOT, TRAY_TOP = 3700.0, 3800.0     # cable tray  300 x 100, top tier
BUS_BOT, BUS_TOP = 3250.0, 3400.0       # busway      200 x 150, middle tier
CHW_Z = 2750.0                          # CHW centreline, bottom tier
TRAY_W, TRAY_H = 300.0, 100.0
BUS_W, BUS_H = 200.0, 150.0
CHW_OD = 168.0              # M-101 CHW pipe outside diameter
CHW_INSUL = 25.4            # M-101/A-602 insulation thickness
CHW_OUT = CHW_OD + 2 * CHW_INSUL        # 218.8 mm clash envelope
HEADROOM_MIN = 2600.0       # A-602 code note
DEFLECTOR_CLEAR = 460.0     # F-101 note: clear below every deflector
NFPA_OBSTRUCTION = 450.0    # F-101 note: NFPA 13 obstruction band
TRAY_BUS_SEP = 300.0        # A-602 note: tray / busway separation
PDU_DEDICATED = 1800.0      # E-101 note: dedicated space above a PDU

# --- equipment (A-101 / A-601) -------------------------------------------
RACK_W, RACK_D, RACK_H = 600.0, 1200.0, 2000.0
N_RACKS = 128                                   # A-601 cabinet schedule
# rack-row centres measured off A-101 (px -> mm, y flipped) and snapped to the 600 mm floor-tile grid (A-101 measured values
# 16778 / 13734 / 11375 / 8408 / 5973 / 2929 mm)
ROW_Y = [16800.0, 13800.0, 11400.0, 8400.0, 6000.0, 3000.0]
ROW_COUNT = [22, 21, 22, 21, 21, 21]            # sums to 128
# A-101 rack bands, measured per row (px -> mm at 76.06 mm/px, wall face at
# px 463).  Each row has its own drawn extent:
#   row 1  px 488..729 = 1 901..20 231     row 2  px 488..716 = 1 901..19 242
#   row 3  px 487..725 = 1 825..19 927     row 4  px 488..719 = 1 901..19 470
#   row 5  px 487..725 = 1 825..19 927     row 6  px 488..716 = 1 901..19 242
# The block break is drawn at px 590..613 = 9 660..11 410 mm.
# Cabinets are laid on the drawn 600 mm pitch anchored on each row's drawn
# west face; no cabinet may fall outside its drawn band or across the break.
ROW_EXT_DRAW = [(1901.0, 20231.0), (1901.0, 19242.0), (1825.0, 19927.0),
                (1901.0, 19470.0), (1825.0, 19927.0), (1901.0, 19242.0)]
BLOCK_GAP_X0, BLOCK_GAP_X1 = 9660.0, 11410.0     # drawn block break


def _row_cells(west, east, pitch=RACK_W):
    out, k = [], 0
    while west + (k + 1) * pitch <= east + 1.0:
        x = west + k * pitch
        if not (BLOCK_GAP_X0 < x + pitch / 2.0 < BLOCK_GAP_X1):
            out.append(x)
        k += 1
    return out


ROW_CELLS = [_row_cells(w, e) for (w, e) in ROW_EXT_DRAW]
ROW_X0 = min(c[0] for c in ROW_CELLS)            # 1 825 mm
ROW_X_END = max(c[-1] + RACK_W for c in ROW_CELLS)
ROW_FACE = [180.0, 0.0, 180.0, 0.0, 180.0, 0.0]  # front (door) direction, deg

# A-101 perimeter units (fan symbols / unit boxes, ~16-18 px = 1.2-1.4 m wide):
#   south wall  px x = 471..487, 583..600, 695..712, 785..801
#               -> centres 1 445 / 10 040 / 18 710 / 25 100 mm
#   north wall  px x = 750..765, 779..794 (the only unit symbols on that wall;
#               the remaining north-wall annotations are labels only)
#               -> centres 22 400 / 24 606 mm
CRAH_W, CRAH_D, CRAH_H = 1400.0, 1200.0, 2600.0
CRAH_N_Y = HALL_Y - CRAH_D                      # 19 800 .. 21 000 (north wall)
CRAH_S_Y = 0.0                                  #      0 ..  1 200 (south wall)
CRAH_X_S = [1445.0, 10040.0, 18710.0, 25100.0]  # drawn south-wall centres
CRAH_X_N = [22400.0, 24606.0]                   # drawn north-wall centres
CRAH_X = sorted(CRAH_X_S + CRAH_X_N)

# E-101 / A-101 PDU box at each row: px x 753..763 -> 22 050..22 820 mm
PDU_W, PDU_D, PDU_H = 760.0, 1200.0, 2000.0
PDU_X = 22050.0
# no interior columns are drawn on A-101 / A-301 (see the structure block)

HEAD_PITCH = 3000.0                             # F-101
HEAD_NX, HEAD_NY = 9, 7                         # 63 heads
HEAD_X0 = (HALL_X - (HEAD_NX - 1) * HEAD_PITCH) / 2.0     # 1500
HEAD_Y0 = (HALL_Y - (HEAD_NY - 1) * HEAD_PITCH) / 2.0     # 1500

ENTRY_Y = 10000.0                               # M-101 / E-101 west-wall entries (measured y ~9.9 m)
TRAY_SPINE_X = 1100.0
BUS_SPINE_X = 1500.0
CHW_SPINE_X = 800.0
RUN_X0, RUN_X1 = 1100.0, ROW_X_END              # row headers reach the row end
CHW_RUN_X1 = ROW_X_END
SUPPORT_PITCH = 1500.0                          # A-602 max hanger spacing
CONTAINMENT_DECK_T = 100.0                      # A-101 cold-aisle deck at rack top
AISLE_HEAD_Z = RACK_H - 85.0                    # deflector of the heads under the deck
AISLE_HEAD_PITCH = 3000.0                       # F-101 head spacing

EPS = 2.0                                       # clash tolerance (mm)

# =============================================================================
# 2.  GENERIC HELPERS
# =============================================================================


def rng(a, b, n):
    """n evenly spaced values from a to b (inclusive)."""
    if n <= 1:
        return [a]
    return [a + (b - a) * i / (n - 1.0) for i in range(n)]


class Reg:
    """Canonical solid registry -- single source of truth for routing,
    clash checking, code checking and IFC authoring."""

    def __init__(self):
        self.items = []

    def add(self, kind, x0, x1, y0, y1, z0, z1, meta=None, rot=0.0,
            profile="rect", diameter=None):
        x0, x1 = sorted((float(x0), float(x1)))
        y0, y1 = sorted((float(y0), float(y1)))
        z0, z1 = sorted((float(z0), float(z1)))
        if x1 - x0 < 0.5 or y1 - y0 < 0.5 or z1 - z0 < 0.5:
            raise ValueError("degenerate solid %s %r" % (kind, (x0, x1, y0, y1, z0, z1)))
        it = dict(kind=kind, x0=x0, x1=x1, y0=y0, y1=y1, z0=z0, z1=z1,
                  meta=dict(meta or {}), rot=rot, profile=profile,
                  diameter=diameter)
        self.items.append(it)
        return it

    def by_kind(self, *kinds):
        ks = set(kinds)
        return [i for i in self.items if i["kind"] in ks]

    # ---- clash ----------------------------------------------------------
    def clashes(self, ignore_pairs=(), tol=EPS):
        items = self.items
        n = len(items)
        lo = np.array([[i["x0"], i["y0"], i["z0"]] for i in items])
        hi = np.array([[i["x1"], i["y1"], i["z1"]] for i in items])
        out = []
        # broad phase: sort on x0, sweep
        order = np.argsort(lo[:, 0])
        for a in range(n):
            ia = order[a]
            for b in range(a + 1, n):
                ib = order[b]
                if lo[ib, 0] > hi[ia, 0] - tol:
                    break
                ov = np.minimum(hi[ia], hi[ib]) - np.maximum(lo[ia], lo[ib])
                if ov[0] > tol and ov[1] > tol and ov[2] > tol:
                    ka, kb = items[ia]["kind"], items[ib]["kind"]
                    if (ka, kb) in ignore_pairs or (kb, ka) in ignore_pairs:
                        continue
                    out.append((ia, ib, ov.tolist()))
        return out


R = Reg()

# =============================================================================
# 3.  SHELL AND FIT-OUT
# =============================================================================
# --- structure ------------------------------------------------------------
R.add("SLAB_STRUCT", -WALL_T, HALL_X + WALL_T, -WALL_T, HALL_Y + WALL_T,
      SLAB_TOP - SLAB_T, SLAB_TOP,
      {"name": "Structural slab", "PredefinedType": "BASESLAB"})
R.add("ACCESS_FLOOR", 0.0, HALL_X, 0.0, HALL_Y,
      -ACCESS_FLOOR_T, 0.0,
      {"name": "Access floor", "PredefinedType": "FLOOR", "Tile": TILE})
R.add("ROOF", -WALL_T, HALL_X + WALL_T, -WALL_T, HALL_Y + WALL_T,
      SOFFIT_Z, SOFFIT_Z + ROOF_T,
      {"name": "Roof slab", "PredefinedType": "ROOF"})
for nm, (x0, x1, y0, y1) in {
        "South wall": (0.0, HALL_X, -WALL_T, 0.0),
        "North wall": (0.0, HALL_X, HALL_Y, HALL_Y + WALL_T),
        "West wall": (-WALL_T, 0.0, 0.0, HALL_Y),
        "East wall": (HALL_X, HALL_X + WALL_T, 0.0, HALL_Y)}.items():
    R.add("WALL", x0, x1, y0, y1, 0.0, SOFFIT_Z, {"name": nm})

# --- structural columns ---------------------------------------------------
# A-101 and A-301 were re-examined for column symbols: the plan shows none
# inside the hall (the aisles between the rack rows carry only equipment
# labels) and the section shows no interior vertical element between FFL and
# the soffit - the roof is clear-span on the perimeter walls.  No interior
# columns are therefore modelled; should the structural package later add a
# grid it can be inserted here without touching the routes.
COLUMNS_DRAWN = False

# --- rack rows (A-101 plan, A-601 schedule) -------------------------------
# The drawn cells are the 600 mm cabinet positions of A-101 (block A 1 800..
# 9 600, break, block B 11 400..20 400).  The 128 scheduled cabinets are
# distributed over every drawn cell so that each row keeps the drawn extent:
# the first and the last cell of the row are always populated.
ROW_EXTENT = {}
for ri, (cy, cnt) in enumerate(zip(ROW_Y, ROW_COUNT)):
    cells = ROW_CELLS[ri]
    ncell = len(cells)
    if cnt == ncell:
        sel = list(range(ncell))
    else:
        sel = sorted({int(round(i * (ncell - 1) / float(cnt - 1)))
                      for i in range(cnt)})
    while len(sel) < cnt:                     # guarantee exactly `cnt` racks
        for c in range(ncell):
            if c not in sel:
                sel.append(c)
                break
        sel.sort()
    for k, ci in enumerate(sel):
        bx = cells[ci]
        cx = bx + RACK_W / 2
        R.add("RACK", cx - RACK_W / 2, cx + RACK_W / 2,
              cy - RACK_D / 2, cy + RACK_D / 2, 0.0, RACK_H,
              {"name": "Rack %d-%02d" % (ri + 1, k + 1),
               "row": ri + 1, "idx": k + 1, "facing": ROW_FACE[ri],
               "cell": ci, "x": cx, "y": cy}, rot=ROW_FACE[ri])
    ROW_EXTENT[ri + 1] = (cells[sel[0]], cells[sel[-1]] + RACK_W)

# --- CRAHs (perimeter, A-101 / M-101) -------------------------------------
crahs = []
for tag, xs, y0 in (("N", CRAH_X_N, CRAH_N_Y), ("S", CRAH_X_S, CRAH_S_Y)):
    for i, cx in enumerate(xs):
        nm = "CRAH-%s%d" % (tag, i + 1)
        crahs.append((nm, cx, y0))
        R.add("CRAH", cx - CRAH_W / 2, cx + CRAH_W / 2, y0, y0 + CRAH_D,
              0.0, CRAH_H,
              {"name": nm, "x": cx, "y": y0 + CRAH_D / 2, "wall": tag})

# --- PDUs (E-101) ---------------------------------------------------------
pdus = []
for ri, cy in enumerate(ROW_Y):
    pdus.append(("PDU-%d" % (ri + 1), PDU_X, cy))
    R.add("PDU", PDU_X, PDU_X + PDU_W, cy - PDU_D / 2, cy + PDU_D / 2,
          0.0, PDU_H, {"name": "PDU-%d" % (ri + 1), "x": PDU_X + PDU_W / 2,
                        "y": cy})

# --- cold-aisle containment (A-101: enclosed aisles) ----------------------
# End panels close the aisle at both ends; a deck at rack-top level closes it
# overhead.  The deck is a containment roof, so F-101 requires sprinkler
# heads beneath it - modelled below (AISLE_HEADS).
AISLES = []
for pi in (0, 2, 4):
    ya, yb = ROW_Y[pi + 1] + RACK_D / 2, ROW_Y[pi] - RACK_D / 2
    AISLES.append((ya, yb))
    for xe in (ROW_X0 - 100.0, ROW_X_END):
        R.add("CONTAINMENT", xe, xe + 100.0, ya, yb, 0.0, RACK_H,
              {"name": "Containment end panel", "Type": "Cold aisle end panel",
               "role": "End panel"})
    R.add("CONTAINMENT_ROOF", ROW_X0, ROW_X_END, ya, yb,
          RACK_H, RACK_H + CONTAINMENT_DECK_T,
          {"name": "Cold aisle deck", "Type": "Cold aisle containment roof",
           "role": "Roof"})

# --- sprinkler heads (F-101, 9 x 7 grid) ----------------------------------
heads = []
for j in range(HEAD_NY):
    for i in range(HEAD_NX):
        hx = HEAD_X0 + i * HEAD_PITCH
        hy = HEAD_Y0 + j * HEAD_PITCH
        heads.append((hx, hy))
        R.add("SPRINKLER", hx - 50, hx + 50, hy - 50, hy + 50,
              DEFLECTOR_Z, DEFLECTOR_Z + 80,
              {"name": "Sprinkler %d-%d" % (j + 1, i + 1), "x": hx, "y": hy,
               "deflector": DEFLECTOR_Z, "role": "Ceiling"})

# --- sprinkler heads beneath the containment roofs (F-101 obstruction rule)
AISLE_HEADS = []
for ai, (ya, yb) in enumerate(AISLES):
    n = int((ROW_X_END - ROW_X0) // AISLE_HEAD_PITCH) + 1
    for k, hx in enumerate(rng(ROW_X0 + 600.0, ROW_X_END - 600.0, n)):
        hy = (ya + yb) / 2.0
        nm = "Sprinkler A%d-%d" % (ai + 1, k + 1)
        AISLE_HEADS.append(nm)
        R.add("SPRINKLER", hx - 50, hx + 50, hy - 50, hy + 50,
              AISLE_HEAD_Z, RACK_H - 5.0,
              {"name": nm, "x": hx, "y": hy, "deflector": AISLE_HEAD_Z,
               "role": "Containment roof"})

# =============================================================================
# 4.  ROUTING
# =============================================================================
# Tier / topology (all axis aligned, every change of direction or tier is a
# new segment):
#
#   TRAY    z 3700..3800 at y = row-pair centre, spine at x = 1100
#   BUSWAY  z 3250..3400 at the same y, spine at x = 1500
#   CHW     z 2750 centre (envelope 218.8) at the same y, spine at x = 800
#           plus north / south CRAH manifolds at y = 20550 / 450
#
PAIR_Y = [(ROW_Y[0] + ROW_Y[1]) / 2.0,
          (ROW_Y[2] + ROW_Y[3]) / 2.0,
          (ROW_Y[4] + ROW_Y[5]) / 2.0]                      # 15256, 9891, 4451

segs = []          # (service, p0, p1, width, height, meta)


def seg(service, p0, p1, w, h, **meta):
    p0 = tuple(float(v) for v in p0)
    p1 = tuple(float(v) for v in p1)
    assert p0 != p1, (service, p0)
    assert sum(1 for a, b in zip(p0, p1) if abs(a - b) > 1e-9) == 1, (service, p0, p1)
    segs.append((service, p0, p1, w, h, meta))


def split_run(service, p, q, cuts, w, h, **meta):
    """Emit a straight run p->q split at every crossing point in `cuts`
    (so that every junction is an exact endpoint-to-endpoint connection)."""
    axis = 0 if abs(q[0] - p[0]) > 1e-9 else 1
    lo, hi = sorted((p[axis], q[axis]))
    cs = sorted({round(lo, 3), round(hi, 3)} |
                {round(c, 3) for c in cuts if lo + 1e-6 < c < hi - 1e-6})
    for a, b in zip(cs, cs[1:]):
        pa = list(p); pb = list(p)
        pa[axis] = a; pb[axis] = b
        seg(service, pa, pb, w, h, **meta)


# ---- cable tray ----------------------------------------------------------
# Junctions are face-to-face with a 1 mm penetration: the solids intersect
# (so the network is unambiguously connected) yet the overlap stays well
# below the 2 mm clash tolerance.
INT = 1.0
TRAY_MZ = (TRAY_BOT + TRAY_TOP) / 2.0
BUS_MZ = (BUS_BOT + BUS_TOP) / 2.0

tray_cuts = [ENTRY_Y] + PAIR_Y
split_run("TRAY", (TRAY_SPINE_X, min(PAIR_Y) - TRAY_W / 2, TRAY_MZ),
          (TRAY_SPINE_X, max(PAIR_Y) + TRAY_W / 2, TRAY_MZ),
          tray_cuts, TRAY_W, TRAY_H, tier=1)
for y in PAIR_Y:
    seg("TRAY", (TRAY_SPINE_X + TRAY_W / 2 - INT, y, TRAY_MZ), (RUN_X1, y, TRAY_MZ),
        TRAY_W, TRAY_H, tier=1)
seg("TRAY", (0.0, ENTRY_Y, TRAY_MZ), (TRAY_SPINE_X - TRAY_W / 2 + INT, ENTRY_Y, TRAY_MZ),
    TRAY_W, TRAY_H, tier=1, entry=True)

# ---- busway --------------------------------------------------------------
split_run("BUSWAY", (BUS_SPINE_X, min(PAIR_Y) - BUS_W / 2, BUS_MZ),
          (BUS_SPINE_X, max(PAIR_Y) + BUS_W / 2, BUS_MZ),
          tray_cuts, BUS_W, BUS_H, tier=2)
for y in PAIR_Y:
    seg("BUSWAY", (BUS_SPINE_X + BUS_W / 2 - INT, y, BUS_MZ), (RUN_X1, y, BUS_MZ),
        BUS_W, BUS_H, tier=2)
seg("BUSWAY", (0.0, ENTRY_Y, BUS_MZ), (BUS_SPINE_X - BUS_W / 2 + INT, ENTRY_Y, BUS_MZ),
    BUS_W, BUS_H, tier=2, entry=True)

# ---- chilled water -------------------------------------------------------
CHW_Y_N = CRAH_N_Y + CRAH_D / 2        # 20550
CHW_Y_S = CRAH_S_Y + CRAH_D / 2        # 450
CHW_TOP_CONN = CHW_Z - CHW_OUT / 2     # manifold soffit, drops land here
chw_cuts = [ENTRY_Y] + PAIR_Y
split_run("CHW", (CHW_SPINE_X, CHW_Y_S - CHW_OUT / 2, CHW_Z),
          (CHW_SPINE_X, CHW_Y_N + CHW_OUT / 2, CHW_Z),
          chw_cuts, CHW_OUT, CHW_OUT, tier=3, diameter=CHW_OD)
for y in PAIR_Y:
    seg("CHW", (CHW_SPINE_X + CHW_OUT / 2 - INT, y, CHW_Z), (CHW_RUN_X1, y, CHW_Z),
        CHW_OUT, CHW_OUT, tier=3, diameter=CHW_OD)
seg("CHW", (0.0, ENTRY_Y, CHW_Z), (CHW_SPINE_X - CHW_OUT / 2 + INT, ENTRY_Y, CHW_Z),
    CHW_OUT, CHW_OUT, tier=3, entry=True, diameter=CHW_OD)
# CRAH manifolds (the perimeter units that no row header passes)
for yman in (CHW_Y_N, CHW_Y_S):
    seg("CHW", (CHW_SPINE_X + CHW_OUT / 2 - INT, yman, CHW_Z),
        (CRAH_X[-1] + CRAH_W / 2, yman, CHW_Z),
        CHW_OUT, CHW_OUT, tier=3, diameter=CHW_OD)
# drops to every CRAH (top connection at CRAH_H)
for (nm, cx, y0) in crahs:
    yd = y0 + CRAH_D / 2
    seg("CHW", (cx, yd, CRAH_H + 5.0), (cx, yd, CHW_TOP_CONN + INT), CHW_OUT, CHW_OUT,
        tier=3, drop=True, serves=nm, diameter=CHW_OD)

# ---- build the solids ----------------------------------------------------
for (service, p0, p1, w, h, meta) in segs:
    meta = dict(meta)
    meta["length"] = math.dist(p0, p1)      # true centreline length (mm)
    x0, x1 = sorted((p0[0], p1[0]))
    y0, y1 = sorted((p0[1], p1[1]))
    z0, z1 = sorted((p0[2], p1[2]))
    if p0[2] != p1[2]:                      # vertical drop
        x0, x1 = p0[0] - w / 2, p0[0] + w / 2
        y0, y1 = p0[1] - w / 2, p0[1] + w / 2
    else:
        if p0[0] != p1[0]:                  # runs along X
            y0, y1 = p0[1] - w / 2, p0[1] + w / 2
            z0, z1 = p0[2] - h / 2, p0[2] + h / 2
        else:                               # runs along Y
            x0, x1 = p0[0] - w / 2, p0[0] + w / 2
            z0, z1 = p0[2] - h / 2, p0[2] + h / 2
    d = meta.get("diameter")
    R.add(service, x0, x1, y0, y1, z0, z1, meta,
          profile="circle" if d else "rect", diameter=d)

# ---- hangers / supports (optional diagnostics, A-602 max spacing) --------
# Every support line is laid out at <= 1500 mm pitch.  Where a rod would land
# under a sprinkler head it is offset sideways inside the carrier footprint
# (never omitted), so the spacing never opens up.
n_sup = 0
SUPPORTS = []


def support_positions(a, b, pitch=SUPPORT_PITCH):
    n = max(2, int(math.ceil((b - a) / pitch)) + 1)
    xs = [a + (b - a) * i / float(n - 1) for i in range(n)]
    gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    return xs, max(gaps)


def add_support(x0, x1, y0, y1, z0, z1, svc, typ, gap, tag):
    global n_sup
    n_sup += 1
    it = R.add("SUPPORT", x0, x1, y0, y1, z0, z1,
               {"name": "%s %d" % (typ, n_sup), "Type": typ, "service": svc,
                "gap": gap, "run": tag})
    SUPPORTS.append(it)


for k, y in enumerate(PAIR_Y):
    # tray hangers: rod offset +120 mm in Y -> clear of the head boxes
    xs, g = support_positions(TRAY_SPINE_X + 550.0, RUN_X1 - 400.0)
    for x in xs:
        add_support(x - 20, x + 20, y + 100.0, y + 140.0, TRAY_TOP, SOFFIT_Z,
                    "TRAY", "Hanger", g, "tray-row-%d" % (k + 1))
    # busway supports: rod offset -75 mm in Y -> inside the 200 mm busway and
    # clear of the sprinkler heads at y = 4500 + n*3000
    xs, g = support_positions(BUS_SPINE_X + 600.0, RUN_X1 - 700.0)
    for x in xs:
        add_support(x - 20, x + 20, y - 95.0, y - 55.0, BUS_TOP, TRAY_BOT,
                    "BUSWAY", "Support", g, "busway-row-%d" % (k + 1))
    # busway row supports at 1500 pitch as well

# spine supports
xs, g = support_positions(min(PAIR_Y) - TRAY_W / 2 + 100.0,
                          max(PAIR_Y) + TRAY_W / 2 - 100.0)
for y in xs:
    add_support(TRAY_SPINE_X - 20, TRAY_SPINE_X + 20, y - 20, y + 20,
                TRAY_TOP, SOFFIT_Z, "TRAY", "Hanger", g, "tray-spine")
xs, g = support_positions(min(PAIR_Y) - BUS_W / 2 + 100.0,
                          max(PAIR_Y) + BUS_W / 2 - 100.0)
for y in xs:
    add_support(BUS_SPINE_X + 55.0, BUS_SPINE_X + 95.0, y - 20, y + 20,
                BUS_TOP, TRAY_BOT, "BUSWAY", "Support", g, "busway-spine")

# =============================================================================
# 5.  CHECKS
# =============================================================================
errors = []
warnings = []


def mm(v):
    return "%.1f" % v


# ---- 5.1 clashes ---------------------------------------------------------
IGNORE = {
    ("RACK", "RACK"),           # adjacent cabinets share a face
    ("SPRINKLER", "SPRINKLER"),
}
cl = [c for c in R.clashes() if (R.items[c[0]]["kind"], R.items[c[1]]["kind"]) not in IGNORE
      and (R.items[c[1]]["kind"], R.items[c[0]]["kind"]) not in IGNORE]
if cl:
    for (ia, ib, ov) in cl[:20]:
        errors.append("clash %s %s / %s %s overlap %s" %
                      (R.items[ia]["kind"], R.items[ia]["meta"].get("name", ""),
                       R.items[ib]["kind"], R.items[ib]["meta"].get("name", ""),
                       [round(v, 1) for v in ov]))

# ---- 5.2 headroom --------------------------------------------------------
for it in R.items:
    if it["kind"] in ("TRAY", "BUSWAY", "CHW", "SUPPORT"):
        if it["meta"].get("drop"):
            continue                      # vertical drop to an equipment connection
        if it["z0"] < HEADROOM_MIN - 1e-6:
            errors.append("headroom %.1f < 2600 for %s" % (it["z0"], it["kind"]))

# ---- 5.3 deflector clearance --------------------------------------------
# Only solids that actually pass BELOW a deflector are obstructions; runs above
# a head (e.g. over a cold-aisle deck) cannot obstruct it.
for h in R.by_kind("SPRINKLER"):
    for it in R.items:
        if it["kind"] not in ("TRAY", "BUSWAY", "CHW"):
            continue
        if it["meta"].get("drop"):
            continue
        if it["z1"] > h["z0"] + 1e-6:
            continue
        # does the run pass below the head?
        if (it["x0"] <= h["x1"] and it["x1"] >= h["x0"] and
                it["y0"] <= h["y1"] and it["y1"] >= h["y0"]):
            clear = h["z0"] - it["z1"]
            if clear < DEFLECTOR_CLEAR - 1e-6:
                errors.append("deflector clearance %.1f < %.1f (%s)" %
                              (clear, DEFLECTOR_CLEAR, it["kind"]))
            if DEFLECTOR_CLEAR - 1e-6 <= clear < NFPA_OBSTRUCTION:
                warnings.append("run within the NFPA-13 obstruction band under a head")

# ---- 5.3b every containment roof has sprinkler heads beneath it ---------
for roof in R.by_kind("CONTAINMENT_ROOF"):
    under = [h for h in R.by_kind("SPRINKLER")
             if roof["x0"] <= (h["x0"] + h["x1"]) / 2 <= roof["x1"]
             and roof["y0"] <= (h["y0"] + h["y1"]) / 2 <= roof["y1"]
             and h["z1"] <= roof["z0"] + 1e-6]
    if not under:
        errors.append("containment roof at y %.0f has no sprinkler head beneath" % roof["y0"])

# ---- 5.4 heads under wide runs / containment roofs ----------------------
for it in R.by_kind("TRAY", "BUSWAY", "CHW"):
    wid = min(it["x1"] - it["x0"], it["y1"] - it["y0"])
    if wid > 1200.0:
        errors.append("run wider than 1200 mm without heads beneath: %r" % wid)

# ---- 5.5 tray / busway separation ---------------------------------------
tray_ref = (TRAY_BOT + TRAY_TOP) / 2
sep_v = TRAY_BOT - BUS_TOP
if sep_v < TRAY_BUS_SEP - 1e-6:
    errors.append("tray/busway vertical separation %.1f < 300" % sep_v)

# ---- 5.6 CHW in the dedicated space above a PDU -------------------------
for p in R.by_kind("PDU"):
    for it in R.by_kind("CHW"):
        if (it["x0"] < p["x1"] and it["x1"] > p["x0"] and
                it["y0"] < p["y1"] and it["y1"] > p["y0"] and
                it["z1"] > p["z1"] and it["z0"] < p["z1"] + PDU_DEDICATED):
            errors.append("CHW inside the 1800 mm dedicated space above %s" %
                          p["meta"].get("name"))

# ---- 5.7 connectivity ----------------------------------------------------
def graph_ok(service, eps=0.5):
    """Union-find over the segments of one service.  Two segments belong to
    the same network when their bounding boxes touch or intersect (the
    junctions are modelled face-to-face with a 1 mm penetration)."""
    boxes = []
    entry = []
    for (s, p0, p1, w, h, meta) in segs:
        if s != service:
            continue
        if p0[2] != p1[2]:
            x0, x1 = p0[0] - w / 2, p0[0] + w / 2
            y0, y1 = p0[1] - w / 2, p0[1] + w / 2
            z0, z1 = min(p0[2], p1[2]), max(p0[2], p1[2])
        elif abs(p0[0] - p1[0]) > 1e-9:
            x0, x1 = min(p0[0], p1[0]), max(p0[0], p1[0])
            y0, y1 = p0[1] - w / 2, p0[1] + w / 2
            z0, z1 = p0[2] - h / 2, p0[2] + h / 2
        else:
            x0, x1 = p0[0] - w / 2, p0[0] + w / 2
            y0, y1 = min(p0[1], p1[1]), max(p0[1], p1[1])
            z0, z1 = p0[2] - h / 2, p0[2] + h / 2
        boxes.append((x0, x1, y0, y1, z0, z1))
        entry.append(bool(meta.get("entry")))
    n = len(boxes)
    par = list(range(n))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for i in range(n):
        for j in range(i + 1, n):
            dx = max(boxes[i][0] - boxes[j][1], boxes[j][0] - boxes[i][1], 0.0)
            dy = max(boxes[i][2] - boxes[j][3], boxes[j][2] - boxes[i][3], 0.0)
            dz = max(boxes[i][4] - boxes[j][5], boxes[j][4] - boxes[i][5], 0.0)
            if dx <= eps and dy <= eps and dz <= eps:
                ra, rb = find(i), find(j)
                if ra != rb:
                    par[rb] = ra
    roots = {find(i) for i in range(n)}
    return len(roots) == 1, roots, [i for i in range(n) if entry[i]]


for svc in ("TRAY", "BUSWAY", "CHW"):
    ok, roots, ent = graph_ok(svc)
    if not ok:
        errors.append("%s network is not connected (%d components)" % (svc, len(roots)))
    if not ent:
        errors.append("%s has no entry segment" % svc)

# ---- 5.8 every row served by all three services -------------------------
row_report = {}
for ri, cy in enumerate(ROW_Y):
    xa, xb = ROW_EXTENT[ri + 1]
    row_report[ri + 1] = dict(y=cy, x0=xa, x1=xb, services={},
                              racks=ROW_COUNT[ri])
    for svc in ("TRAY", "BUSWAY", "CHW"):
        best = 0.0
        near = 1e9
        for it in R.by_kind(svc):
            if it["z0"] > 4000:            # only overhead runs count
                continue
            dy = max(it["y0"] - cy, cy - it["y1"], 0.0)
            if dy > 2500.0:
                continue
            ov = max(0.0, min(it["x1"], xb) - max(it["x0"], xa))
            if ov > best:
                best = ov
            near = min(near, dy)
        frac = best / max(1.0, xb - xa)
        row_report[ri + 1]["services"][svc] = dict(cover=round(frac, 3),
                                                   lateral=round(near, 1))
        if frac < 0.80 - 1e-9:
            errors.append("row %d served %.0f%% by %s (<80%%)" % (ri + 1, frac * 100, svc))
        if near > 2500.0:
            errors.append("row %d not within 2500 mm of %s" % (ri + 1, svc))

# ---- 5.9 every CRAH reached by CHW --------------------------------------
crah_report = []
for (nm, cx, y0) in crahs:
    yd = y0 + CRAH_D / 2
    best = 1e9
    for it in R.by_kind("CHW"):
        dx = max(it["x0"] - cx, cx - it["x1"], 0.0)
        dy = max(it["y0"] - yd, yd - it["y1"], 0.0)
        best = min(best, math.hypot(dx, dy))
    crah_report.append(dict(name=nm, dist=round(best, 1)))
    if best > 2500.0:
        errors.append("CRAH %s not reached by CHW (%.0f mm)" % (nm, best))

if errors:
    print("SELF-CHECK FAILED")
    for e in errors:
        print("  !", e)
    sys.exit(1)

# =============================================================================
# 6.  DIAGNOSTICS
# =============================================================================
def length_of(it):
    """Centreline length of a routed segment (from its endpoints)."""
    return it["meta"]["length"]


lengths = {}
for svc in ("TRAY", "BUSWAY", "CHW"):
    over = under = 0.0
    for it in R.by_kind(svc):
        L = length_of(it)
        if it["z1"] <= 0:
            under += L
        elif it["z0"] >= HEADROOM_MIN:
            over += L
        else:
            # vertical connection below the clear-height band
            under += 0.0
            over += L
    lengths[svc] = dict(overhead=round(over, 1), underfloor=round(under, 1),
                        total=round(over + under, 1))
L_total = sum(v["total"] for v in lengths.values())

# support spacing check (A-602 maximum)
for it in R.by_kind("SUPPORT"):
    if it["meta"].get("gap", 0.0) > SUPPORT_PITCH + 1e-6:
        errors.append("support spacing %.0f > %.0f (%s)" %
                      (it["meta"]["gap"], SUPPORT_PITCH, it["meta"].get("run")))

head_clear = []
for h in R.by_kind("SPRINKLER"):
    dz = h["meta"]["deflector"]
    rec = dict(id=h["meta"]["name"], x=h["meta"]["x"], y=h["meta"]["y"],
               deflector=dz, role=h["meta"].get("role", "Ceiling"),
               services=[], above=[])
    for svc in ("TRAY", "BUSWAY", "CHW"):
        inplan = [it for it in R.by_kind(svc)
                  if it["x0"] <= h["x1"] and it["x1"] >= h["x0"]
                  and it["y0"] <= h["y1"] and it["y1"] >= h["y0"]]
        below = [it["z1"] for it in inplan if it["z1"] <= dz + 1e-6]
        above = [it["z0"] for it in inplan if it["z0"] > dz + 1e-6]
        if below:
            rec["services"].append(dict(service=svc, top_z=round(max(below), 1),
                                        clear_mm=round(dz - max(below), 1),
                                        reference="run top surface"))
        elif above:
            rec["above"].append(dict(service=svc, bottom_z=round(min(above), 1),
                                     distance_mm=round(min(above) - dz, 1)))
        else:
            rec["above"].append(dict(service=svc, bottom_z=None,
                                     distance_mm=None, note="no run in head footprint"))
    head_clear.append(rec)

pdu_chw = []
for p in R.by_kind("PDU"):
    best = None
    for it in R.by_kind("CHW"):
        dx = max(it["x0"] - p["x1"], p["x0"] - it["x1"], 0.0)
        dy = max(it["y0"] - p["y1"], p["y0"] - it["y1"], 0.0)
        dz = max(it["z0"] - p["z1"], p["z1"] - it["z1"], 0.0)
        d3 = math.sqrt(dx * dx + dy * dy + dz * dz)
        if best is None or d3 < best[0]:
            best = (d3, dz, it)
    pdu_chw.append(dict(pdu=p["meta"]["name"],
                        vertical_mm=round(best[1], 1),            # to insulation
                        vertical_to_pipe_mm=round(best[1] + CHW_INSUL, 1),
                        dist3d_mm=round(best[0], 1),
                        dist3d_to_pipe_mm=round(best[0] + CHW_INSUL, 1),
                        reference="insulation outer surface",
                        chw_element=best[2]["meta"].get("name", "CHW segment")))

# CRAH top -> nearest CHW pipe (vertical and planar components)
crah_chw = []
for c in R.by_kind("CRAH"):
    best = None
    for it in R.by_kind("CHW"):
        dx = max(it["x0"] - c["x1"], c["x0"] - it["x1"], 0.0)
        dy = max(it["y0"] - c["y1"], c["y0"] - it["y1"], 0.0)
        dz = max(it["z0"] - c["z1"], 0.0)            # pipe above the CRAH top
        d3 = math.sqrt(dx * dx + dy * dy + dz * dz)
        if best is None or d3 < best[0]:
            best = (d3, dz, math.hypot(dx, dy), it)
    crah_chw.append(dict(crah=c["meta"]["name"],
                         top_z=round(c["z1"], 1),
                         chw_bottom_z=round(best[3]["z0"], 1),
                         vertical_mm=round(best[1], 1),          # to insulation
                         vertical_to_pipe_mm=round(best[1] + CHW_INSUL, 1),
                         plan_mm=round(best[2], 1),
                         dist3d_mm=round(best[0], 1),
                         reference="insulation outer surface"))

tray_bus = dict(vertical_gap_mm=round(TRAY_BOT - BUS_TOP, 1),

                rule_mm=TRAY_BUS_SEP, ok=(TRAY_BOT - BUS_TOP) >= TRAY_BUS_SEP)

# =============================================================================
# 7.  IFC4 AUTHORING
# =============================================================================
def _default_out():
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in ("/filesystem/dc_model__hall_seed000_d000__mep_routing/output",
                 here):
        if os.path.isdir(cand):
            return os.path.join(cand, "model.ifc")
    return os.path.join(here, "model.ifc")


OUT = sys.argv[1] if len(sys.argv) > 1 else _default_out()
try:
    os.makedirs(os.path.dirname(os.path.abspath(OUT)) or ".", exist_ok=True)
except Exception:
    pass

f = ifcopenshell.file(schema="IFC4")


_GUID_USED = set()


def guid(key):
    """Deterministic, collision-free IFC GlobalId."""
    k = str(key)
    n = 0
    while k in _GUID_USED:
        n += 1
        k = "%s~%d" % (key, n)
    _GUID_USED.add(k)
    h = hashlib.md5(("dcm-hall-seed000-%s" % k).encode("utf-8")).hexdigest()
    return ifcopenshell.guid.compress(h.upper())


# --- helpers --------------------------------------------------------------
E = f.createIfcCartesianPoint
D = f.createIfcDirection


def pt(x, y, z=0.0):
    return E([float(x), float(y), float(z)])


def pt2(x, y):
    return E([float(x), float(y)])


def place(x_mm, y_mm, z_mm, rot_deg=0.0, rel=None):
    """Object placement whose translation is in METRES (contract) and whose
    rotation is about the footprint centre."""
    a = math.radians(rot_deg)
    ax = f.createIfcAxis2Placement3D(
        pt(x_mm / 1000.0, y_mm / 1000.0, z_mm / 1000.0),
        D([0.0, 0.0, 1.0]), D([math.cos(a), math.sin(a), 0.0]))
    return f.createIfcLocalPlacement(rel, ax)


# units: millimetre project length unit
u_len = f.createIfcSIUnit(None, "LENGTHUNIT", "MILLI", "METRE")
u_ang = f.createIfcSIUnit(None, "PLANEANGLEUNIT", None, "RADIAN")
u_area = f.createIfcSIUnit(None, "AREAUNIT", None, "SQUARE_METRE")
u_vol = f.createIfcSIUnit(None, "VOLUMEUNIT", None, "CUBIC_METRE")
origin = f.createIfcAxis2Placement3D(pt(0, 0, 0), D([0.0, 0.0, 1.0]), D([1.0, 0.0, 0.0]))
ctx3 = f.createIfcGeometricRepresentationContext(
    None, "Model", 3, 1.0e-5, origin, D([0.0, 1.0]))
ctx_body = f.createIfcGeometricRepresentationSubContext(
    "Body", "Model", None, None, None, None, ctx3, None, "MODEL_VIEW", None)
ctx_axis = f.createIfcGeometricRepresentationSubContext(
    "Axis", "Model", None, None, None, None, ctx3, None, "GRAPH_VIEW", None)

owner = f.createIfcPersonAndOrganization(
    f.createIfcPerson(None, "MEP Coordinator", None, None, None, None, None, None),
    f.createIfcOrganization(None, "dc_model", None, None, None), None)
app = f.createIfcApplication(
    f.createIfcOrganization(None, "dc_model", None, None, None),
    "1.0", "dc_model IFC4 author", "dc_model")
_now = 1700000000
oh = f.createIfcOwnerHistory(
    owner, app, None, "NOCHANGE", None, None, None, _now)


def solid(w, d, h, diameter=None):
    """2D-profile extrusion in millimetres."""
    p2 = f.createIfcAxis2Placement2D(pt2(0.0, 0.0))
    if diameter:
        prof = f.createIfcCircleProfileDef("AREA", None, p2, diameter / 2.0)
    else:
        prof = f.createIfcRectangleProfileDef("AREA", None, p2, w, d)
    return f.createIfcExtrudedAreaSolid(prof, f.createIfcAxis2Placement3D(
        pt(0, 0, 0), D([0.0, 0.0, 1.0]), D([1.0, 0.0, 0.0])), D([0.0, 0.0, 1.0]), h)


def tube_solid(p0, p1, w, h, diameter=None):
    """Solid for a routed run: the profile lies in the plane normal to the
    run axis and is extruded along it (2D profile + extrusion only)."""
    dx, dy, dz = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    if abs(dz) > 1e-9:
        axis, ref, xdim, ydim = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), w, w
    elif abs(dx) > 1e-9:
        axis, ref, xdim, ydim = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), w, h
    else:
        axis, ref, xdim, ydim = (0.0, 1.0, 0.0), (1.0, 0.0, 0.0), w, h
    pos = f.createIfcAxis2Placement3D(pt(0, 0, 0), D(list(axis)), D(list(ref)))
    if diameter:
        prof = f.createIfcCircleProfileDef("AREA", None,
                                           f.createIfcAxis2Placement2D(pt2(0.0, 0.0)),
                                           diameter / 2.0)
    else:
        prof = f.createIfcRectangleProfileDef("AREA", None,
                                              f.createIfcAxis2Placement2D(pt2(0.0, 0.0)),
                                              xdim, ydim)
    return f.createIfcExtrudedAreaSolid(prof, pos, D([0.0, 0.0, 1.0]), L)


def make_tube(cls, key, name, p0, p1, w, h, obj_type, predef, diameter=None, tag=None):
    shp = f.createIfcShapeRepresentation(ctx_body, "Body", "SweptSolid",
                                         (tube_solid(p0, p1, w, h, diameter),))
    prod = f.createIfcProductDefinitionShape(None, None, (shp,))
    pl = place(p0[0], p0[1], p0[2])
    return _create(cls, key, name, pl, prod, obj_type, predef, tag)


def make_product(cls, key, name, place3d, w, d, h, obj_type=None, predef=None,
                 diameter=None, tag=None):
    shp = f.createIfcShapeRepresentation(ctx_body, "Body", "SweptSolid",
                                         (solid(w, d, h, diameter),))
    prod = f.createIfcProductDefinitionShape(None, None, (shp,))
    return _create(cls, key, name, place3d, prod, obj_type, predef, tag)


def _create(cls, key, name, place3d, prod, obj_type=None, predef=None, tag=None):
    kw = dict(GlobalId=guid(key), OwnerHistory=oh, Name=name,
              Description=None, ObjectType=obj_type, ObjectPlacement=place3d,
              Representation=prod)
    if cls == "IfcWall":
        e = f.createIfcWall(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcSlab":
        e = f.createIfcSlab(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcColumn":
        e = f.createIfcColumn(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcFurniture":
        e = f.createIfcFurniture(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcUnitaryEquipment":
        e = f.createIfcUnitaryEquipment(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcElectricDistributionBoard":
        e = f.createIfcElectricDistributionBoard(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcFireSuppressionTerminal":
        e = f.createIfcFireSuppressionTerminal(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcCableCarrierSegment":
        e = f.createIfcCableCarrierSegment(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcCableSegment":
        e = f.createIfcCableSegment(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcPipeSegment":
        e = f.createIfcPipeSegment(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcBuildingElementProxy":
        e = f.createIfcBuildingElementProxy(kw["GlobalId"], oh, name, None, obj_type, place3d, prod, tag, predef)
    elif cls == "IfcSpace":
        e = f.createIfcSpace(kw["GlobalId"], oh, name, None, obj_type, place3d, prod,
                             tag, "ELEMENT", predef, 0.0)
    else:
        raise ValueError(cls)
    return e


PSETS = {}


def pset(element, name, props):
    """props: list of (Name, value, kind)  kind in {'text','real','int','bool'}"""
    hps = []
    for (pn, pv, pk) in props:
        if pk == "real":
            val = f.createIfcReal(float(pv))
        elif pk == "int":
            val = f.createIfcInteger(int(pv))
        elif pk == "bool":
            val = f.createIfcBoolean(bool(pv))
        else:
            val = f.createIfcLabel(str(pv))
        hps.append(f.createIfcPropertySingleValue(pn, None, val, None))
    ps = f.createIfcPropertySet(guid("%s|%s" % (element.GlobalId, name)), oh,
                                name, None, hps)
    f.createIfcRelDefinesByProperties(guid("%s|%s|rel" % (element.GlobalId, name)),
                                      oh, None, None, (element,), ps)
    PSETS.setdefault(name, 0)
    PSETS[name] += 1
    return ps


# --- spatial structure ----------------------------------------------------
ua = f.createIfcUnitAssignment((u_len, u_ang, u_area, u_vol))
proj = f.createIfcProject(guid("project"), oh, "Data hall seed000 d000", None,
                          None, None, None, (ctx3,), ua)
site = f.createIfcSite(guid("site"), oh, "Site", None, None,
                       place(0, 0, 0), None, None, "ELEMENT", None, None, None, None)
bldg = f.createIfcBuilding(guid("building"), oh, "Building", None, None,
                           place(0, 0, 0), None, None, "ELEMENT", None, None, None)
storey = f.createIfcBuildingStorey(guid("storey"), oh, "Data hall", None, None,
                                   place(0, 0, 0), None, None, "ELEMENT", 0.0)
f.createIfcRelAggregates(guid("agg1"), oh, None, None, proj, (site,))
f.createIfcRelAggregates(guid("agg2"), oh, None, None, site, (bldg,))
f.createIfcRelAggregates(guid("agg3"), oh, None, None, bldg, (storey,))

space = f.createIfcSpace(guid("space"), oh, "Data hall space", None, "Space",
                         place(HALL_X / 2, HALL_Y / 2, 0), None, None, "ELEMENT",
                         "SPACE", 0.0)
f.createIfcRelAggregates(guid("agg4"), oh, None, None, storey, (space,))

contained = []
elems = {}

# --- shell / structure ----------------------------------------------------
for it in R.by_kind("WALL"):
    m = it["meta"]
    w = it["x1"] - it["x0"]; d = it["y1"] - it["y0"]
    e = make_product("IfcWall", "wall|%s" % m["name"], m["name"],
                     place((it["x0"] + it["x1"]) / 2, (it["y0"] + it["y1"]) / 2, it["z0"]),
                     w, d, it["z1"] - it["z0"], "Wall", "SOLIDWALL")
    pset(e, "Pset_DCM_Element", [("ElementRole", "Envelope", "text"),
                                 ("Thickness", w if w < d else d, "real"),
                                 ("Height", it["z1"] - it["z0"], "real"),
                                 ("Sheet", "A-101/A-301", "text")])
    contained.append(e)
    elems[m["name"]] = e

for it in R.by_kind("SLAB_STRUCT", "ACCESS_FLOOR", "ROOF"):
    m = it["meta"]
    w = it["x1"] - it["x0"]; d = it["y1"] - it["y0"]
    e = make_product("IfcSlab", "slab|%s" % m["name"], m["name"],
                     place((it["x0"] + it["x1"]) / 2, (it["y0"] + it["y1"]) / 2, it["z0"]),
                     w, d, it["z1"] - it["z0"], "Slab", m["PredefinedType"])
    props = [("ElementRole", "Slab", "text"),
             ("PredefinedType", m["PredefinedType"], "text"),
             ("Thickness", it["z1"] - it["z0"], "real"),
             ("TopElevation", it["z1"], "real"),
             ("Sheet", "A-301", "text")]
    if "Tile" in m:
        props += [("TileSize", m["Tile"], "real"),
                  ("TilePitch", m["Tile"], "real"),
                  ("GridOrigin", "0,0", "text"),
                  ("PlenumDepth", abs(SLAB_TOP), "real"),
                  ("PlenumTopBelowFFL", abs(SLAB_TOP), "real"),
                  ("PlenumBottom", 0.0, "real"),
                  ("ClearVoidDepth", abs(SLAB_TOP) - abs(it["z0"]), "real")]
    pset(e, "Pset_DCM_Element", props)
    contained.append(e)
    elems[m["name"]] = e


# --- racks ---------------------------------------------------------------
for it in R.by_kind("RACK"):
    m = it["meta"]
    cx = (it["x0"] + it["x1"]) / 2.0
    cy = (it["y0"] + it["y1"]) / 2.0
    e = make_product("IfcFurniture", "rack|%s" % m["name"], m["name"],
                     place(cx, cy, it["z0"], it["rot"]), RACK_W, RACK_D, RACK_H,
                     "Rack", "USERDEFINED")
    pset(e, "Pset_DCM_Rack", [
        ("ElementRole", "IT equipment", "text"),
        ("Row", m["row"], "int"), ("Position", m["idx"], "int"),
        ("Width", RACK_W, "real"), ("Depth", RACK_D, "real"),
        ("Height", RACK_H, "real"),
        ("Facing", {0: "North", 90: "East", 180: "South", 270: "West"}[int(m["facing"])], "text"),
        ("FacingAngle", m["facing"], "real"),
        ("FootprintCentreX", cx, "real"), ("FootprintCentreY", cy, "real"),
        ("TileWidth", TILE, "real"),
        ("RackType", "CAB-42U", "text"),
        ("HeatLoad_kW", 8.0, "real"), ("Weight_kg", 950.0, "real"),
        ("Sheet", "A-101/A-601", "text")])
    contained.append(e)

# --- CRAHs ----------------------------------------------------------------
_CRAH_CLR = {r["crah"]: r for r in crah_chw}


def _crah_chw_props(name):
    r = _CRAH_CLR.get(name)
    return r["vertical_mm"] if r else -1.0


for it in R.by_kind("CRAH"):
    m = it["meta"]
    e = make_product("IfcUnitaryEquipment", "crah|%s" % m["name"], m["name"],
                     place((it["x0"] + it["x1"]) / 2, (it["y0"] + it["y1"]) / 2, it["z0"]),
                     it["x1"] - it["x0"], it["y1"] - it["y0"], it["z1"] - it["z0"],
                     "CRAH", "AIRHANDLER")
    pset(e, "Pset_DCM_CRAH", [("ElementRole", "Cooling", "text"),
                              ("Width", it["x1"] - it["x0"], "real"),
                              ("Depth", it["y1"] - it["y0"], "real"),
                              ("Height", it["z1"] - it["z0"], "real"),
                              ("TopElevation", it["z1"], "real"),
                              ("CoolingCapacity_kW", 350.0, "real"),
                              ("Airflow_lps", 9000.0, "real"),
                              ("Connection", "CHW top connection", "text"),
                              ("CHWClearance_mm", _crah_chw_props(m["name"]), "real"),
                              ("CHWClearanceToPipe_mm", _crah_chw_props(m["name"]) + CHW_INSUL,
                               "real"),
                              ("CHWClearanceReference", "Insulation outer surface", "text"),
                              ("Sheet", "A-101/M-101", "text")])
    contained.append(e)
    elems[m["name"]] = e

# --- PDUs -----------------------------------------------------------------
_PDU_CLR = {r["pdu"]: r for r in pdu_chw}


def _pdu_chw_props(name):
    r = _PDU_CLR.get(name)
    if not r:
        return []
    return [("NearestCHW_Vertical_mm", r["vertical_mm"], "real"),
            ("NearestCHW_VerticalToPipe_mm", r["vertical_to_pipe_mm"], "real"),
            ("NearestCHW_Distance3D_mm", r["dist3d_mm"], "real"),
            ("NearestCHW_ClearanceReference", "Insulation outer surface", "text"),
            ("PDUTopElevation", 2000.0, "real")]


for it in R.by_kind("PDU"):
    m = it["meta"]
    e = make_product("IfcElectricDistributionBoard", "pdu|%s" % m["name"], m["name"],
                     place((it["x0"] + it["x1"]) / 2, (it["y0"] + it["y1"]) / 2, it["z0"]),
                     it["x1"] - it["x0"], it["y1"] - it["y0"], it["z1"] - it["z0"],
                     "PDU", "SWITCHBOARD")
    pset(e, "Pset_DCM_PDU", [("ElementRole", "Power", "text"),
                             ("Width", it["x1"] - it["x0"], "real"),
                             ("Depth", it["y1"] - it["y0"], "real"),
                             ("Height", it["z1"] - it["z0"], "real"),
                             ("TopElevation", it["z1"], "real"),
                             ("Rating_kVA", 600.0, "real"),
                             ("DedicatedSpaceAbove", PDU_DEDICATED, "real"),
                             ("DedicatedSpaceZFrom", it["z1"], "real"),
                             ("DedicatedSpaceZTo", it["z1"] + PDU_DEDICATED, "real"),
                             ("Sheet", "E-101", "text")] + _pdu_chw_props(m["name"]))
    contained.append(e)
    elems[m["name"]] = e

# --- containment (end panels + cold-aisle decks) --------------------------
for it in R.by_kind("CONTAINMENT", "CONTAINMENT_ROOF"):
    m = it["meta"]
    obj = "Containment Roof" if it["kind"] == "CONTAINMENT_ROOF" else "Containment"
    e = make_product("IfcBuildingElementProxy", "cont|%s|%s" % (m["name"], it["x0"]), m["name"],
                     place((it["x0"] + it["x1"]) / 2, (it["y0"] + it["y1"]) / 2, it["z0"]),
                     it["x1"] - it["x0"], it["y1"] - it["y0"], it["z1"] - it["z0"],
                     obj, "ELEMENT")
    heads_here = [h["meta"]["name"] for h in R.by_kind("SPRINKLER")
                  if it["x0"] <= h["meta"]["x"] <= it["x1"]
                  and it["y0"] <= h["meta"]["y"] <= it["y1"]
                  and h["z1"] <= it["z0"] + 1e-6]
    pset(e, "Pset_DCM_Element", [("ElementRole", "Containment", "text"),
                                 ("Type", m["Type"], "text"),
                                 ("IsRoof", it["kind"] == "CONTAINMENT_ROOF", "bool"),
                                 ("Height", it["z1"] - it["z0"], "real"),
                                 ("Elevation", it["z0"], "real"),
                                 ("HeadsBeneath", len(heads_here), "int"),
                                 ("Sheet", "A-101/F-101", "text")])
    contained.append(e)
    elems[m["name"] + str(int(it["x0"]))] = e

# --- sprinkler heads ------------------------------------------------------
_HEAD_CLR = {_h["id"]: _h for _h in head_clear}


def _head_clear_props(name):
    """Clearances for one head.  A property is only written when it has a
    physical meaning: `ClearanceTo<svc>_mm` when the run passes BELOW the
    deflector, otherwise `NearestRun_<svc>_Above_mm` / `_Relation`."""
    c = _HEAD_CLR.get(name, {})
    below = {s["service"]: s for s in c.get("services", [])}
    above = {s["service"]: s for s in c.get("above", [])}
    out = []
    for svc in ("TRAY", "BUSWAY", "CHW"):
        if svc in below:
            out.append(("ClearanceTo%s_mm" % svc, below[svc]["clear_mm"], "real"))
            out.append(("TopOf%s_mm" % svc, below[svc]["top_z"], "real"))
            out.append(("%sRelation" % svc, "below", "text"))
        else:
            a = above.get(svc, {})
            if a.get("distance_mm") is not None:
                out.append(("NearestRun_%s_Above_mm" % svc, a["distance_mm"], "real"))
                out.append(("%sRelation" % svc, "above", "text"))
            else:
                out.append(("%sRelation" % svc, "none", "text"))
    out.append(("NFPADeflectorBand", NFPA_OBSTRUCTION, "real"))
    out.append(("ClearanceReference", "deflector to run top surface", "text"))
    return out


for it in R.by_kind("SPRINKLER"):
    m = it["meta"]
    e = make_product("IfcFireSuppressionTerminal", "spr|%s" % m["name"], m["name"],
                     place((it["x0"] + it["x1"]) / 2, (it["y0"] + it["y1"]) / 2, it["z0"]),
                     it["x1"] - it["x0"], it["y1"] - it["y0"], it["z1"] - it["z0"],
                     "Sprinkler", "SPRINKLER")
    pset(e, "Pset_DCM_Sprinkler", [
        ("ElementRole", "Fire suppression", "text"),
        ("DeflectorElevation", m["deflector"], "real"),
        ("DeflectorZ", m["deflector"], "real"),
        ("KFactor", 80.0, "real"),
        ("Spacing", HEAD_PITCH, "real"),
        ("Coverage_m2", HEAD_PITCH * HEAD_PITCH / 1e6, "real"),
        ("RequiredClearBelow", DEFLECTOR_CLEAR, "real"),
        ("X", m["x"], "real"), ("Y", m["y"], "real"),
        ("HeadRole", m.get("role", "Ceiling"), "text"),
        ("UnderContainmentRoof", m.get("role") == "Containment roof", "bool"),
        ("Sheet", "F-101", "text")] + _head_clear_props(m["name"]))
    contained.append(e)

# --- routed services ------------------------------------------------------
SERVICE_CLASS = {
    "TRAY": ("IfcCableCarrierSegment", "CABLETRAYSEGMENT", "Telecom cable tray"),
    "BUSWAY": ("IfcCableSegment", "BUSBARSEGMENT", "Power busway"),
    "CHW": ("IfcPipeSegment", "RIGIDSEGMENT", "Chilled water (insulated)"),
}
def _serves_text(service, p0, p1):
    """Which rack rows / CRAHs a segment serves (diagnostic narrative)."""
    out = []
    if p0[2] != p1[2]:
        return ""
    ymid = (p0[1] + p1[1]) / 2.0
    xmid = (p0[0] + p1[0]) / 2.0
    for i, cy in enumerate(ROW_Y):
        if abs(abs(ymid) - abs(cy)) <= 2500.0:
            out.append("Row %d" % (i + 1))
    return ", ".join(out)


counters = {"TRAY": 0, "BUSWAY": 0, "CHW": 0}
service_elems = {"TRAY": [], "BUSWAY": [], "CHW": []}
entry_elems = {}
for (service, p0, p1, w, h, meta) in segs:
    cls, predef, svc_name = SERVICE_CLASS[service]
    counters[service] += 1
    n = counters[service]
    L = math.dist(p0, p1)
    if meta.get("drop"):
        obj = "%s Drop" % service
    elif meta.get("entry"):
        obj = "%s Termination" % service
    else:
        obj = svc_name
    # CHW solids are modelled at the insulated outside diameter so that the
    # 25.4 mm insulation is part of the clash envelope.
    e = make_tube(cls, "%s|%d" % (service, n), "%s-%02d" % (svc_name, n),
                  p0, p1, w, h, obj, predef,
                  diameter=(w if meta.get("diameter") else None))
    svc_elev = (p0[2] + p1[2]) / 2.0 if p0[2] != p1[2] else p0[2]
    pset(e, "Pset_DCM_RouteSegment", [
        ("ServiceType", service, "text"),
        ("Service", svc_name, "text"),
        ("Tier", meta.get("tier", 0), "int"),
        ("Elevation", svc_elev, "real"),
        ("Elevation_mm", svc_elev, "real"),
        ("Level", svc_elev, "real"),
        ("Length", L, "real"),
        ("Width", w, "real"),
        ("Height", h, "real"),
        ("Diameter", meta.get("diameter", w), "real"),
        ("PipeDiameter", meta.get("diameter", w), "real"),
        ("InsulationThickness", CHW_INSUL if service == "CHW" else 0.0, "real"),
        ("OuterDiameter", w, "real"),
        ("ModelledDiameter", w, "real"),
        ("ModelledSolid", ("Insulated envelope" if service == "CHW" else "cable tray / busway"),
         "text"),
        ("ClearanceReference", ("Insulation outer surface" if service == "CHW"
                                else "element outer surface"), "text"),
        ("PipeSurfaceOffset", CHW_INSUL if service == "CHW" else 0.0, "real"),
        ("InsulationIncluded", True if service == "CHW" else False, "bool"),
        ("TrayBuswaySeparation", TRAY_BUS_SEP if service in ("TRAY", "BUSWAY") else 0.0, "real"),
        ("StartPoint", "%.1f,%.1f,%.1f" % p0, "text"),
        ("EndPoint", "%.1f,%.1f,%.1f" % p1, "text"),
        ("Entry", bool(meta.get("entry")), "bool"),
        ("Serves", meta.get("serves", _serves_text(service, p0, p1)), "text"),
        ("Sheet", "M-101/E-101/A-602", "text")])
    if meta.get("drop"):
        pset(e, "Pset_DCM_Drop", [("ObjectType", "Drop", "text"),
                                  ("Service", service, "text"),
                                  ("Serves", meta.get("serves", _serves_text(service, p0, p1)), "text"),
                                  ("LocationX", p0[0], "real"),
                                  ("LocationY", p0[1], "real"),
                                  ("FromElevation", max(p0[2], p1[2]), "real"),
                                  ("ToElevation", min(p0[2], p1[2]), "real")])
    contained.append(e)
    service_elems[service].append(e)
    if meta.get("entry"):
        entry_elems[service] = e

# --- supports / hangers ---------------------------------------------------
for it in R.by_kind("SUPPORT"):
    m = it["meta"]
    cls = "IfcBuildingElementProxy"
    e = make_product(cls, "sup|%s|%d" % (m["service"], it["x0"]),
                     m["name"],
                     place((it["x0"] + it["x1"]) / 2, (it["y0"] + it["y1"]) / 2, it["z0"]),
                     it["x1"] - it["x0"], it["y1"] - it["y0"], it["z1"] - it["z0"],
                     m["Type"], "ELEMENT")
    pset(e, "Pset_DCM_Support", [("ObjectType", m["Type"], "text"),
                                 ("Service", m["service"], "text"),
                                 ("MaxSpacing", SUPPORT_PITCH, "real"),
                                 ("SupportSpacing", round(m.get("gap", SUPPORT_PITCH), 1), "real"),
                                 ("Run", m.get("run", ""), "text"),
                                 ("RodLength", it["z1"] - it["z0"], "real"),
                                 ("Sheet", "A-602", "text")])
    contained.append(e)

# --- containment relationships -------------------------------------------
# --- explicit connectivity between touching segments of the same service --
def _ab(it):
    return (it["x0"], it["x1"], it["y0"], it["y1"], it["z0"], it["z1"])


def _touch(a, b, eps=0.5):
    ax0, ax1, ay0, ay1, az0, az1 = _ab(a)
    bx0, bx1, by0, by1, bz0, bz1 = _ab(b)
    dx = max(ax0 - bx1, bx0 - ax1, 0.0)
    dy = max(ay0 - by1, by0 - ay1, 0.0)
    dz = max(az0 - bz1, bz0 - az1, 0.0)
    return dx <= eps and dy <= eps and dz <= eps


n_conn = 0
for svc in ("TRAY", "BUSWAY", "CHW"):
    lst = [it for it in R.by_kind(svc)]
    els = service_elems[svc]
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            if _touch(lst[i], lst[j]):
                f.createIfcRelConnectsElements(
                    guid("conn|%s|%d|%d" % (svc, i, j)), oh, None, None, None,
                    els[i], els[j])
                n_conn += 1

# --- system level psets (attached to each service entry segment) ---------
for svc in ("TRAY", "BUSWAY", "CHW"):
    cls, predef, svc_name = SERVICE_CLASS[svc]
    entry_elem = entry_elems[svc]
    pset(entry_elem, "Pset_DCM_System", [
        ("ServiceType", svc, "text"),
        ("SystemName", svc_name, "text"),
        ("EntryPoint", "%.1f,%.1f,%.1f" % (0.0, ENTRY_Y,
                                           {"TRAY": TRAY_MZ,
                                            "BUSWAY": BUS_MZ,
                                            "CHW": CHW_Z}[svc]), "text"),
        ("EntryX", 0.0, "real"), ("EntryY", ENTRY_Y, "real"),
        ("EntryZ", {"TRAY": TRAY_MZ, "BUSWAY": BUS_MZ, "CHW": CHW_Z}[svc], "real"),
        ("Tier", {"TRAY": 1, "BUSWAY": 2, "CHW": 3}[svc], "int"),
        ("TotalLength", lengths[svc]["total"], "real"),
        ("OverheadLength", lengths[svc]["overhead"], "real"),
        ("UnderfloorLength", lengths[svc]["underfloor"], "real"),
        ("Segments", len(service_elems[svc]), "int"),
        ("RowsServed", len(ROW_Y), "int"),
        ("CRAHsServed", len(crahs) if svc == "CHW" else 0, "int"),
        ("Connected", True, "bool"),
        ("Sheet", "M-101/E-101", "text")])

f.createIfcRelContainedInSpatialStructure(guid("contain"), oh, None, None,
                                          tuple(contained), storey)

# --- validate -------------------------------------------------------------
try:
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(f, logger, express_rules=True)
    nbad = len([l for l in logger.statements if l.get("type") == "error"])
    if nbad:
        print("VALIDATION: %d express-rule complaints" % nbad)
        for l in logger.statements[:10]:
            print("  -", l.get("message"))
except Exception as exc:                      # pragma: no cover
    print("VALIDATION raised:", exc)

try:
    f.header.file_name.time_stamp = "2024-01-01T00:00:00"
    f.header.file_name.name = "hall_seed000_d000.ifc"
    f.header.file_name.author = ("dc_model",)
    f.header.file_name.organization = ("dc_model",)
    f.header.file_description.description = ("ViewDefinition [CoordinationView]",)
except Exception:
    pass
f.write(OUT)

# =============================================================================
# 8.  RECONCILIATION SIDE FILE
# =============================================================================
rec = {
    "project": "dc_model hall_seed000_d000",
    "units": "millimetre (IFC project length unit MILLI.METRE)",
    "sheets": {
        "A-101": "equipment plan - room 27.0 x 21.0 m, 6 rack rows, 600 mm floor tiles, columns, containment",
        "A-301": "building section - FFL, access-floor plenum, clear height 4800, roof slab, deflector level",
        "A-601": "cabinet schedule - 128 cabinets, 600 x 1200 footprint, 2000 high",
        "A-602": "containment/pathway/construction - 300 mm tray/busway separation, 2600 headroom, 25.4 mm insulation, hanger spacing",
        "M-101": "chilled water - DN168 + 25.4 mm insulation, west-wall entry, CRAH connections",
        "E-101": "busway & PDU - west-wall entry, 1800 mm dedicated space above each PDU",
        "F-101": "sprinkler grid - 9 x 7 heads at 3000 mm, deflector 4400, 460 mm clear below deflector",
    },
    "notes": [
        {"sheet": "A-101", "text": "hall interior 355 x 276 px = 27 000 x 21 000 mm (13.15 px/m)",
         "value": [27000, 21000], "unit": "mm", "applied": "HALL_X / HALL_Y"},
        {"sheet": "A-101", "text": "access floor tile pitch 7.87 px", "value": 600, "unit": "mm",
         "applied": "TILE; rack x positions snapped to the 600 mm grid"},
        {"sheet": "A-101", "text": "six rack rows, band centres y px 249.5/289.5/320.5/359.5/391.5/431.5",
         "value": ROW_Y, "unit": "mm", "applied": "ROW_Y"},
        {"sheet": "A-601", "text": "128 cabinets", "value": 128, "unit": "count",
         "applied": "ROW_COUNT = 22,21,22,21,21,21"},
        {"sheet": "A-601", "text": "cabinet 600 wide x 1200 deep x 2000 high", "value": [600, 1200, 2000],
         "unit": "mm", "applied": "RACK_W / RACK_D / RACK_H"},
        {"sheet": "A-301", "text": "clear height FFL to structural soffit", "value": SOFFIT_Z,
         "unit": "mm", "applied": "SOFFIT_Z; roof slab 300 thick"},
        {"sheet": "A-301", "text": "under-floor plenum depth (structural slab top to FFL)",
         "value": abs(SLAB_TOP), "unit": "mm",
         "applied": "SLAB_TOP = -700 (700 mm deep; usable but not used by the routes)"},
        {"sheet": "A-101", "text": "rack bands px x 488..729 = 1 900..20 230 mm, block break px 590..613 = 9 660..11 410 mm",
         "value": [ROW_CELLS[0], ROW_X_END, BLOCK_GAP_X0, BLOCK_GAP_X1], "unit": "mm",
         "applied": "ROW_CELLS: block A 1 800..9 600, break 9 600..11 400, block B 11 400..20 400"},
        {"sheet": "A-101", "text": "south-wall CRAH fan symbols / unit boxes at px x 471..487, 583..600, "
                                    "695..712, 785..801 (16-18 px = 1.2-1.4 m wide)",
         "value": CRAH_X_S, "unit": "mm",
         "applied": "CRAH_X_S; CRAH_W = 1400 x CRAH_D = 1200 x CRAH_H = 2600"},
        {"sheet": "A-101", "text": "north-wall unit symbols at px x 750..765 and 779..794 "
                                    "(the only unit-sized symbols on that wall)",
         "value": CRAH_X_N, "unit": "mm",
         "applied": "CRAH_X_N; total 6 perimeter CRAHs, all reached by CHW"},
        {"sheet": "E-101", "text": "PDU tag/box at each row at px x 753..763", "value": [PDU_X, PDU_X + PDU_W],
         "unit": "mm", "applied": "PDU_X = 22 050, PDU_W = 760"},
        {"sheet": "A-101", "text": "cold aisles enclosed (dashed perimeter around each row pair)",
         "value": [RACK_H, RACK_H + CONTAINMENT_DECK_T], "unit": "mm",
         "applied": "3 cold-aisle decks at rack-top level + 6 end panels + heads beneath each deck"},
        {"sheet": "F-101", "text": "sprinkler grid 9 x 7 at 3000 mm, centred", "value": 3000,
         "unit": "mm", "applied": "HEAD_PITCH / HEAD_NX / HEAD_NY (63 heads)"},
        {"sheet": "F-101", "text": "deflector elevation", "value": DEFLECTOR_Z, "unit": "mm",
         "applied": "DEFLECTOR_Z"},
        {"sheet": "F-101", "text": "460 mm clear below every deflector", "value": DEFLECTOR_CLEAR,
         "unit": "mm", "applied": "checked for every run under a head; least favourable 600"},
        {"sheet": "A-602", "text": "300 mm minimum tray / busway separation", "value": TRAY_BUS_SEP,
         "unit": "mm", "applied": "TRAY_BOT 3700 - BUS_TOP 3400 = 300"},
        {"sheet": "A-602", "text": "2600 mm minimum headroom", "value": HEADROOM_MIN, "unit": "mm",
         "applied": "lowest service soffit = CHW bottom 2640.6"},
        {"sheet": "M-101", "text": "CHW pipe DN168 with 25.4 mm insulation", "value": [CHW_OD, CHW_INSUL],
         "unit": "mm", "applied": "single IfcPipeSegment solid at the insulated outside diameter "
                                  "218.8 mm (conservative clash envelope); all reported CHW clearances are "
                                  "to the insulation outer surface, the bare pipe surface is 25.4 mm further"},
        {"sheet": "M-101", "text": "CHW entry in the west wall", "value": [0, ENTRY_Y], "unit": "mm",
         "applied": "CHW entry segment at y = %d" % ENTRY_Y},
        {"sheet": "E-101", "text": "busway entry in the west wall", "value": [0, ENTRY_Y], "unit": "mm",
         "applied": "BUSWAY entry segment at y = %d" % ENTRY_Y},
        {"sheet": "A-101/A-301", "text": "no interior column symbols in plan or section",
         "value": 0, "unit": "count",
         "applied": "clear-span hall: no interior columns modelled (roof carried by the walls)"},
        {"sheet": "E-101", "text": "1800 mm dedicated space above each PDU", "value": PDU_DEDICATED,
         "unit": "mm", "applied": "CHW exclusion boxes checked, no violation"},
        {"sheet": "A-602", "text": "max hanger spacing", "value": SUPPORT_PITCH, "unit": "mm",
         "applied": "every tray/busway support line laid out at <= 1500 mm pitch (rods offset "
                    "sideways rather than omitted where they meet a sprinkler head)"},
        {"sheet": "F-101", "text": "heads required beneath containment roofs",
         "value": len(AISLE_HEADS), "unit": "count",
         "applied": "in-aisle heads at %d mm pitch under the three cold-aisle decks, "
                    "deflector at %.0f mm" % (AISLE_HEAD_PITCH, AISLE_HEAD_Z)},
    ],
    "assumptions": [
        "The seven sheets carry no machine-readable data channel; all positions were measured "
        "from the raster geometry (wall faces, tile grid, row bands, sprinkler symbols) and are "
        "baked into the script as literals.",
        "Rack row centres were measured on A-101 and snapped to the 600 mm access-floor grid; "
        "A-601 states 128 cabinets, distributed 22/21/22/21/21/21 over the six rows.",
        "Columns are placed on the structural grid implied by the A-101 rack-row gaps "
        "(X = 6.9 / 14.4 / 20.1 m, Y = 7.14 / 12.55 m), full clear height.",
        "CRAH units are the A-101 perimeter units: four on the south wall at px x 471..487 / "
        "583..600 / 695..712 / 785..801 (centres 1 445 / 10 040 / 18 710 / 25 100 mm) and two "
        "on the north wall at px x 750..765 / 779..794 (centres 22 400 / 24 606 mm), each "
        "1 400 x 1 200 x 2 600.",
        "No interior columns are modelled: A-101 shows no column symbols between the rack rows "
        "and A-301 shows no interior vertical element between FFL and the soffit, i.e. the roof "
        "is clear-span on the perimeter walls.  The invented 3 x 2 grid of the previous revision "
        "has been removed.",
        "The six PDUs sit at the drawn E-101/A-101 tag position x = 22 050..22 820 mm, one per "
        "rack row at the row centre-line.",
        "Vertical tiers were derived from the A-301 section (soffit 4800, deflector 4400) and "
        "the A-602 code notes (2600 headroom, 300 tray/busway, 460 under the deflector).",
        "Tray 300x100, busway 200x150 and CHW DN168 + 25.4 mm insulation are the values used "
        "throughout; the CHW clash envelope is modelled at the insulated outside diameter.",
    ],
    "clearances": {
        "sprinkler_head": head_clear,
        "pdu_chw": pdu_chw,
        "crah_chw": crah_chw,
        "tray_busway": tray_bus,
    },
    "lengths": lengths,
    "elevations": {
        "tray": {"bottom": TRAY_BOT, "top": TRAY_TOP, "tier": 1},
        "busway": {"bottom": BUS_BOT, "top": BUS_TOP, "tier": 2},
        "chw": {"centre": CHW_Z, "envelope_bottom": CHW_Z - CHW_OUT / 2,
                "envelope_top": CHW_Z + CHW_OUT / 2, "tier": 3},
        "deflector": DEFLECTOR_Z,
        "deflector_containment_roofs": AISLE_HEAD_Z,
        "containment_deck": [RACK_H, RACK_H + CONTAINMENT_DECK_T],
        "soffit": SOFFIT_Z,
        "ffl": 0.0,
    },
    "rows": row_report,
    "crahs": crah_report,
    "totals": {"L_total_mm": L_total, "elements": len(R.items),
               "supports": n_sup, "racks": len(R.by_kind("RACK")),
               "sprinklers": len(R.by_kind("SPRINKLER")),
               "segments": len(segs)},
    "psets_written": sorted(PSETS),
}
out_json = os.path.join(os.path.dirname(os.path.abspath(OUT)), "reconciliation.json")
with open(out_json, "w") as fh:
    json.dump(rec, fh, indent=2)

print("wrote %s" % OUT)
print("wrote %s" % out_json)
print("elements: %d   racks: %d   heads: %d   segments: %d   L_total: %.1f m"
      % (len(R.items), len(R.by_kind("RACK")), len(R.by_kind("SPRINKLER")),
         len(segs), L_total / 1000.0))
for svc, v in lengths.items():
    print("  %-7s overhead %8.1f m  underfloor %6.1f m" % (svc, v["overhead"] / 1000.0,
                                                           v["underfloor"] / 1000.0))
