Deliverable written: `submission/model.ifc` (IFC4 STEP, 145 entities).

What it contains
- 1 `IfcProject`, 1 `IfcSite` aggregated under the project, and 7 `IfcBuilding`s aggregated under the site.
- Buildings: DH_P1 (phase 1), DH_P2 (phase 2), SUB, CTP, GEN, BRM, RET, each with an extruded `Body`/`SweptSolid` footprint, `DCD_Layout` identity pset, and storeys. Both data halls are 2-storey, height 9.0 m, floor-to-floor 4.5 m, with GFA matching footprint × storeys.
- `DCD_Networks` pset on the `IfcSite`, embedded as an `IfcText` JSON payload with 3 roads, 3 MV networks, and the typed graph (`utility_feed` POI→SUB, `power_feed` SUB→DH_P1, SUB→DH_P2, each with `via`).
- RET is extruded below grade (z −0.3…0, max Z = 0); BERM screens the generator yard from R2 and is 5.4 m high.

Computed design checks (deterministic re-extraction from the IFC)
- Weighted utility cost: **463.25** ≤ 473 (MV 356.3 m; roads 356.5 m).
- Phase 1 weighted cost: **294.15** ≤ 314.
- Noise: **R1 38.14 dB**, **R2 37.44 dB** ≤ 42.35 dB.
- Aggregate building footprint: **11,884.06 m²** ≤ 13,529.6 m².
- Stormwater retention: **2,400 m²** ≥ 1,654.7 m² required.
- All occupied/hazardous structures within 18 m of the connected road network (max access distance 15.21 m).
- GEN is ≥28 m from all occupied structures (min 30.0 m) and screened from both receptors.
- All buildings and roads are >8 m from WET1/WET2; road minimum wetland clearance is 13.04 m.
- Buildings meet the 18 m lot setbacks, minimum areas, aspect limits, and height limits; the IFC structure, units, storeys, psets, and network schema were re-parsed from the final file and checked.