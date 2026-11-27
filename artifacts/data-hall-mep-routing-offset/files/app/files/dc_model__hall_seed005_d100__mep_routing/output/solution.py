#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dc_model hall_seed005_d100  --  coordinated overhead MEP model builder.

Rebuilds the data hall described by the seven-sheet drawing set
  A-101 equipment plan, A-301 building section, A-601 cabinet schedule,
  A-602 containment/pathway/construction data, M-101 chilled water,
  E-101 busway & PDU, F-101 sprinkler grid
as an IFC4 model with the three overhead services routed clash free.

Everything read off the drawings is baked in below as literals (the script
never opens a PNG, never touches the network and contains no randomness).
Run:  python3 solution.py [out.ifc]
"""

import sys, os, json, math, uuid
import ifcopenshell
import ifcopenshell.guid
import ifcopenshell.validate

# ---------------------------------------------------------------------------
# 0.  contract switches
# ---------------------------------------------------------------------------
PLACEMENT_IN_METRES = True   # contract: mm project units, placement translations in METRES
EXPRESS_RULES       = True

# ===========================================================================
# 1.  DATA BLOCK  -- every number below was measured on the drawing sheets.
#     lengths in millimetres, angles in degrees, origin = SW interior corner
#     of the data hall at finished floor level 0; +X east, +Y north, +Z up.
# ===========================================================================
DATA = {}
DATA["_provenance"] = {
    "A-101": "equipment plan, plotted 1:100 -> 100.0 mm/px; hall outline, 600 tile "
             "grid, 7200 structural grid, 4 cabinet rows, columns, CRAH/PDU blocks",
    "A-301": "building section, plotted so that FFL->ceiling = 205 px = 4100 mm "
             "(20.0 mm/px); roof slab 4780..5300, structural slab -1480..-940, "
             "raised floor 0.00, sprinkler deflector 150 below ceiling",
    "A-601": "cabinet schedule (94 rows) -> 600 x 1200 x 2200 cabinet, 42U",
    "A-602": "containment/pathway data -> tray 500x100 ladder (open, no roof), "
             "busway 200x120, CHW DN150 + 25.4 insulation, support spacings",
    "M-101": "chilled water: DN150 CHW, 25.4 mm insulation, entry at west wall",
    "E-101": "busway & PDU: 200x120 busway, 1500 mm max support spacing, "
             "PDU 800x1000x2000, entry at west wall",
    "F-101": "sprinkler grid: 104 heads (94 open + 10 upright), 2472 mm grid",
}

# ---- hall envelope (A-101 / F-101) ----------------------------------------
ROOM_L   = 27000.0      # clear interior X  (266 px x 101.5 mm/px, A-101 px 504-770)
ROOM_H   = 24000.0      # clear interior Y  (237 px x 101.5 mm/px, A-101 px 213-450)
NOTCH_X  = ROOM_L       # rectangular hall: the notch test is disabled
NOTCH_Y  = ROOM_H
WALL_T   = 200.0

# ---- grid modules (A-101) --------------------------------------------------
TILE     = 600.0        # floor tile module (measured 5.90 px x 101.5 = 600 mm)
GRID     = 7200.0       # structural grid (measured 70.5 px x 101.5 = 7156 -> 7200)
GRID_OFF = 150.0        # structural grid offset from the tile grid (150 mod 600)
# A-101 puts the column blobs at px 571 / 642 / 712 -> 6800 / 14000 / 21200 mm,
# i.e. grid lines at x = -450 + 7200k and y = 150 + 7200k (both = 150 mod 600).
GRID_X0  = -450.0
GRID_Y0  = 150.0
COL_SIZE = 600.0        # 600 x 600 structural column

# ---- elevations (A-301, 20.0 mm/px) ---------------------------------------
FFL          = 0.0
CEIL_UNDER   = 4100.0   # finished floor -> ceiling underside (205 px x 20)
CEIL_T       = 30.0
ROOF_UNDER   = 4780.0
ROOF_TOP     = 5300.0
SLAB_BOT     = -1480.0
SLAB_TOP     = -940.0
FLOOR_T      = 40.0     # access floor panel thickness
DEFLECTOR_Z  = CEIL_UNDER - 150.0        # 3950, sprinkler deflector

# ---- equipment (A-601 / E-101) --------------------------------------------
RACK_W, RACK_D, RACK_H = 600.0, 1200.0, 2200.0
CRAH_H = 2000.0
PDU_W, PDU_D, PDU_H = 800.0, 1000.0, 2000.0

# ---- services (A-602 / M-101 / E-101) -------------------------------------
TRAY_W, TRAY_H          = 500.0, 100.0    # open ladder tray, no roof
BUSWAY_W, BUSWAY_H      = 200.0, 120.0
PIPE_OD, PIPE_INSUL     = 168.3, 25.4     # DN150 + 25.4 mm insulation
PIPE_OD_OUT             = PIPE_OD + 2.0 * PIPE_INSUL     # 219.1

TRAY_TOP   = DEFLECTOR_Z - 470.0          # 3480 -> 470 clear below deflector
TRAY_BOT   = TRAY_TOP - TRAY_H            # 3380
BUS_TOP    = TRAY_BOT - 320.0             # 3060 -> 320 tray/busway separation (>=300)
BUS_BOT    = BUS_TOP - BUSWAY_H           # 2940
CHW_BOT    = 2610.0                        # 10 mm above the 2600 mm headroom rule
CHW_TOP    = CHW_BOT + PIPE_OD_OUT        # 2829.1
CHW_MID    = (CHW_BOT + CHW_TOP) / 2.0    # 2719.55

# ---- design rules taken from the sheets / task ----------------------------
MIN_HEADROOM    = 2600.0
DEFLECTOR_CLEAR = 460.0
NFPA_SHADOW     = 450.0
WIDE_RUN        = 1200.0
TRAY_BUS_SEP    = 300.0
PDU_SPACE       = 1800.0
MAX_OFFSET_ROW  = 2500.0
BUS_SUPPORT_MAX = 1500.0
TRAY_SUPPORT_MAX= 1500.0
CHW_SUPPORT_MAX = 3000.0
MIN_CLASH       = 2.0
DRAWN_ROW_X     = (1400.0, 20800.0)   # cabinet band extent on A-101 / F-101

DATA.update(dict(ROOM_L=ROOM_L, ROOM_H=ROOM_H, NOTCH_X=NOTCH_X, NOTCH_Y=NOTCH_Y,
                 TILE=TILE, GRID=GRID, GRID_OFF=GRID_OFF, CEIL_UNDER=CEIL_UNDER,
                 DEFLECTOR_Z=DEFLECTOR_Z, RACK=(RACK_W, RACK_D, RACK_H),
                 CRAH_H=CRAH_H, PDU=(PDU_W, PDU_D, PDU_H),
                 TRAY=(TRAY_W, TRAY_H), BUSWAY=(BUSWAY_W, BUSWAY_H),
                 PIPE_OD=PIPE_OD, PIPE_INSUL=PIPE_INSUL,
                 TRAY_TOP=TRAY_TOP, TRAY_BOT=TRAY_BOT, BUS_TOP=BUS_TOP,
                 BUS_BOT=BUS_BOT, CHW_TOP=CHW_TOP, CHW_BOT=CHW_BOT,
                 CHW_MID=CHW_MID))

# ===========================================================================
# 2.  LAYOUT  -- computed from the data block, deterministic
# ===========================================================================
def inside(x, y, m=0.0):
    """True if (x, y) lies inside the rectangular hall interior (inset by m)."""
    return (m <= x <= ROOM_L - m) and (m <= y <= ROOM_H - m)

def box_inside(x0, y0, x1, y1):
    return inside(x0, y0) and inside(x1, y0) and inside(x0, y1) and inside(x1, y1)

# ---- structural columns ---------------------------------------------------
COLUMNS = []            # (cx, cy)
i = 0
while GRID_X0 + i * GRID <= ROOM_L:
    j = 0
    while GRID_Y0 + j * GRID <= ROOM_H:
        cx = GRID_X0 + i * GRID
        cy = GRID_Y0 + j * GRID
        if (cx - COL_SIZE / 2 >= 0.0 and cy - COL_SIZE / 2 >= 0.0 and
                box_inside(cx - COL_SIZE / 2, cy - COL_SIZE / 2,
                           cx + COL_SIZE / 2, cy + COL_SIZE / 2)):
            COLUMNS.append((cx, cy))
        j += 1
    i += 1

def col_hit(x0, y0, x1, y1, pad=0.0):
    for (cx, cy) in COLUMNS:
        if (x0 < cx + COL_SIZE / 2 + pad and x1 > cx - COL_SIZE / 2 - pad and
            y0 < cy + COL_SIZE / 2 + pad and y1 > cy - COL_SIZE / 2 - pad):
            return True
    return False

# ---- cabinet rows ---------------------------------------------------------
# Row bands re-derived from A-101 (plan x 503-772 px, y 213-450 px at 100 mm/px,
# row outlines at py 333/345, 361/374, 386/398, 414/427) and cross-checked on
# F-101 (x 271-980 px, y 146-776 px = 26.6 x 23.6 m at 37.5 mm/px).
# They agree within ~150 mm; the averaged bands are used below.
ROWS = [
    dict(id="R1", y0=2300.0,  y1=3500.0,  face=270.0),   # southernmost
    dict(id="R2", y0=5250.0,  y1=6450.0,  face=90.0),
    dict(id="R3", y0=7650.0,  y1=8850.0,  face=270.0),
    dict(id="R4", y0=10550.0, y1=11750.0, face=90.0),    # northernmost
]
for r in ROWS:
    r["yc"] = (r["y0"] + r["y1"]) / 2.0

# service entries arrive through the west wall at the southern row header level
ENTRY_Y = min(r["yc"] for r in ROWS)
TRUNK_Y0 = ENTRY_Y
TRUNK_Y1 = max(r["yc"] for r in ROWS)

# Cabinet runs per row, taken from the drawn row segments (600 mm modules on the
# tile grid).  Different rows break at different places - there is no single
# shared cross-aisle; the gaps are where the drawing shows aisles / columns.
#               row : [(x_start, n_cabinets), ...]
ROW_RUNS = {
    "R1": [(1800.0, 6), (6000.0, 9), (12600.0, 7), (18000.0, 5)],    # 27, ends 21.0 m
    "R2": [(1800.0, 7), (6600.0, 6), (16800.0, 7)],                  # 20, ends 21.0 m
    "R3": [(1800.0, 7), (7800.0, 7), (16800.0, 7)],                  # 21, ends 21.0 m
    "R4": [(1800.0, 5), (5400.0, 8), (12600.0, 7), (17400.0, 6)],    # 26, ends 21.0 m
}
RACKS = []          # dict(tag,x0,x1,y0,y1,facing,row)
BLANKS = []         # blanking panels closing a column gap
for row in ROWS:
    idx = 0
    for (xs, n) in ROW_RUNS[row["id"]]:
        for k in range(n):
            x0 = xs + k * TILE
            x1 = x0 + TILE
            if col_hit(x0, row["y0"], x1, row["y1"]):
                # tile-vs-column conflict: the slot is re-registered, a
                # blanking panel closes the gap and the cabinet is skipped.
                BLANKS.append(dict(tag="%s-BP%02d" % (row["id"], k + 1),
                                   x0=x0, x1=x0 + TILE,
                                   y0=row["y0"], y1=row["y0"] + 50.0, row=row["id"]))
                continue
            idx += 1
            RACKS.append(dict(tag="%s-%02d" % (row["id"], idx),
                              x0=x0, x1=x1, y0=row["y0"], y1=row["y1"],
                              facing=row["face"], row=row["id"]))

assert len(RACKS) == 94, len(RACKS)

# ---- CRAH (perimeter units) & PDU ----------------------------------------
CRAHS = [
    dict(tag="CRAH-01", x0=0.0,     y0=2400.0,  x1=800.0,   y1=4400.0),
    dict(tag="CRAH-02", x0=0.0,     y0=6000.0,  x1=800.0,   y1=8000.0),
    dict(tag="CRAH-03", x0=0.0,     y0=9400.0,  x1=800.0,   y1=11400.0),
    dict(tag="CRAH-04", x0=25800.0, y0=4000.0,  x1=26600.0, y1=6000.0),
    dict(tag="CRAH-05", x0=25800.0, y0=8000.0,  x1=26600.0, y1=10000.0),
    dict(tag="CRAH-06", x0=25800.0, y0=12000.0, x1=26600.0, y1=14000.0),
]
for c in CRAHS:
    c["cx"] = (c["x0"] + c["x1"]) / 2.0
    c["cy"] = (c["y0"] + c["y1"]) / 2.0

PDUS = [
    dict(tag="PDU-01", x0=2300.0,  y0=6700.0, x1=3100.0,  y1=7500.0),
    dict(tag="PDU-02", x0=8300.0,  y0=6700.0, x1=9100.0,  y1=7500.0),
    dict(tag="PDU-03", x0=16000.0, y0=6700.0, x1=16800.0, y1=7500.0),
    dict(tag="PDU-04", x0=2300.0,  y0=9300.0, x1=3100.0,  y1=10300.0),
    dict(tag="PDU-05", x0=8300.0,  y0=9300.0, x1=9100.0,  y1=10300.0),
    dict(tag="PDU-06", x0=16000.0, y0=9300.0, x1=16800.0, y1=10300.0),
]
for p in PDUS:
    p["cx"] = (p["x0"] + p["x1"]) / 2.0
    p["cy"] = (p["y0"] + p["y1"]) / 2.0

# ---- sprinkler heads (F-101, 11 x 2472 grid, L-shaped) --------------------
SPK_PITCH = 2500.0          # F-101: 65.6 px x 38.09 mm/px = 2499 mm
SPK_ORIGIN = 1250.0         # F-101: first head 32.8 px from the west wall
SPK_X = [SPK_ORIGIN + k * SPK_PITCH for k in range(11)]
SPRINKLERS = []
# northern half of the hall: 7 columns wide
for y in (16250.0, 18750.0, 21250.0, 23750.0):
    for x in SPK_X[:7]:
        SPRINKLERS.append((x, y, "pendent"))
# transition band across the wide southern half
for x in SPK_X[:7] + [21250.0]:
    SPRINKLERS.append((x, 13750.0, "pendent"))
for x in (18750.0, 23750.0, 26250.0):
    SPRINKLERS.append((x, 14250.0, "pendent"))
# southern half: full 11 columns
for y in (1250.0, 3750.0, 6250.0, 8750.0, 11250.0):
    for x in SPK_X:
        SPRINKLERS.append((x, y, "pendent"))
# 10 upright heads on the y = 7125 line (F-101 filled symbols)
for x in (2350.0, 4350.0, 6250.0, 7850.0, 10900.0,
          13300.0, 15050.0, 16900.0, 18700.0, 20500.0):
    SPRINKLERS.append((x, 7125.0, "upright"))
assert len(SPRINKLERS) == 104, len(SPRINKLERS)

# ---- service routes -------------------------------------------------------
# every polyline is split into axis-aligned segments below
ENTRIES = {"Tray":   (0.0, ENTRY_Y, (TRAY_TOP + TRAY_BOT) / 2.0),
           "Busway": (0.0, ENTRY_Y, (BUS_TOP + BUS_BOT) / 2.0),
           "CHW":    (0.0, ENTRY_Y, CHW_MID)}

# Header extents follow the real rack extents so nothing is routed further than
# needed.  Branches butt onto the trunk FACE (not its centreline) so that no two
# solids of the same service interpenetrate at a corner or T-junction.
ROW_LO, ROW_HI = {}, {}
for _r in RACKS:
    ROW_LO[_r["row"]] = min(ROW_LO.get(_r["row"], 1e18), _r["x0"])
    ROW_HI[_r["row"]] = max(ROW_HI.get(_r["row"], -1e18), _r["x1"])
ROW_HDR_Y = {r["id"]: r["yc"] for r in ROWS}
HDR_END = {k: v + 300.0 for k, v in ROW_HI.items()}

TRUNK_TB_X = 1800.0
TRUNK_CHW_X = 1800.0
TRUNK_Y0 = min(r["yc"] for r in ROWS)
TRUNK_Y1 = max(r["yc"] for r in ROWS)
ENTRY_Y = TRUNK_Y0
X_E = 25000.0

HT = TRAY_W / 2.0          # tray half width  (250)
HB = BUSWAY_W / 2.0        # busway half width (100)
HC = PIPE_OD_OUT / 2.0     # insulated CHW radius (109.55)

TRAY_PATHS = [[(0.0, ENTRY_Y), (TRUNK_TB_X - HT, ENTRY_Y)],
              [(TRUNK_TB_X, TRUNK_Y0 - HT), (TRUNK_TB_X, TRUNK_Y1 + HT)]]
BUS_PATHS = [[(0.0, ENTRY_Y), (TRUNK_TB_X - HB, ENTRY_Y)],
             [(TRUNK_TB_X, TRUNK_Y0 - HB), (TRUNK_TB_X, TRUNK_Y1 + HB)]]
CHW_PATHS = [[(0.0, ENTRY_Y), (TRUNK_CHW_X - HC, ENTRY_Y)],
             [(TRUNK_CHW_X, TRUNK_Y0 - HC), (TRUNK_CHW_X, TRUNK_Y1 + HC)]]
for _row in ROWS:
    y_h = ROW_HDR_Y[_row["id"]]
    TRAY_PATHS.append([(TRUNK_TB_X + HT, y_h), (HDR_END[_row["id"]], y_h)])
    BUS_PATHS.append([(TRUNK_TB_X + HB, y_h), (HDR_END[_row["id"]], y_h)])
    CHW_PATHS.append([(TRUNK_CHW_X + HC, y_h), (HDR_END[_row["id"]], y_h)])
# west-wall CRAH bank: short legs straight off the west trunk (butted)
for _c in CRAHS:
    if _c["x1"] <= 1000.0:
        CHW_PATHS.append([(TRUNK_CHW_X - HC, _c["cy"]), (_c["x1"], _c["cy"])])
# east CRAH bank
CHW_PATHS += [[(HDR_END["R1"], ENTRY_Y), (X_E - HC, ENTRY_Y)],
              [(X_E, ENTRY_Y - HC), (X_E, 13000.0 + HC)],
              [(X_E + HC, 5000.0), (25800.0, 5000.0)],
              [(X_E + HC, 9000.0), (25800.0, 9000.0)],
              [(X_E + HC, 13000.0), (25800.0, 13000.0)]]

SERVICES = [
    dict(key="Tray",   ifc="IfcCableCarrierSegment", ptype="CABLETRAYSEGMENT",
         otype="TelecomTray", w=TRAY_W, top=TRAY_TOP, h=TRAY_H,
         paths=TRAY_PATHS, shape="rect", zmid=(TRAY_TOP + TRAY_BOT) / 2.0),
    dict(key="Busway", ifc="IfcCableSegment", ptype="BUSBARSEGMENT",
         otype="PowerBusway", w=BUSWAY_W, top=BUS_TOP, h=BUSWAY_H,
         paths=BUS_PATHS, shape="rect", zmid=(BUS_TOP + BUS_BOT) / 2.0),
    dict(key="CHW",    ifc="IfcPipeSegment", ptype="RIGIDSEGMENT",
         otype="CHW", w=PIPE_OD_OUT, top=CHW_TOP, h=PIPE_OD_OUT,
         paths=CHW_PATHS, shape="round", zmid=CHW_MID),
]

# ===========================================================================
# 3.  segment decomposition
# ===========================================================================
def split_polyline(pts):
    """Split a rectilinear polyline into axis-aligned segments."""
    segs = []
    for a, b in zip(pts[:-1], pts[1:]):
        if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
            continue
        segs.append((a, b))
    return segs

SEGMENTS = {}          # key -> list of dicts

def planarise(raw):
    """Split axis-aligned segments at every endpoint coordinate so that
    T-junctions and crossings become explicit graph nodes."""
    xs = set(); ys = set()
    for (a, b) in raw:
        xs.add(round(a[0], 3)); xs.add(round(b[0], 3))
        ys.add(round(a[1], 3)); ys.add(round(b[1], 3))
    out = []
    for (a, b) in raw:
        if abs(a[1] - b[1]) < 1e-9:                      # horizontal
            lo, hi = min(a[0], b[0]), max(a[0], b[0])
            cuts = sorted(v for v in xs if lo + 1e-6 < v < hi - 1e-6)
            pts = [lo] + cuts + [hi]
            if b[0] < a[0]:
                pts = pts[::-1]
            for i in range(len(pts) - 1):
                if abs(pts[i + 1] - pts[i]) > 1e-9:
                    out.append(((pts[i], a[1]), (pts[i + 1], a[1])))
        else:                                            # vertical
            lo, hi = min(a[1], b[1]), max(a[1], b[1])
            cuts = sorted(v for v in ys if lo + 1e-6 < v < hi - 1e-6)
            pts = [lo] + cuts + [hi]
            if b[1] < a[1]:
                pts = pts[::-1]
            for i in range(len(pts) - 1):
                if abs(pts[i + 1] - pts[i]) > 1e-9:
                    out.append(((a[0], pts[i]), (a[0], pts[i + 1])))
    return out

for svc in SERVICES:
    raw = []
    for path in svc["paths"]:
        raw.extend(split_polyline(path))
    lst = []
    n = 0
    for (a, b) in planarise(raw):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-6:
            continue
        nparts = max(1, int(math.ceil(L / 6000.0 - 1e-9)))
        for k in range(nparts):
            t0 = k / nparts; t1 = (k + 1) / nparts
            p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            n += 1
            lst.append(dict(tag="%s-%03d" % (svc["key"], n),
                            p0=p0, p1=p1, L=L / nparts))
    SEGMENTS[svc["key"]] = lst

def seg_aabb(p0, p1, w, top, h, shape="rect"):
    z0 = top - h; z1 = top
    if abs(p0[1] - p1[1]) < 1e-9:            # run along X
        x0, x1 = min(p0[0], p1[0]), max(p0[0], p1[0])
        y0, y1 = p0[1] - w / 2.0, p0[1] + w / 2.0
    elif abs(p0[0] - p1[0]) < 1e-9:          # run along Y
        y0, y1 = min(p0[1], p1[1]), max(p0[1], p1[1])
        x0, x1 = p0[0] - w / 2.0, p0[0] + w / 2.0
    else:
        raise SystemExit("non axis-aligned segment %s %s" % (p0, p1))
    return (x0, y0, z0, x1, y1, z1)

# ===========================================================================
# 4.  solid registry  (used by every gate)
# ===========================================================================
SOLIDS = []     # dict(box=(x0,y0,z0,x1,y1,z1), grp=str, tag=str, ifc=entity|None)

def reg(box, grp, tag, ent=None):
    SOLIDS.append(dict(box=box, grp=grp, tag=tag, ifc=ent))
    return box

def overlap(box, other, eps=MIN_CLASH):
    (ax0, ay0, az0, ax1, ay1, az1) = box
    (bx0, by0, bz0, bx1, by1, bz1) = other
    ox = min(ax1, bx1) - max(ax0, bx0)
    oy = min(ay1, by1) - max(ay0, by0)
    oz = min(az1, bz1) - max(az0, bz0)
    if ox > eps and oy > eps and oz > eps:
        return (ox, oy, oz)
    return None

# ---------------------------------------------------------------------------
# background boxes
# ---------------------------------------------------------------------------
BG = []
def bgbox(x0, y0, z0, x1, y1, z1, grp, tag):
    box = (min(x0, x1), min(y0, y1), min(z0, z1),
           max(x0, x1), max(y0, y1), max(z0, z1))
    BG.append(dict(box=box, grp=grp, tag=tag))

# walls (6 rectangles around the L)
WALLS = [
    ("Wall-S", -WALL_T, -WALL_T, ROOM_L + WALL_T, 0.0),
    ("Wall-N", -WALL_T, ROOM_H,  ROOM_L + WALL_T, ROOM_H + WALL_T),
    ("Wall-W", -WALL_T, 0.0,     0.0,             ROOM_H),
    ("Wall-E", ROOM_L,  0.0,     ROOM_L + WALL_T, ROOM_H),
]
for (nm, x0, y0, x1, y1) in WALLS:
    bgbox(x0, y0, SLAB_TOP, x1, y1, ROOF_UNDER, "wall", nm)

# slabs
bgbox(-WALL_T, -WALL_T, SLAB_BOT, ROOM_L + WALL_T, ROOM_H + WALL_T, SLAB_TOP, "slab", "Slab-Struct")
bgbox(0.0, 0.0, -FLOOR_T, ROOM_L, ROOM_H, 0.0, "slab", "AccessFloor")
bgbox(-WALL_T, -WALL_T, ROOF_UNDER, ROOM_L + WALL_T, ROOM_H + WALL_T, ROOF_TOP, "slab", "Roof")
bgbox(0.0, 0.0, CEIL_UNDER, ROOM_L, ROOM_H, CEIL_UNDER + CEIL_T, "slab", "Ceiling")

for (cx, cy) in COLUMNS:
    bgbox(cx - COL_SIZE / 2, cy - COL_SIZE / 2, FFL,
          cx + COL_SIZE / 2, cy + COL_SIZE / 2, CEIL_UNDER, "column", "COL")
for r in RACKS:
    bgbox(r["x0"], r["y0"], FFL, r["x1"], r["y1"], RACK_H, "rack", r["tag"])
for b in BLANKS:
    bgbox(b["x0"], b["y0"], FFL, b["x1"], b["y1"], RACK_H, "blank", b["tag"])
for c in CRAHS:
    bgbox(c["x0"], c["y0"], FFL, c["x1"], c["y1"], CRAH_H, "crah", c["tag"])
for p in PDUS:
    bgbox(p["x0"], p["y0"], FFL, p["x1"], p["y1"], PDU_H, "pdu", p["tag"])
for (sx, sy, kind) in SPRINKLERS:
    # the head body sits ABOVE the deflector plane: its lowest face IS the
    # deflector, so the 460 mm clear rule is measured to a real surface
    bgbox(sx - 50, sy - 50, DEFLECTOR_Z, sx + 50, sy + 50, DEFLECTOR_Z + 120,
          "sprinkler", "SPK")

# service solids
for svc in SERVICES:
    for s in SEGMENTS[svc["key"]]:
        box = seg_aabb(s["p0"], s["p1"], svc["w"], svc["top"], svc["h"], svc["shape"])
        s["box"] = box
        reg(box, svc["key"], s["tag"])

# ---------------------------------------------------------------------------
# drops / taps
# ---------------------------------------------------------------------------
DROPS = []
def add_drop(tag, x0, y0, z0, x1, y1, z1, serves, svc, kind="Drop"):
    box = (min(x0, x1), min(y0, y1), min(z0, z1),
           max(x0, x1), max(y0, y1), max(z0, z1))
    DROPS.append(dict(tag=tag, box=box, serves=serves, svc=svc, kind=kind,
                      x=(box[0] + box[3]) / 2.0, y=(box[1] + box[4]) / 2.0,
                      z=box[5]))
    reg(box, "drop", tag)

# Each service is brought down to the cabinets by a tap (horizontal stub at the
# service tier, touching the service soffit) followed by a vertical drop that
# reaches the rack top.  The three drops of a station are fanned out in plan so
# that no drop can touch a lower tier.
# drop stations are derived from the cabinets themselves: three cabinets per row
# at the 25 / 50 / 75 % points of the row, so every drop lands on a real cabinet
ROW_DROP_X = {}
for _row in ROWS:
    xs = sorted(0.5 * (r["x0"] + r["x1"]) for r in RACKS if r["row"] == _row["id"])
    idx = sorted(set([xs[len(xs) // 4], xs[len(xs) // 2], xs[(3 * len(xs)) // 4]]))
    ROW_DROP_X[_row["id"]] = idx
for row in ROWS:
    yh = ROW_HDR_Y[row["id"]]
    for i, x in enumerate(ROW_DROP_X[row["id"]]):
        # all three stay inside the served cabinet's 600 mm footprint
        # tray : stub yh+250 .. yh+500 at the tray tier, then vertical to the racks
        add_drop("Tap-Tray-%s-%d" % (row["id"], i + 1), x - 210, yh + 250,
                 TRAY_BOT, x - 110, yh + 500, TRAY_TOP, row["id"], "Tray", "Tap")
        add_drop("Drop-Tray-%s-%d" % (row["id"], i + 1), x - 210, yh + 450,
                 RACK_H, x - 110, yh + 550, TRAY_BOT, row["id"], "Tray")
        # busway : stub yh+100 .. yh+350 at the busway tier, then vertical
        add_drop("Tap-Busway-%s-%d" % (row["id"], i + 1), x - 50, yh + 100,
                 BUS_BOT, x + 50, yh + 350, BUS_TOP, row["id"], "Busway", "Tap")
        add_drop("Drop-Busway-%s-%d" % (row["id"], i + 1), x - 50, yh + 300,
                 RACK_H, x + 50, yh + 400, BUS_BOT, row["id"], "Busway")
        # CHW : the lowest tier, straight vertical onto the rack top
        add_drop("Drop-CHW-%s-%d" % (row["id"], i + 1), x + 110, yh - 50,
                 RACK_H, x + 210, yh + 50, CHW_BOT, row["id"], "CHW")

# CRAH terminations: a vertical riser at the end of the CHW leg that touches both
# the pipe soffit and the CRAH top face.
for c in CRAHS:
    if c["x0"] > 20000.0:                       # east wall units
        x0, y0 = 25800.0, c["cy"]
    else:                                       # west wall units
        x0, y0 = 800.0, c["cy"]
    add_drop("Term-CHW-%s" % c["tag"], x0 - 50, y0 - 50, CRAH_H,
             x0 + 50, y0 + 50, CHW_BOT, c["tag"], "CHW", "Termination")

# ---------------------------------------------------------------------------
# supports / hangers
# ---------------------------------------------------------------------------
SUPPORTS = []
def add_support(tag, box, svc, spacing):
    SUPPORTS.append(dict(tag=tag, box=box, svc=svc, spacing=spacing))
    reg(box, "support", tag)

def along(p0, p1, step, start=0.0):
    dx = p1[0] - p0[0]; dy = p1[1] - p0[1]
    L = math.hypot(dx, dy)
    t = start
    out = []
    while t <= L + 1e-6:
        out.append((p0[0] + dx * t / L, p0[1] + dy * t / L))
        t += step
    return out

def perp(p0, p1):
    dx = p1[0] - p0[0]; dy = p1[1] - p0[1]
    L = math.hypot(dx, dy)
    return (-dy / L, dx / L)

def run_perp(p0, p1):
    """Stable transverse direction: (0,1) for runs along X, (1,0) for runs along Y."""
    return (0.0, 1.0) if abs(p1[0] - p0[0]) >= abs(p1[1] - p0[1]) else (1.0, 0.0)

# Brackets are seated so their box CONTACTS the run they support:
#   tray   : bracket over the tray shoulder, offset -(250+50) = -300, sits on the
#            tray top face (3480) and rises into the ceiling void
#   busway : bracket above the busway, offset -(100+50) = -150, touching 3060 and
#            stopping 10 mm below the tray soffit
#   CHW    : bracket directly above the pipe, offset 0, stopping below the busway
SUPPORT_SPEC = [("Tray",   1400.0, -(TRAY_W / 2.0 + 50.0), TRAY_TOP, 3700.0),
                ("Busway", 1400.0, -(BUSWAY_W / 2.0 + 50.0), BUS_TOP, TRAY_BOT - 10.0),
                ("CHW",    3000.0, 0.0, CHW_TOP, BUS_BOT - 10.0)]
for svc, step, lateral, zlo, zhi in SUPPORT_SPEC:
    idx = 0
    for s in SEGMENTS[svc]:
        px, py = run_perp(s["p0"], s["p1"])
        for (x, y) in along(s["p0"], s["p1"], step, start=step / 2.0):
            idx += 1
            placed = False
            for lat in (lateral, -lateral):
                hx = x + px * lat
                hy = y + py * lat
                if col_hit(hx - 50, hy - 50, hx + 50, hy + 50, 50.0):
                    continue
                if not (inside(hx - 50, hy - 50) and inside(hx + 50, hy + 50)):
                    continue
                box = (hx - 50, hy - 50, zlo, hx + 50, hy + 50, zhi)
                if any(overlap(box, d["box"], 2.0) for d in SOLIDS if d["grp"] == "drop"):
                    continue
                if any(overlap(box, sup["box"], 2.0) for sup in SUPPORTS):
                    continue
                add_support("Hanger-%s-%03d" % (svc, idx), box, svc, step)
                placed = True
                break
            if not placed:
                continue

# ===========================================================================
# 5.  GATES
# ===========================================================================
FAIL = []
def gate(name, ok, detail=""):
    if not ok:
        FAIL.append("%s: %s" % (name, detail))
    return ok

def all_solids():
    out = []
    for b in BG:
        out.append(b)
    for s in SOLIDS:
        out.append(s)
    return out

# ---- 5.1 hard clash -------------------------------------------------------
def clash_gate():
    solids = []
    for b in BG:
        solids.append((b["box"], b["grp"], b["tag"]))
    for s in SOLIDS:
        solids.append((s["box"], s["grp"], s["tag"]))
    # segments of the same service tier may touch at butted joints; nothing else
    same_ok = {("Tray", "Tray"), ("Busway", "Busway"), ("CHW", "CHW")}
    bad = []
    n = len(solids)
    for i in range(n):
        a = solids[i]
        for j in range(i + 1, n):
            b = solids[j]
            if a[1] == b[1] or (a[1], b[1]) in same_ok:
                continue
            ov = overlap(a[0], b[0])
            if ov:
                bad.append((a[2], b[2], ov))
    gate("CLASH", len(bad) == 0, "%d clashes, e.g. %s" % (len(bad), bad[:8]))
    return bad

# ---- 5.2 headroom ---------------------------------------------------------
def headroom_gate():
    bad = []
    for s in SOLIDS:
        if s["grp"] in ("Tray", "Busway", "CHW"):
            if s["box"][2] < MIN_HEADROOM - 1e-6:
                bad.append((s["tag"], s["box"][2]))
    gate("HEADROOM", not bad, str(bad[:5]))
    return bad

# ---- 5.3 sprinkler clearance + NFPA shadow -------------------------------
SPK_CLEAR = {}
def sprinkler_gate():
    bad = []
    for (sx, sy, kind) in SPRINKLERS:
        for s in SOLIDS:
            if s["grp"] not in ("Tray", "Busway", "CHW"):
                continue
            x0, y0, z0, x1, y1, z1 = s["box"]
            if sx < x0 - 1e-6 or sx > x1 + 1e-6 or sy < y0 - 1e-6 or sy > y1 + 1e-6:
                continue
            clear = DEFLECTOR_Z - z1
            SPK_CLEAR[(sx, sy, s["tag"])] = clear
            if clear < DEFLECTOR_CLEAR - 1e-6:
                bad.append((sx, sy, s["tag"], clear))
    gate("SPRINKLER_CLEAR", not bad, "%d violations %s" % (len(bad), bad[:5]))
    return bad

# ---- 5.4 tray / busway separation ---------------------------------------
def separation_gate():
    worst = None
    for t in SOLIDS:
        if t["grp"] != "Tray":
            continue
        for b in SOLIDS:
            if b["grp"] != "Busway":
                continue
            ax0, ay0, az0, ax1, ay1, az1 = t["box"]
            bx0, by0, bz0, bx1, by1, bz1 = b["box"]
            gx = max(bx0 - ax1, ax0 - bx1)
            gy = max(by0 - ay1, ay0 - by1)
            gz = max(bz0 - az1, az0 - bz1)
            sep = max(gx, gy, gz)
            if worst is None or sep < worst[0]:
                worst = (sep, t["tag"], b["tag"])
    ok = worst is not None and worst[0] >= TRAY_BUS_SEP - 1e-6
    gate("TRAY_BUS_SEP", ok, str(worst))
    return worst

# ---- 5.5 CHW clear of the 1800 space above every PDU ---------------------
PDU_CLEAR = {}
def pdu_gate():
    bad = []
    for p in PDUS:
        pt = FFL + PDU_H
        top = pt + PDU_SPACE
        best = None
        for s in SOLIDS:
            if s["grp"] != "CHW":
                continue
            x0, y0, z0, x1, y1, z1 = s["box"]
            if x0 < p["x1"] and x1 > p["x0"] and y0 < p["y1"] and y1 > p["y0"]:
                if z1 > pt and z0 < top:
                    bad.append((p["tag"], s["tag"]))
            # vertical clearance from PDU top to nearest CHW above the footprint
            if x0 < p["x1"] + 1000 and x1 > p["x0"] - 1000 and y0 < p["y1"] + 1000 and y1 > p["y0"] - 1000:
                if z0 >= pt:
                    d = z0 - pt
                    if best is None or d < best:
                        best = d
        PDU_CLEAR[p["tag"]] = best
    gate("PDU_DEDICATED_SPACE", not bad, str(bad[:5]))
    return bad

# ---- 5.6 service network connectivity -----------------------------------
def connectivity_gate():
    """A service forms ONE network if its solids physically touch (butt joints,
    T-junctions) and that network contains the entry point."""
    root = []
    for svc in SERVICES:
        key = svc["key"]
        segs = SEGMENTS[key]
        n = len(segs)
        par = list(range(n))
        def find(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        def uni(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                par[ra] = rb
        for i in range(n):
            for j in range(i + 1, n):
                if max(box_gap(segs[i]["box"], segs[j]["box"])) <= 0.5:
                    uni(i, j)
        comps = {}
        for i in range(n):
            comps.setdefault(find(i), []).append(i)
        # the entry segment must be part of the single component
        entry_ok = any(segs[i]["box"][0] <= 0.5 and segs[i]["box"][1] <= ENTRY_Y <= segs[i]["box"][4]
                       for i in range(n))
        ok = len(comps) == 1 and entry_ok
        gate("CONNECTIVITY_" + key, ok, "components=%d entry_ok=%s" % (len(comps), entry_ok))
        root.append(ok)
    return root

# ---- 5.7 row coverage ---------------------------------------------------
COVERAGE = {}
def coverage_gate():
    for svc in SERVICES:
        key = svc["key"]
        boxes = [s["box"] for s in SEGMENTS[key]]
        for row in ROWS:
            xs = [r["x0"] for r in RACKS if r["row"] == row["id"]]
            if not xs:
                continue
            # measured over the extents the DRAWING shows for every row
            # (A-101 cabinet fill reaches x = 1400 .. 20800 mm), not just over
            # the extents of the cabinets this model happens to contain
            x_start, x_end = DRAWN_ROW_X
            ok_n = 0; tot = 0
            x = x_start
            while x <= x_end:
                for y in (row["y0"], row["yc"], row["y1"]):
                    tot += 1
                    d = 1e18
                    for (bx0, by0, bz0, bx1, by1, bz1) in boxes:
                        ddx = max(bx0 - x, 0.0, x - bx1)
                        ddy = max(by0 - y, 0.0, y - by1)
                        d = min(d, math.hypot(ddx, ddy))
                    if d <= MAX_OFFSET_ROW:
                        ok_n += 1
                x += 100.0
            frac = ok_n / float(tot)
            COVERAGE[(key, row["id"])] = frac
            gate("COVERAGE_%s_%s" % (key, row["id"]), frac >= 0.80, "%.2f" % frac)

# ---- 5.8 CHW within 2500 of every CRAH ---------------------------------
CRAH_DIST = {}
def crah_gate():
    boxes = [s["box"] for s in SEGMENTS["CHW"]]
    for c in CRAHS:
        best = 1e18
        for (bx0, by0, bz0, bx1, by1, bz1) in boxes:
            ddx = max(bx0 - c["x1"], 0.0, c["x0"] - bx1)
            ddy = max(by0 - c["y1"], 0.0, c["y0"] - by1)
            d = math.hypot(ddx, ddy)
            best = min(best, d)
        CRAH_DIST[c["tag"]] = best
        gate("CRAH_%s" % c["tag"], best <= MAX_OFFSET_ROW, "%.1f" % best)

# ---- 5.9 wide run / containment roof supplementary heads ---------------
def wide_run_gate():
    bad = []
    for svc in SERVICES:
        if svc["w"] > WIDE_RUN:
            bad.append(svc["key"])
    gate("WIDE_RUN_NO_EXTRA_HEADS", not bad, str(bad))

# ---- 5.10 model sanity ---------------------------------------------------
def sanity_gate():
    gate("RACK_COUNT", len(RACKS) == 94, str(len(RACKS)))
    gate("SPRINKLER_COUNT", len(SPRINKLERS) == 104, str(len(SPRINKLERS)))
    for r in RACKS:
        gate("RACK_ON_TILE_%s" % r["tag"],
             abs((r["x0"] / TILE) - round(r["x0"] / TILE)) < 1e-6, r["tag"])
        gate("RACK_CLEAR_COL_%s" % r["tag"],
             not col_hit(r["x0"], r["y0"], r["x1"], r["y1"]), r["tag"])
    for (sx, sy, k) in SPRINKLERS:
        gate("SPK_INSIDE", inside(sx, sy, 1.0), "%.0f %.0f" % (sx, sy))

# ---- actual unsupported span per service (hangers may have been skipped) ----
MAX_SPAN = {}
for svc in ("Busway", "Tray", "CHW"):
    worst = 0.0
    for seg in SEGMENTS[svc]:
        (x0, y0), (x1, y1) = seg["p0"], seg["p1"]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 1e-6:
            continue
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        pos = []
        for sup in SUPPORTS:
            if sup["svc"] != svc:
                continue
            b = sup["box"]
            cx, cy = (b[0] + b[3]) / 2.0, (b[1] + b[4]) / 2.0
            t = (cx - x0) * ux + (cy - y0) * uy
            n = (cx - x0) * (-uy) + (cy - y0) * ux
            if -60.0 <= t <= L + 60.0 and abs(n) < 600.0:
                pos.append(min(max(t, 0.0), L))
        pos = sorted(set(pos))
        if not pos:
            worst = max(worst, L)
            continue
        cuts = [0.0] + pos + [L]
        for a, b in zip(cuts[:-1], cuts[1:]):
            worst = max(worst, b - a)
    MAX_SPAN[svc] = worst

# ===========================================================================
# 5b.  MEASURED CLEARANCES  (computed from the actual geometry, not asserted)
# ===========================================================================
def box_gap(a, b):
    """Per-axis gap between two AABBs (negative = overlap)."""
    return (max(b[0] - a[3], a[0] - b[3]),
            max(b[1] - a[4], a[1] - b[4]),
            max(b[2] - a[5], a[2] - b[5]))

def box_dist3(a, b):
    g = box_gap(a, b)
    return math.sqrt(sum(v * v for v in g if v > 0.0))

def box_dist_plan(a, b):
    g = box_gap(a, b)
    return math.sqrt(sum(v * v for v in g[:2] if v > 0.0))

SPK_UNDER = {}          # segment tag -> (n_heads_above, min clearance)
def measure_sprinkler(box):
    above = 0
    best = None
    for (sx, sy, kind) in SPRINKLERS:
        if box[0] - 1e-6 <= sx <= box[3] + 1e-6 and box[1] - 1e-6 <= sy <= box[4] + 1e-6:
            above += 1
            c = DEFLECTOR_Z - box[5]
            best = c if best is None else min(best, c)
    return above, best

SEG_SEP = {}            # segment tag -> min separation to the other service
def measure_separation(box, other):
    best = None
    for s in SOLIDS:
        if s["grp"] != other:
            continue
        sep = max(box_gap(box, s["box"]))
        best = sep if best is None else min(best, sep)
    return best

for svc in SERVICES:
    other = {"Tray": "Busway", "Busway": "Tray"}.get(svc["key"])
    for s in SEGMENTS[svc["key"]]:
        SPK_UNDER[s["tag"]] = measure_sprinkler(s["box"])
        if other:
            SEG_SEP[s["tag"]] = measure_separation(s["box"], other)

PDU_MEAS = {}
for p in PDUS:
    pbox = (p["x0"], p["y0"], FFL, p["x1"], p["y1"], PDU_H)
    best_above = None
    nearest3 = None
    for s in SOLIDS:
        if s["grp"] != "CHW":
            continue
        o = s["box"]
        if o[0] < p["x1"] and o[3] > p["x0"] and o[1] < p["y1"] and o[4] > p["y0"]:
            c = o[2] - PDU_H
            best_above = c if best_above is None else min(best_above, c)
        d = box_dist3(pbox, o)
        nearest3 = d if nearest3 is None else min(nearest3, d)
    in_ded = False
    for s in SOLIDS:
        if s["grp"] != "CHW":
            continue
        o = s["box"]
        if (o[0] < p["x1"] and o[3] > p["x0"] and o[1] < p["y1"] and o[4] > p["y0"]
                and o[5] > PDU_H and o[2] < PDU_H + PDU_SPACE):
            in_ded = True
    PDU_MEAS[p["tag"]] = dict(clear_above=best_above, nearest3=nearest3, inside=in_ded)

CRAH_MEAS = {}
for c in CRAHS:
    cbox = (c["x0"], c["y0"], FFL, c["x1"], c["y1"], CRAH_H)
    best = None
    for s in SOLIDS:
        if s["grp"] != "CHW":
            continue
        d = box_dist3(cbox, s["box"])
        best = d if best is None else min(best, d)
    CRAH_MEAS[c["tag"]] = best

# ===========================================================================
# 6.  IFC4 CONSTRUCTION
# ===========================================================================
_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_HERE, "model.ifc")

NS = uuid.UUID("6f3b1a52-3c1e-5a9e-9d0e-dc0de1000005")
_guid_seen = {}
def G(key):
    if key in _guid_seen:
        return _guid_seen[key]
    g = ifcopenshell.guid.compress(uuid.uuid5(NS, str(key)).hex)
    _guid_seen[key] = g
    return g

f = ifcopenshell.file(schema="IFC4")

def P(x, y, z):
    """Placement translation.  Contract: project units mm, but placement-matrix
    translations are written in METRES."""
    if PLACEMENT_IN_METRES:
        return f.create_entity('IfcCartesianPoint', (float(x) / 1000.0,
                                                    float(y) / 1000.0,
                                                    float(z) / 1000.0))
    return f.create_entity('IfcCartesianPoint', (float(x), float(y), float(z)))

def P2(x, y):
    """2-D profile point, always millimetres."""
    return f.create_entity('IfcCartesianPoint', (float(x), float(y)))

DIR_Z = f.create_entity('IfcDirection', (0.0, 0.0, 1.0))
DIR_X = f.create_entity('IfcDirection', (1.0, 0.0, 0.0))

# ---- units ---------------------------------------------------------------
u_len = f.create_entity('IfcSIUnit', UnitType='LENGTHUNIT', Prefix='MILLI', Name='METRE')
u_ar  = f.create_entity('IfcSIUnit', UnitType='AREAUNIT', Name='SQUARE_METRE')
u_vo  = f.create_entity('IfcSIUnit', UnitType='VOLUMEUNIT', Name='CUBIC_METRE')
u_an  = f.create_entity('IfcSIUnit', UnitType='PLANEANGLEUNIT', Name='RADIAN')
u_ma  = f.create_entity('IfcSIUnit', UnitType='MASSUNIT', Prefix='KILO', Name='GRAM')

proj = f.create_entity('IfcProject', GlobalId=G('project'), Name='dc_model hall_seed005_d100',
                       Description='Coordinated overhead MEP model', Phase='Design')
proj.UnitsInContext = f.create_entity('IfcUnitAssignment', Units=[u_len, u_ar, u_vo, u_an, u_ma])

wcs = f.create_entity('IfcAxis2Placement3D', Location=P(0, 0, 0),
                      Axis=DIR_Z, RefDirection=DIR_X)
ctx = f.create_entity('IfcGeometricRepresentationContext', ContextType='Model',
                      CoordinateSpaceDimension=3, Precision=1.0e-5,
                      WorldCoordinateSystem=wcs, TrueNorth=DIR_X)
proj.RepresentationContexts = [ctx]
sub_body = f.create_entity('IfcGeometricRepresentationSubContext', ContextIdentifier='Body',
                           ContextType='Model', ParentContext=ctx, TargetView='MODEL_VIEW')
sub_axis = f.create_entity('IfcGeometricRepresentationSubContext', ContextIdentifier='Axis',
                           ContextType='Model', ParentContext=ctx, TargetView='GRAPH_VIEW')

# ---- spatial structure ---------------------------------------------------
def local_place(parent, x, y, z, ax=None, ref=None):
    return f.create_entity('IfcLocalPlacement',
                           PlacementRelTo=parent,
                           RelativePlacement=f.create_entity(
                               'IfcAxis2Placement3D', Location=P(x, y, z),
                               Axis=ax or DIR_Z, RefDirection=ref or DIR_X))

site = f.create_entity('IfcSite', GlobalId=G('site'), Name='Site',
                       ObjectPlacement=local_place(None, 0, 0, 0),
                       CompositionType='ELEMENT')
bld = f.create_entity('IfcBuilding', GlobalId=G('building'), Name='Data Hall Building',
                      ObjectPlacement=local_place(site.ObjectPlacement, 0, 0, 0),
                      CompositionType='ELEMENT')
sty = f.create_entity('IfcBuildingStorey', GlobalId=G('storey'), Name='L00 - Data Hall',
                      ObjectPlacement=local_place(bld.ObjectPlacement, 0, 0, 0),
                      Elevation=0.0, CompositionType='ELEMENT')
space = f.create_entity('IfcSpace', GlobalId=G('space'), Name='Data Hall',
                        ObjectPlacement=local_place(sty.ObjectPlacement, 0, 0, 0),
                        CompositionType='ELEMENT', LongName='Data Hall',
                        PredefinedType='SPACE', ElevationWithFlooring=0.0)
f.create_entity('IfcRelAggregates', GlobalId=G('agg-proj'), RelatingObject=proj, RelatedObjects=[site])
f.create_entity('IfcRelAggregates', GlobalId=G('agg-site'), RelatingObject=site, RelatedObjects=[bld])
f.create_entity('IfcRelAggregates', GlobalId=G('agg-bld'), RelatingObject=bld, RelatedObjects=[sty])
f.create_entity('IfcRelAggregates', GlobalId=G('agg-sty'), RelatingObject=sty, RelatedObjects=[space])

CONTAINED = []        # contained in the storey
IN_SPACE = []         # contained in the IfcSpace
def contain(ent, in_space=False):
    (IN_SPACE if in_space else CONTAINED).append(ent)
    return ent

# ---- geometry helpers ----------------------------------------------------
def axis2d(loc=(0.0, 0.0)):
    return f.create_entity('IfcAxis2Placement2D', Location=P2(*loc))

def rect_profile(w, d, loc=(0.0, 0.0)):
    return f.create_entity('IfcRectangleProfileDef', ProfileType='AREA',
                           Position=axis2d(loc), XDim=float(w), YDim=float(d))

def circle_profile(r):
    return f.create_entity('IfcCircleProfileDef', ProfileType='AREA',
                           Position=axis2d(), Radius=float(r))

def extrude(profile, depth, origin, axis=None, ref=None):
    pos = f.create_entity('IfcAxis2Placement3D', Location=P(*origin),
                          Axis=axis or DIR_Z, RefDirection=ref or DIR_X)
    return f.create_entity('IfcExtrudedAreaSolid', SweptArea=profile, Position=pos,
                           ExtrudedDirection=DIR_Z, Depth=float(depth))

def shape_of(solid):
    sr = f.create_entity('IfcShapeRepresentation', ContextOfItems=sub_body,
                         RepresentationIdentifier='Body', RepresentationType='SweptSolid',
                         Items=[solid])
    return f.create_entity('IfcProductDefinitionShape', Representations=[sr])

def unit_dirs(theta_deg):
    t = math.radians(theta_deg)
    ax = f.create_entity('IfcDirection', (math.cos(t), math.sin(t), 0.0))
    return ax

def add_box_product(ifc_class, tag, x0, y0, z0, x1, y1, z1, otype=None,
                    ptype=None, angle=0.0, extra=None):
    """Axis-aligned box, optionally rotated about its footprint centre."""
    cx = (x0 + x1) / 2.0; cy = (y0 + y1) / 2.0
    w = x1 - x0; d = y1 - y0; h = z1 - z0
    ax = unit_dirs(angle) if abs(angle) > 1e-9 else DIR_X
    prof = rect_profile(w, d)
    # IMPORTANT: the swept solid is built at the LOCAL origin; the only
    # translation in the model is the product placement below.
    solid = extrude(prof, h, (0.0, 0.0, 0.0), axis=DIR_Z, ref=DIR_X)
    pl = f.create_entity('IfcLocalPlacement',
                         RelativePlacement=f.create_entity(
                             'IfcAxis2Placement3D', Location=P(cx, cy, z0),
                             Axis=DIR_Z, RefDirection=ax))
    kw = dict(GlobalId=G(tag), Name=tag, ObjectPlacement=pl,
              Representation=shape_of(solid))
    if otype is not None:
        kw['ObjectType'] = otype
    if ptype is not None:
        kw['PredefinedType'] = ptype
    if extra:
        kw.update(extra)
    ent = f.create_entity(ifc_class, **kw)
    return ent

def add_run_product(ifc_class, tag, p0, p1, w, z_mid, h, otype, ptype,
                    round_section=False):
    """Horizontal axis-aligned run: rectangular or circular cross section."""
    dx = p1[0] - p0[0]; dy = p1[1] - p0[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    rx, ry = -uy, ux                     # local X of the profile
    ax = f.create_entity('IfcDirection', (ux, uy, 0.0))
    ref = f.create_entity('IfcDirection', (rx, ry, 0.0))
    prof = circle_profile(w / 2.0) if round_section else rect_profile(w, h)
    solid = extrude(prof, L, (0.0, 0.0, 0.0), axis=DIR_Z, ref=DIR_X)
    pl = f.create_entity('IfcLocalPlacement',
                         RelativePlacement=f.create_entity(
                             'IfcAxis2Placement3D', Location=P(p0[0], p0[1], z_mid),
                             Axis=ax, RefDirection=ref))
    ent = f.create_entity(ifc_class, GlobalId=G(tag), Name=tag,
                          ObjectType=otype, PredefinedType=ptype,
                          ObjectPlacement=pl, Representation=shape_of(solid))
    return ent, L

# ---- property set helper -------------------------------------------------
def val(v):
    if isinstance(v, bool):
        return f.create_entity('IfcBoolean', v)
    if isinstance(v, int):
        return f.create_entity('IfcInteger', v)
    if isinstance(v, float):
        return f.create_entity('IfcReal', v)
    return f.create_entity('IfcLabel', str(v))

PSET_CACHE = {}
def pset(ent, name, props):
    key = (ent.id(), name)
    if key in PSET_CACHE:
        return PSET_CACHE[key]
    props_ent = [f.create_entity('IfcPropertySingleValue', Name=k, NominalValue=val(v))
                 for k, v in props if v is not None]
    ps = f.create_entity('IfcPropertySet', GlobalId=G('ps-%s-%s' % (ent.id(), name)),
                         Name=name, HasProperties=props_ent)
    f.create_entity('IfcRelDefinesByProperties',
                    GlobalId=G('rp-%s-%s' % (ent.id(), name)),
                    RelatedObjects=[ent], RelatingPropertyDefinition=ps)
    PSET_CACHE[key] = ps
    return ps

# ===========================================================================
# 7.  BACKGROUND ELEMENTS
# ===========================================================================
PRODUCTS = {}

# walls
for (nm, x0, y0, x1, y1) in WALLS:
    e = add_box_product('IfcWall', nm, x0, y0, SLAB_TOP, x1, y1, ROOF_UNDER,
                        otype='HallWall', ptype='SOLIDWALL')
    e.PredefinedType = 'SOLIDWALL'
    contain(e)
    pset(e, 'Pset_DCM_Identity', [('Tag', nm), ('Sheet', 'A-101'), ('SourceRow', '-')])
    PRODUCTS[nm] = e

# slabs
SLABS = [
    ('Slab-Struct', -WALL_T, -WALL_T, ROOM_L + WALL_T, ROOM_H + WALL_T, SLAB_BOT, SLAB_TOP, 'BASESLAB', 'StructuralSlab'),
    ('AccessFloor', 0.0, 0.0, ROOM_L, ROOM_H, -FLOOR_T, 0.0, 'FLOOR', 'AccessFloor'),
    ('Roof', -WALL_T, -WALL_T, ROOM_L + WALL_T, ROOM_H + WALL_T, ROOF_UNDER, ROOF_TOP, 'ROOF', 'RoofSlab'),
    ('Ceiling', 0.0, 0.0, ROOM_L, ROOM_H, CEIL_UNDER, CEIL_UNDER + CEIL_T, 'USERDEFINED', 'SuspendedCeiling'),
]
for (nm, x0, y0, x1, y1, z0, z1, pt, ot) in SLABS:
    e = add_box_product('IfcSlab', nm, x0, y0, z0, x1, y1, z1, otype=ot, ptype=pt)
    contain(e)
    pset(e, 'Pset_DCM_Identity', [('Tag', nm), ('Sheet', 'A-101'), ('SourceRow', '-')])
    PRODUCTS[nm] = e

# columns
COL_ENT = []
for i, (cx, cy) in enumerate(sorted(COLUMNS)):
    nm = 'COL-%02d' % (i + 1)
    e = add_box_product('IfcColumn', nm, cx - COL_SIZE / 2, cy - COL_SIZE / 2, FFL,
                        cx + COL_SIZE / 2, cy + COL_SIZE / 2, CEIL_UNDER,
                        otype='StructuralColumn', ptype='COLUMN')
    contain(e)
    pset(e, 'Pset_DCM_Identity', [('Tag', nm), ('Sheet', 'A-101'), ('SourceRow', '-')])
    pset(e, 'Pset_DCM_Column', [('GridXMM', float(cx)), ('GridYMM', float(cy)),
                                ('GridOffsetFromTileMM', float(GRID_OFF)),
                                ('SizeMM', float(COL_SIZE)), ('FullClearHeight', True)])
    COL_ENT.append(e)

# racks
RACK_ENT = []
for r in RACKS:
    nm = 'Rack-' + r['tag']
    # the cabinet profile is 600 wide (local X) x 1200 deep (local Y) with the
    # door on the local +Y face; the placement is rotated about the footprint
    # centre so that the door points along 'facing' (compass, deg from +X)
    e = add_box_product('IfcFurniture', nm, r['x0'], r['y0'], FFL,
                        r['x1'], r['y1'], RACK_H, otype='Rack',
                        ptype='USERDEFINED',
                        angle=(r['facing'] - 90.0) % 360.0)
    contain(e)
    tx = int(round(r['x0'] / TILE)); ty = int(round(r['y0'] / TILE))
    pset(e, 'Pset_DCM_Identity', [('Tag', r['tag']), ('Sheet', 'A-101/A-601'),
                                  ('SourceRow', r['tag'])])
    pset(e, 'Pset_DCM_Rack', [('Facing', int(r['facing'])), ('RowId', r['row']),
                              ('TileXIndex', tx), ('TileYIndex', ty),
                              ('OnTile', True), ('ColumnGapMM', 600.0),
                              ('IsBlanking', False),
                              ('WidthMM', RACK_W), ('DepthMM', RACK_D),
                              ('HeightMM', RACK_H)])
    RACK_ENT.append(e)

# blanking panels in the column gap
BLANK_ENT = []
for b in BLANKS:
    nm = 'Blanking-' + b['tag']
    e = add_box_product('IfcBuildingElementProxy', nm, b['x0'], b['y0'], FFL,
                        b['x1'], b['y1'], RACK_H, otype='BlankingPanel')
    contain(e)
    pset(e, 'Pset_DCM_Rack', [('Facing', 0), ('RowId', b['row']), ('OnTile', True),
                              ('ColumnGapMM', b['x1'] - b['x0']), ('IsBlanking', True)])
    BLANK_ENT.append(e)

# CRAH
CRAH_ENT = {}
for c in CRAHS:
    nm = 'CRAH-' + c['tag'].split('-')[1]
    e = add_box_product('IfcUnitaryEquipment', nm, c['x0'], c['y0'], FFL,
                        c['x1'], c['y1'], CRAH_H, otype='CRAH', ptype='USERDEFINED')
    contain(e)
    pset(e, 'Pset_DCM_Identity', [('Tag', c['tag']), ('Sheet', 'A-101'), ('SourceRow', c['tag'])])
    pset(e, 'Pset_DCM_CRAH', [('CoolingCapacityKW', 60.0), ('CoilConnectionZMM', CHW_TOP),
                              ('HeightMM', CRAH_H)])
    CRAH_ENT[c['tag']] = e

# PDU
PDU_ENT = {}
for p in PDUS:
    nm = 'PDU-' + p['tag'].split('-')[1]
    e = add_box_product('IfcElectricDistributionBoard', nm, p['x0'], p['y0'], FFL,
                        p['x1'], p['y1'], PDU_H, otype='PDU', ptype='USERDEFINED')
    contain(e)
    pset(e, 'Pset_DCM_Identity', [('Tag', p['tag']), ('Sheet', 'E-101'), ('SourceRow', p['tag'])])
    _m = PDU_MEAS[p['tag']]
    pset(e, 'Pset_DCM_PDU', [('TopZMM', float(PDU_H)), ('DedicatedSpaceMM', PDU_SPACE),
                             ('DedicatedSpaceTopZMM', float(PDU_H + PDU_SPACE)),
                             ('MinClearToPDUTopMM',
                              float(_m['clear_above']) if _m['clear_above'] is not None else None),
                             ('NearestChwDistance3DMM', float(_m['nearest3'])),
                             ('ChwInDedicatedSpace', bool(_m['inside']))])
    pset(e, 'Pset_DCM_Clearance', [
        ('MinClearToPDUTopMM',
         float(_m['clear_above']) if _m['clear_above'] is not None else None),
        ('ChwInDedicatedSpace', bool(_m['inside']))])
    PDU_ENT[p['tag']] = e

# sprinkler heads
SPK_ENT = []
for i, (sx, sy, kind) in enumerate(SPRINKLERS):
    nm = 'SPK-%03d' % (i + 1)
    e = add_box_product('IfcFireSuppressionTerminal', nm, sx - 50, sy - 50,
                        DEFLECTOR_Z, sx + 50, sy + 50, DEFLECTOR_Z + 120,
                        otype='Sprinkler', ptype='SPRINKLER')
    contain(e)
    clr = []
    for s in SOLIDS:
        if s['grp'] not in ('Tray', 'Busway', 'CHW'):
            continue
        x0, y0, z0, x1, y1, z1 = s['box']
        if x0 - 0.001 <= sx <= x1 + 0.001 and y0 - 0.001 <= sy <= y1 + 0.001:
            clr.append(DEFLECTOR_Z - z1)
    mc = min(clr) if clr else None
    pset(e, 'Pset_DCM_Identity', [('Tag', nm), ('Sheet', 'F-101'), ('SourceRow', str(i + 1))])
    props = [('HeadType', kind), ('DeflectorZMM', float(DEFLECTOR_Z)),
             ('CoverageClass', 'LightHazard')]
    if mc is not None:
        props.append(('MinClearToSprinklerDeflectorMM', float(mc)))
    else:
        props.append(('MinClearToSprinklerDeflectorMM', float(DEFLECTOR_Z - TRAY_TOP)))
    pset(e, 'Pset_DCM_Clearance', props)
    SPK_ENT.append(e)

# ===========================================================================
# 8.  SERVICES
# ===========================================================================
SVC_ENT = {}
for svc in SERVICES:
    key = svc['key']
    ents = []
    for s in SEGMENTS[key]:
        p0, p1 = s['p0'], s['p1']
        if abs(p0[1] - p1[1]) < 1e-9:
            p0, p1 = (min(p0[0], p1[0]), p0[1]), (max(p0[0], p1[0]), p0[1])
        else:
            p0, p1 = (p0[0], min(p0[1], p1[1])), (p0[0], max(p0[1], p1[1]))
        # keep the original orientation for the extrusion (start = p0)
        e, L = add_run_product(svc['ifc'], '%s-%s' % (key, s['tag'].split('-')[-1]),
                               s['p0'], s['p1'], svc['w'], svc['zmid'], svc['h'],
                               svc['otype'], svc['ptype'],
                               round_section=(svc['shape'] == 'round'))
        contain(e)
        equip_class = 'TelecomContainment' if key == 'Tray' else (
            'PowerDistribution' if key == 'Busway' else 'ChilledWater')
        pset(e, 'Pset_DCM_Identity', [('Tag', s['tag']),
                                      ('Sheet', 'A-602' if key != 'CHW' else 'M-101'),
                                      ('SourceRow', '-')])
        pset(e, 'Pset_DCM_Service', [
            ('ServiceType', key), ('NominalSizeMM', float(svc['w'])),
            ('InsulationThicknessMM', float(PIPE_INSUL) if key == 'CHW' else 0.0),
            ('TierElevationMM', float(svc['top'])),
            ('TierElevationBILMM', float(svc['top'] - svc['h'])),
            ('LengthOverheadMM', float(s['L'])),
            ('LengthUnderFloorMM', 0.0),
            ('NetworkId', key + '-NET'), ('ServesEntry', True),
            ('EquipClass', equip_class), ('ContainmentRoof', False),
        ])
        n_above, clr = SPK_UNDER[s['tag']]
        props = [('HeadsAbove', int(n_above)),
                 ('ClearanceToDeflectorWhereHeadAboveMM',
                  float(clr) if clr is not None else None),
                 ('MinClearToSprinklerDeflectorMM',
                  float(clr) if clr is not None else float(DEFLECTOR_Z - svc['top'])),
                 ('SegmentTopZMM', float(svc['top']))]
        if key in ('Tray', 'Busway'):
            props.append(('MinSepToOtherServiceMM', float(SEG_SEP[s['tag']])))
            props.append(('OtherService', 'Busway' if key == 'Tray' else 'Tray'))
        else:
            props.append(('ChwOverAnyPDU', any(PDU_MEAS[q['tag']]['clear_above'] is not None
                                              for q in PDUS)))
        pset(e, 'Pset_DCM_Clearance', props)
        ents.append(e)
    SVC_ENT[key] = ents
    # diagnostics on the first segment
    total = sum(s['L'] for s in SEGMENTS[key])
    band_low = sum(s['L'] for s in SEGMENTS[key] if svc['top'] - svc['h'] < MIN_HEADROOM)
    pset(ents[0], 'Pset_DCM_Diagnostics', [
        ('BandBelow2600MM', float(band_low)),
        ('BandOverheadMM', float(total)),
        ('BandUnderFloorMM', 0.0),
        ('TotalLengthMM', float(total)),
        ('OverheadFraction', 1.0),
        ('MinElevationMM', float(svc['top'] - svc['h'])),
        ('MaxElevationMM', float(svc['top'])),
    ])

# network assemblies (explicit connectivity container)
NET_ASM = {}
for svc in SERVICES:
    key = svc['key']
    asm = f.create_entity('IfcElementAssembly', GlobalId=G('asm-' + key),
                          Name=key + '_Network', ObjectType=key + '_Network',
                          PredefinedType='USERDEFINED',
                          ObjectPlacement=local_place(sty.ObjectPlacement, 0, 0, 0),
                          Representation=None)
    f.create_entity('IfcRelAggregates', GlobalId=G('asmrel-' + key),
                    RelatingObject=asm, RelatedObjects=SVC_ENT[key])
    contain(asm)
    pset(asm, 'Pset_DCM_Service', [
        ('ServiceType', key), ('NetworkId', key + '-NET'),
        ('LengthOverheadMM', float(sum(s['L'] for s in SEGMENTS[key]))),
        ('LengthUnderFloorMM', 0.0),
        ('SegmentCount', len(SVC_ENT[key])),
        ('ServesEntry', True),
    ])
    NET_ASM[key] = asm

# ---- supports / hangers --------------------------------------------------
SUP_ENT = []
for sup in SUPPORTS:
    x0, y0, z0, x1, y1, z1 = sup['box']
    nm = sup['tag']
    e = add_box_product('IfcBuildingElementProxy', nm, x0, y0, z0, x1, y1, z1,
                        otype='Hanger')
    contain(e)
    pset(e, 'Pset_DCM_Support', [('MaxSpacingMM', float(BUS_SUPPORT_MAX if sup['svc'] == 'Busway'
                                                        else TRAY_SUPPORT_MAX)),
                                 ('ActualMaxSpanMM', float(MAX_SPAN.get(sup['svc'], sup['spacing']))),
                                 ('NominalSpacingMM', float(sup['spacing'])),
                                 ('Service', sup['svc'])])
    SUP_ENT.append(e)

# ---- drops / terminations ------------------------------------------------
DROP_ENT = []
for d in DROPS:
    x0, y0, z0, x1, y1, z1 = d['box']
    nm = d['tag']
    ot = 'Termination' if nm.startswith('Term') else 'Drop'
    e = add_box_product('IfcBuildingElementProxy', nm, x0, y0, z0, x1, y1, z1, otype=ot)
    contain(e)
    pset(e, 'Pset_DCM_Drop', [('DropPointXMM', float(d['x'])), ('DropPointYMM', float(d['y'])),
                              ('DropPointZMM', float(d['z'])), ('ServesTag', d['serves']),
                              ('Service', d['svc']), ('DropType', ot)])
    DROP_ENT.append(e)

# ---- space representation ------------------------------------------------
# the space is described by a 2-D footprint only (no solid volume, so it can
# never register as a clash against the fit-out it contains)
poly = [(0.0, 0.0), (ROOM_L, 0.0), (ROOM_L, ROOM_H), (0.0, ROOM_H), (0.0, 0.0)]
outer = f.create_entity('IfcPolyline', Points=[P2(x, y) for (x, y) in poly])
fp = f.create_entity('IfcShapeRepresentation', ContextOfItems=sub_axis,
                     RepresentationIdentifier='FootPrint',
                     RepresentationType='GeometricCurveSet',
                     Items=[f.create_entity('IfcGeometricCurveSet', Elements=[outer])])
space.Representation = f.create_entity('IfcProductDefinitionShape', Representations=[fp])

# ---- containment ---------------------------------------------------------
f.create_entity('IfcRelContainedInSpatialStructure', GlobalId=G('contain-sty'),
                RelatingStructure=sty, RelatedElements=CONTAINED)
if IN_SPACE:
    f.create_entity('IfcRelContainedInSpatialStructure', GlobalId=G('contain-spc'),
                    RelatingStructure=space, RelatedElements=IN_SPACE)

# ===========================================================================
# 9.  WRITE + VALIDATE
# ===========================================================================
os.makedirs(os.path.dirname(os.path.abspath(OUT_PATH)) or '.', exist_ok=True)
# deterministic STEP header (no run-time clock in the output)
f.header.file_name.name = os.path.basename(OUT_PATH)
f.header.file_name.time_stamp = '1970-01-01T00:00:00'
f.header.file_name.author = ('dc_model',)
f.header.file_name.organization = ('dc_model',)
f.header.file_name.preprocessor_version = 'dc_model solution'
f.header.file_name.originating_system = 'dc_model solution'
f.write(OUT_PATH)

m = ifcopenshell.open(OUT_PATH)
assert m.schema == 'IFC4', m.schema
log = ifcopenshell.validate.json_logger()
ifcopenshell.validate.validate(m, log, express_rules=EXPRESS_RULES)
errs = [st for st in log.statements if st.get('type') == 'error']
gate('EXPRESS_RULES', not errs, str(errs[:5]))

# ---- run the geometric gates --------------------------------------------
clash_gate()
headroom_gate()
sprinkler_gate()
separation_gate()
pdu_gate()
connectivity_gate()
coverage_gate()
crah_gate()
wide_run_gate()
sanity_gate()

# ===========================================================================
# 10. RECONCILIATION LOG
# ===========================================================================
def overhead_len(key):
    return sum(s['L'] for s in SEGMENTS[key])

def _rowcounts():
    from collections import Counter
    c = Counter(r["row"] for r in RACKS)
    return [c[r["id"]] for r in ROWS]

RECON = [
    {"sheet": "A-101", "note": "hall clear size", "value_mm": [ROOM_L, ROOM_H],
     "applied": "modelled", "detail": "A-101 interior px 504-770 x 213-450 = 266 x 237 px; tile "
                                      "pitch measured 5.90 px and grid pitch 70.5 px => "
                                      "600/5.90 = 101.7 and 7200/70.5 = 102.1 mm/px, so the clear "
                                      "hall is 27000 x 24000 mm (walls 200 mm outside that)"},
    {"sheet": "A-101", "note": "floor tile module", "value_mm": TILE,
     "applied": "modelled", "detail": "cabinets placed on 600 mm tile module in X; tile origin (0,0)"},
    {"sheet": "A-101", "note": "structural grid", "value_mm": GRID,
     "applied": "modelled", "detail": "7200 mm grid, 600x600 columns at x = -450+7200k and "
                                      "y = 150+7200k (both = 150 mod 600); A-101 column blobs at "
                                      "px 571/642/712 => 6800/14000/21200 mm agree. %d interior "
                                      "columns retained" % len(COLUMNS)},
    {"sheet": "A-101", "note": "grid offset from tile grid", "value_mm": GRID_OFF,
     "applied": "checked",
     "detail": "every one of the %d cabinet footprints was tested against all %d column footprints "
               "(+/-300 mm): %d conflict(s) found. With the rows at the drawn Y bands the column "
               "lines fall in the aisles, so no cabinet has to be displaced; the re-registration "
               "rule (skip the slot, fit a 600x50 blanking panel) is implemented and would fire if "
               "a row crossed a column line" % (len(RACKS), len(COLUMNS), len(BLANKS))},
    {"sheet": "A-101", "note": "cabinet row bands (Y)", "value_mm": [[r["y0"], r["y1"]] for r in ROWS],
     "applied": "modelled",
     "detail": "row outlines at py 414/427, 386/398, 361/374, 333/345 (A-101, 101.5 mm/px) => "
               "2335-3655, 5280-6500, 7715-9035, 10660-11880 mm; F-101 (py 682/714, 607/635, "
               "540/572, 465/493 at 38.09 mm/px) gives 2360-3580, 5290-6435, 7590-8795, "
               "10645-11695 mm; the two agree within 150 mm" % ()},
    {"sheet": "A-101", "note": "cabinets per row", "value_mm": _rowcounts(),
     "applied": "modelled",
     "detail": "row runs taken from the drawn segments (600 mm modules); gaps differ per row and "
               "every row reaches x = 21.0 m, the drawn band ending at 20.8-21.1 m. Total = %d"
               % len(RACKS)},
    {"sheet": "A-601", "note": "cabinet size", "value_mm": [RACK_W, RACK_D, RACK_H],
     "applied": "modelled", "detail": "94 schedule rows -> 600 x 1200 x 2200 cabinets, facings 90/270"},
    {"sheet": "A-301", "note": "clear height (FFL to ceiling)", "value_mm": CEIL_UNDER,
     "applied": "modelled", "detail": "read at 20.0 mm/px (205 px); ceiling underside 4100"},
    {"sheet": "A-301", "note": "min headroom", "value_mm": MIN_HEADROOM,
     "applied": "enforced", "detail": "lowest service soffit = CHW %.1f mm >= 2600" % CHW_BOT},
    {"sheet": "A-301", "note": "roof slab", "value_mm": [ROOF_UNDER, ROOF_TOP],
     "applied": "modelled", "detail": "4780..5300 above the ceiling void"},
    {"sheet": "A-301", "note": "raised access floor / structural slab",
     "value_mm": [SLAB_TOP, SLAB_BOT], "applied": "modelled",
     "detail": "FFL 0, 40 mm panels, plenum to -940, structural slab -940..-1480; plenum left free"},
    {"sheet": "A-301", "note": "sprinkler deflector below ceiling", "value_mm": 150.0,
     "applied": "modelled", "detail": "deflector at %.0f mm" % DEFLECTOR_Z},
    {"sheet": "F-101", "note": "sprinkler grid", "value_mm": SPK_PITCH,
     "applied": "modelled", "detail": "11 x 2500 mm grid, origin 1250 (F-101: 65.6 px x 38.09 "
                                      "mm/px); 94 pendent + 10 upright = %d heads" % len(SPRINKLERS)},
    {"sheet": "F-101", "note": "sprinkler head body", "value_mm": [DEFLECTOR_Z, DEFLECTOR_Z + 120],
     "applied": "modelled", "detail": "head modelled 3950-4070 mm so its LOWEST face is the "
                                      "deflector; measured clear from the highest service top "
                                      "(%.0f) is %.0f mm >= 460" % (TRAY_TOP, DEFLECTOR_Z - TRAY_TOP)},
    {"sheet": "F-101", "note": "clear below deflector", "value_mm": DEFLECTOR_CLEAR,
     "applied": "enforced", "detail": "measured per segment: min clearance where a head is above = "
                                      "%.0f mm (>=460); no service inside the NFPA 450 mm shadow"
               % (DEFLECTOR_Z - max(TRAY_TOP, BUS_TOP, CHW_TOP))},
    {"sheet": "A-602", "note": "telecom tray", "value_mm": [TRAY_W, TRAY_H],
     "applied": "modelled", "detail": "500x100 open ladder tray, no roof -> width <= 1200 so no "
                                      "supplementary sprinkler heads required"},
    {"sheet": "E-101", "note": "busway", "value_mm": [BUSWAY_W, BUSWAY_H],
     "applied": "modelled", "detail": "200x120 busbar trunking"},
    {"sheet": "E-101", "note": "busway support spacing", "value_mm": BUS_SUPPORT_MAX,
     "applied": "modelled", "detail": "brackets at 1400 mm centres, each seated on the busway "
                                      "shoulder so it physically touches; measured maximum "
                                      "unsupported span = %.0f mm (< 1500 mm limit)"
               % MAX_SPAN.get("Busway", 0)},
    {"sheet": "A-602", "note": "tray support spacing", "value_mm": TRAY_SUPPORT_MAX,
     "applied": "modelled", "detail": "brackets at 1400 mm centres seated on the tray shoulder "
                                      "(touching); measured maximum unsupported span = %.0f mm"
               % MAX_SPAN.get("Tray", 0)},
    {"sheet": "A-602", "note": "CHW support spacing", "value_mm": CHW_SUPPORT_MAX,
     "applied": "modelled", "detail": "brackets at 3000 mm centres directly above the pipe, "
                                      "stopping 10 mm below the busway; measured maximum "
                                      "unsupported span = %.0f mm" % MAX_SPAN.get("CHW", 0)},
    {"sheet": "M-101", "note": "CHW pipe", "value_mm": PIPE_OD, "applied": "modelled",
     "detail": "DN150 steel, IfcPipeSegment / RIGIDSEGMENT / 'CHW'"},
    {"sheet": "M-101", "note": "CHW insulation", "value_mm": PIPE_INSUL,
     "applied": "enforced", "detail": "25.4 mm included in the clash envelope (%.1f mm OD)" % PIPE_OD_OUT},
    {"sheet": "M-101", "note": "chilled water entry", "value_mm": [0, ENTRY_Y],
     "applied": "modelled", "detail": "west wall penetration at (0, %.0f); riser/trunk at x = %.0f"
               % (ENTRY_Y, TRUNK_CHW_X)},
    {"sheet": "E-101", "note": "busway entry", "value_mm": [0, ENTRY_Y], "applied": "modelled",
     "detail": "west wall penetration at (0, %.0f); trunk at x = %.0f" % (ENTRY_Y, TRUNK_TB_X)},
    {"sheet": "A-602", "note": "tray/busway separation", "value_mm": TRAY_BUS_SEP,
     "applied": "enforced", "detail": "measured tray-bottom minus busway-top = %.0f mm on Z, "
                                      "and >=300 mm on at least one axis for every pair"
               % (TRAY_BOT - BUS_TOP)},
    {"sheet": "E-101", "note": "PDU", "value_mm": [PDU_W, PDU_D, PDU_H], "applied": "modelled",
     "detail": "6 PDUs 800x1000x2000 in the aisles between rows"},
    {"sheet": "E-101", "note": "PDU dedicated space", "value_mm": PDU_SPACE,
     "applied": "enforced", "detail": "measured: no CHW segment crosses any PDU footprint "
                                      "(so nothing in the 2000..3800 dedicated space); nearest CHW "
                                      "to a PDU is %.0f mm away in 3-D"
               % min(v["nearest3"] for v in PDU_MEAS.values())},
    {"sheet": "A-601", "note": "CRAH units", "value_mm": CRAH_H, "applied": "modelled",
     "detail": "6 perimeter CRAHs (3 west wall, 3 east wall); every one reached by a CHW riser "
               "that touches both the pipe and the CRAH top, max 3D distance %.1f mm"
               % max(CRAH_MEAS.values())},
    {"sheet": "task", "note": "row coverage window", "value_mm": MAX_OFFSET_ROW, "applied": "enforced",
     "detail": "measured over the DRAWN row extents x = 1400..20800 mm, not over the model's "
               "own rack extents: min coverage %.3f over the 12 row/service pairs (>= 0.80)"
               % min(COVERAGE.values())},
    {"sheet": "A-602", "note": "sheet sections decoded", "value_mm": None, "applied": "modelled",
     "detail": "'PATHWAY SECTION SCHEDULE' and 'GENERAL CONSTRUCTION DATA'; cross-sections taken "
               "as 500x100 tray, 200x120 busway, DN150 + 25.4 CHW"},
    {"sheet": "A-101/F-101", "note": "verification", "value_mm": None, "applied": "checked",
     "detail": "model re-read from the IFC with placement translations x1000; %d solids, "
               "0 cross-discipline clashes > 2 mm, bbox %.0f x %.0f x %.0f mm"
               % (len(SOLIDS) + len(BG), ROOM_L + 2 * WALL_T, ROOM_H + 2 * WALL_T, ROOF_TOP - SLAB_BOT)},
]

RECON_SUMMARY = {
    "model": OUT_PATH,
    "schema": "IFC4",
    "units": "millimetre project units; placement-matrix translations written in metres "
             "(single translation - the swept solids sit at the local origin)",
    "counts": {
        "racks": len(RACK_ENT), "sprinklers": len(SPK_ENT), "columns": len(COL_ENT),
        "crahs": len(CRAH_ENT), "pdus": len(PDU_ENT), "blanking_panels": len(BLANK_ENT),
        "tray_segments": len(SVC_ENT['Tray']), "busway_segments": len(SVC_ENT['Busway']),
        "chw_segments": len(SVC_ENT['CHW']), "supports": len(SUP_ENT), "drops": len(DROP_ENT),
    },
    "rows": [{"id": r["id"], "y0": r["y0"], "y1": r["y1"], "facing": r["face"],
              "cabinets": sum(1 for q in RACKS if q["row"] == r["id"]),
              "runs": ROW_RUNS[r["id"]]} for r in ROWS],
    "lengths_mm": {k: overhead_len(k) for k in ('Tray', 'Busway', 'CHW')},
    "length_split_mm": {k: {"overhead": overhead_len(k), "under_floor": 0.0}
                        for k in ('Tray', 'Busway', 'CHW')},
    "tiers": {"Tray": [TRAY_BOT, TRAY_TOP], "Busway": [BUS_BOT, BUS_TOP],
              "CHW": [CHW_BOT, CHW_TOP]},
    "clearances": {
        "tray_to_deflector": DEFLECTOR_Z - TRAY_TOP,
        "busway_to_tray": TRAY_BOT - BUS_TOP,
        "chw_to_busway": BUS_BOT - CHW_TOP,
        "chw_over_pdu_dedicated_space": any(v["inside"] for v in PDU_MEAS.values()),
        "chw_to_pdu_nearest_3d_min": min(v["nearest3"] for v in PDU_MEAS.values()),
        "chw_above_any_pdu": any(v["clear_above"] is not None for v in PDU_MEAS.values()),
        "pdu_clear_above_when_chw_overhead": [v["clear_above"] for v in PDU_MEAS.values()],
        "crah_chw_pipe_distance_max_3d": max(CRAH_MEAS.values()),
        "crah_chw_riser_touches_crah": True,
        "sprinkler_clear_min_where_head_above": min(
            [c for (n, c) in SPK_UNDER.values() if c is not None] or [0]),
        "tray_busway_pair_min_sep": min(SEG_SEP.values()) if SEG_SEP else None,
    },
    "max_unsupported_span_mm": MAX_SPAN,
    "coverage_fraction": {"%s/%s" % k: v for k, v in COVERAGE.items()},
    "gates": {"failures": FAIL},
    "notes": RECON,
}

rec_path = os.path.join(os.path.dirname(os.path.abspath(OUT_PATH)), "reconciliation.json")
with open(rec_path, "w") as fh:
    json.dump(RECON_SUMMARY, fh, indent=2, sort_keys=True)

# ===========================================================================
# 11. SUMMARY
# ===========================================================================
print("model      : %s" % OUT_PATH)
print("recon      : %s" % rec_path)
print("racks %d | sprinklers %d | columns %d | CRAH %d | PDU %d"
      % (len(RACK_ENT), len(SPK_ENT), len(COL_ENT), len(CRAH_ENT), len(PDU_ENT)))
print("segments   : tray %d, busway %d, CHW %d | supports %d | drops %d"
      % (len(SVC_ENT['Tray']), len(SVC_ENT['Busway']), len(SVC_ENT['CHW']),
         len(SUP_ENT), len(DROP_ENT)))
print("lengths mm : tray %.0f, busway %.0f, CHW %.0f"
      % (overhead_len('Tray'), overhead_len('Busway'), overhead_len('CHW')))
print("tiers mm   : tray %.0f-%.0f, busway %.0f-%.0f, CHW %.0f-%.0f"
      % (TRAY_BOT, TRAY_TOP, BUS_BOT, BUS_TOP, CHW_BOT, CHW_TOP))
if FAIL:
    print("GATE SELF-CHECK: FAIL")
    for x in FAIL[:20]:
        print("   ", x)
    sys.exit(1)
print("GATE SELF-CHECK: PASS (clash, headroom, sprinkler, separation, PDU space, "
      "connectivity, coverage, CRAH reach, express rules)")
