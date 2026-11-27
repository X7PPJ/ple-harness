All six findings are fixed and re-verified.

## What changed

**1. The hidden support‑support clash is gone, and the gate no longer hides it.** The `("support","support")` (and support↔service) whitelist entries are removed from `clash_gate()` — only `("Tray","Tray")`, `("Busway","Busway")`, `("CHW","CHW")` butted joints are exempt. My independent checker was also too lenient (it grouped every `IfcBuildingElementProxy/"Hanger"` together); it now compares **every solid against every other solid with no skipping at all** and still reports **0 clashes**. The brackets are also rejected if they'd overlap an already‑placed bracket.

**2. Brackets now physically touch their service.** Each bracket is seated on the shoulder of its run instead of floating beside it:

| service | offset from centreline | z range | contact |
|---|---|---|---|
| tray (500 wide) | −(250+50) = −300 | 3480 → 3700 | touches tray top |
| busway (200 wide) | −(100+50) = −150 | 3060 → 3370 (10 mm below tray) | touches busway top |
| CHW (219 OD) | 0 | 2829 → 2930 (10 mm below busway) | touches pipe top |

Measured support→service gap is now **0.0 mm on all 146 brackets** (55 tray, 55 busway, 36 CHW), and the measured max unsupported span is **1400 / 1400 / 3000 mm** — all inside the 1500/1500/3000 limits.

**3. The deflector is now a real surface.** Heads are modelled **3950 → 4070 mm**, so the *lowest face is the deflector* at 3950. Clear space from the highest service top (3480) is a measured **470 mm** to a real face, outside both the 460 mm rule and the 450 mm NFPA shadow.

**4. Same‑service interpenetration removed.** Branches now **butt onto the trunk face**, not its centreline, and the trunk is extended by its half‑width to close the corner: tray headers start at 2050 (trunk face), busway at 1900, CHW at 1909.6, entry stubs stop at the same faces, and every CRAH leg/east branch starts at the pipe face. Connectivity is now proved by **box contact** rather than endpoint coincidence and is still a single component per service.

**5. Envelope and scale re‑derived from the pixels.** Tile pitch 5.90 px and grid pitch 70.5 px give **101.5 mm/px**, so the clear hall is **27000 × 24000 mm** (A‑101 px 504–770 × 213–450) with 200 mm walls outside it. The structural grid is now placed at **x = −450+7200k, y = 150+7200k** (both ≡ 150 mod 600), putting the column centres at **6750 / 13950 / 21150 mm** — matching the A‑101 blobs at px 571/642/712 (6800/14000/21200). The sprinkler grid moved to its true module: **2500 mm pitch, origin 1250** (F‑101 65.6 px × 38.09 mm/px).

**6. Rows and headers reach the drawn ends.** All four rows now run to **x = 21 000 mm** (drawn band ends 20.8–21.1 m), with headers to 21 300. The coverage gate now samples **the drawn extents x = 1400…20 800 mm** instead of the model's own rack extents, and still returns **1.000** for all 12 row/service pairs.

**Final state:** IFC4, **0 express‑rule errors**, **0 clashes under the absolute literal rule**, 146 brackets all in contact, 18/18 drop stations chain service → tap → drop → cabinet, 3.8 s, byte‑identical across runs. Counts: 94 racks (27/20/21/26), 104 sprinklers, 9 columns, 6 CRAHs, 6 PDUs, 4 walls, 4 slabs, 3 network assemblies. Lengths: tray 87.3 m, busway 87.8 m, CHW 106.4 m. Files: `output/solution.py`, `output/model.ifc`, `output/reconciliation.json` (31 notes).