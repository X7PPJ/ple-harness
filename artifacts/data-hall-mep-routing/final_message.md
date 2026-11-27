All five findings are fixed and the model re-verifies clean.

## Deliverables (regenerated)
- **`output/solution.py`** — 3.35 s, deterministic, no PNG reads.
- **`output/model.ifc`** — IFC4, `express_rules=True` → **0 statements**, 371 elements.
- **`output/reconciliation.json`** — notes, assumptions, clearances, lengths/elevations.

## What changed

**1. `PlenumDepth` sign.** The access-floor slab now carries `PlenumDepth = 700.0` (structural slab top −700 → FFL 0), `PlenumTopBelowFFL = 700`, `PlenumBottom = 0`, `ClearVoidDepth = 670` (to the panel underside). The side file says 700; the only negative number left anywhere is the structural slab's genuine `TopElevation = −700`.

**2. Rack rows follow the drawn A-101 bands, per row.** Cabinets are laid on the drawn 600 mm pitch anchored on *each row's own* drawn west face and are never allowed outside that row's band or across the drawn break (9 660–11 410 mm):

| row | drawn (mm) | model (mm) |
|---|---|---|
| 1 | 1 901–20 231 | **1 901–19 901** (22 racks) |
| 2 | 1 901–19 242 | **1 901–18 701** (21) |
| 3 | 1 825–19 927 | **1 825–19 825** (22) |
| 4 | 1 901–19 470 | **1 901–19 301** (21) |
| 5 | 1 825–19 927 | **1 825–19 825** (21) |
| 6 | 1 901–19 242 | **1 901–18 701** (21) |

No row overruns its drawn east end; west faces match the drawing exactly.

**3. Columns.** I re-examined A-101 (no column symbols between the rack rows — only equipment labels) and A-301 (no interior vertical element between FFL and soffit). The invented 3 × 2 interior grid is **removed**; `reconciliation.json` records "no interior column symbols in plan or section → clear-span hall, no interior columns modelled".

**4. CHW pipe vs insulation.** The pipe solids remain a single conservative envelope, but the contract is now explicit everywhere: `PipeDiameter 168`, `InsulationThickness 25.4`, `OuterDiameter 218.8`, `ModelledSolid "Insulated envelope"`, `ClearanceReference "Insulation outer surface"`, `PipeSurfaceOffset 25.4`; elements named "Chilled water (insulated)". Every reported clearance is given **to both surfaces**: PDU top 640.6 mm (insulation) / **666.0 mm (pipe)**; CRAH top 5.0 mm (insulation) / **30.4 mm (pipe)**; `reconciliation.json` carries `reference: "insulation outer surface"` plus `*_to_pipe_mm` fields.

**5. Sprinkler diagnostics — no sentinel.** `ClearanceTo<svc>_mm` is written only when a run actually passes **below** the deflector; otherwise the pset gets `NearestRun_<svc>_Above_mm` + `<svc>Relation = "above"|"none"` with real distances (e.g. the deck heads: tray 1 785 mm, busway 1 335 mm, CHW 725.6 mm above their 1 915 mm deflectors). These 77 heads now carry measured values instead of `−1.0`, and the IFC psets and `reconciliation.json` come from the same data.

## Verification
0 hard clashes · tray/busway/CHW each 1 connected component reaching its entry · all 6 rows 100 % covered (lateral ≤ 1 400 mm) · 6 CRAHs (4 south at the drawn centres 1 445/10 040/18 710/25 100, 2 north at the drawn unit symbols 22 400/24 606) all reached, 0 mm in plan · headroom 2 605 ≥ 2 600 · worst deflector clearance 600 ≥ 460 · tray/busway 300 · support gaps ≤ 1 487.6 ≤ 1 500 · 3 containment roofs with 7 heads beneath each · 0 orphans. Lengths: tray 68.0 m, busway 67.3 m, CHW 127.7 m (263.0 m total), system psets exactly equal to the sum of segment lengths.