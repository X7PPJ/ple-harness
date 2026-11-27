# Method, verification and corrections — DSR Phase 3 L-series task

**Job 2201-03 · Desert Sage Ranch Phase 3 · TM-22-500041 / IP-26-100288 / FM-26-100290**
Requester: project principal. Deliverable: one memorandum to Callaway for signature, dated **10/31/2026**.

---

## 1. Deliverables and where they are

| # | File | What it is |
|---|---|---|
| D-1 | `Callaway_L-Series_Turf_and_Schedule_Memo_2026-10-31.docx` | Editable master of the memorandum (15 pp. incl. Attachments A–C) |
| D-1 | `Callaway_L-Series_Turf_and_Schedule_Memo_2026-10-31.pdf` | Flat copy of the same document, generated from the DOCX |
| D-2 | `LS-01_L-Series_Reconciliation_and_Schedule_Backup.xlsx` | Five-tab backing workbook: Frontage & Trees (with OK/FAIL check), Turf Classification, Irrigation Demand, Schedule & Critical Path, Source Register |
| D-3 | `drafts/Callaway_L-Series_Turf_and_Schedule_Memo_2026-10-31_DRAFT.md` | The memorandum's text, extracted from the DOCX so it is word-for-word identical |
| — | `_build_memo.py`, `_build_workbook.py`, `_docx_to_md.py` | Build scripts; every figure in D-1 is generated from constants in these scripts or from tab 1–4 of D-2 |

Nothing outside `output/` was created, changed or deleted. The tracker, the estimate, the irrigation worksheet, the landscape sheets, the QA/QC checklist and every source PDF/email are untouched.

## 2. The answer the memorandum carries

**No — 12/18/2026 recordation cannot be committed on this revision, and 11/30/2026 cannot be represented as protecting the map.**

1. **Controlling date 12/23/2026.** NRS 278.360 successive-map rule: two years from recording of the preceding final map, recorded 12/23/2024 (Book 175, Page 60; Instrument No. 20241223-0004421). The 12/18/2026 figure in the tracker is a target with five days of internal margin, not a deadline. The 03/14/2026 reading (Hallenbeck) applies to the first map and is spent; the 03/14/2028 reading (Petrosyan) assumes an extension that is not of record.
2. **11/30 + 20 business days = 12/29/2026**, six days after the statutory date. Only 17 business days separate 11/30 from 12/23 — before bond/SIA, four certificate signatures and Recorder processing.
3. **L-2 and L-4 are substantive.** 208 required vs 58 shown on 4,160 lf = **+150 trees**, average spacing 71.7 ft today vs 20 ft required. The work lands on **Sheet L-2 (plan) and Sheet L-1 (schedule)**; **Sheet L-4 is the entry monument and does not change.** A 30% 15-year shade exhibit is also required (CP-PW-GM-2025-04 §3).
4. **Counsel's 10/20/2026 memo does not close L-2.** WRC-2024-07 makes the carve-out lot-based, expressly covers HOA common-area park parcels regardless of single-family zoning, and §3.1/§4 cannot be satisfied by 0 sf of play-area turf with the amenities VE'd out. The 18,400 sf is nonfunctional turf with a 12/31/2026 deadline.
5. **Condition 14 design review is unavoidable.** The 10/28 cutoff for the 11/18 TAB has passed; next is 12/16 (file by 11/25), followed by the Planning Commission — so no staff-level action before 12/23.
6. **Knock-ons:** irrigation **3.287 → 4.208 ac-ft/yr** (lawn retained, +0.921) or **2.307** (lawn deleted, −0.980) — carried to two decimals as 3.28 / 4.21 / 2.31; estimate **+$45,150 direct** (7.09 +$72,750; 7.16 −$39,560; 7.41 +$11,960), Section 6 $389,340 → ≈$434,500, bond to be re-sealed; B-04 $14,300 needs a supplement; extension application held to file **12/24/2026**.

## 3. Corrections made to the earlier draft of this plan

The staged plan and draft were checked line by line against the source files. Six things were wrong and are corrected in the delivered memorandum:

| # | Earlier position | Verified position | Source |
|---|---|---|---|
| 1 | Cost movement "≈ +$53k", built on adding $7,728 of soil preparation (7.01) for the converted area | **Wrong to add 7.01.** Line 7.01 is an 80,000 sf allowance against 40,600 sf of planted area, and the turf footprint was already in it; converting turf to drip does not create new prepared area. Direct change is **+$45,150**; Section 6 moves to ≈$434,500, with a $445k–$465k range once plant stock/granite and the mow-strip and spray-head credits are priced | `DSR_Ph3_Engineers_Estimate.xlsx` rows 103, 108, 113, 129 |
| 2 | Passive-lawn exclusion attributed to bulletin "§3.3 and §4" | §3.3 is **pet-relief turf**. The passive-lawn exclusions are **§3.2** (athletic use test) and **§4** (waiver limits) | `FunctionalTurf_Compliance_Bulletin.pdf` |
| 3 | Windmill frontage described only as "south frontage" | The sheet and the tabulation use opposite labels for the same 2,560 lf — Sheet L-2 "north frontage, Phase 3 extension" (north side of Windmill Ln.), tabulation "Phase 3 south frontage" (parcel's south boundary). The memo uses a description that reconciles both, and explains the discrepancy in Attachment A | `DSR_Ph3_Landscape_L1-L4.pdf` (L-2); tab "Frontage & Trees" |
| 4 | CCWRD capacity confirmation listed as "to be confirmed current" | **It expired 09/30/2026** — one year from issue — and its terms require written renewal and reissuance before plan approval. Added as a critical-path gate in §6.1 and a 11/02 action | `SewerCapacity_Confirmation_09302025.pdf` §3; Condition 22 |
| 5 | Estimate exposure framed only as a consequence of the design change | The County's Uniform Unit Cost Schedule §7 note (a) says **nonfunctional turf "shall not be included in the engineer's estimate for bonding"** — line 7.16 is not bondable as the record stands under any option. Added to §8 | `CC_Unit_Cost_Schedule.pdf` §7 note (a) |
| 6 | Memo left the 1,192 / 310 / 882 plant-count gap and the 71.7-ft spacing as narrative only | Recomputed and tabulated: 882 of 1,192 scheduled shrubs/accents have no count sheet; current spacing 75.3 / 73.8 / 52.5 ft = 71.7 ft average | Sheet L-1 schedule; L-3 and L-4 counts; Sheet L-2 frontage summary |

Also verified and kept: 64 EA on estimate line 7.09 = 58 street + 6 entry; L-1 schedule CHL 18 + PAR 22 + PBR 18 = 58, PIE 6, ULP 10; 18,400 sf identical on L-1, L-3, the tabulation and estimate 7.16; 4,160/58 totals on Sheet L-2 and the tabulation; title report currency to 01/01/2027; will-serve to 07/22/2028.

## 4. Method

- **Dates:** computed in python (`datetime`), never counted by hand. 12/23/2024 + 2 years = Wed 12/23/2026; 11/30/2026 + 20 business days excluding weekends and 12/25/2026 = Tue 12/29/2026 (12/28 if the receipt day counts as day one — still late); 17 business days from 11/30 to 12/23; TAB 21-day cutoffs 11/18→10/28 and 12/16→11/25; 10-day posting 12/06.
- **Trees:** frontage ÷ 20 at the medium-canopy tier (CC 30.64.030(k) as restated in CP-PW-GM-2025-04 §2), using the sheet's own 2,560 / 1,180 / 420 lengths. No rounding arises.
- **Irrigation:** the worksheet's own rate basis (5.5 ft/yr spray; 1.0 ft/yr drip; 2,000 gal/tree; 43,560 sf/ac; 325,851 gal/ac-ft), recomputed at 224 trees. The 3.28 figure is not carried forward.
- **Money:** unit prices from the 10/10/2026 sealed estimate only ($485, $2.15, $0.65, $0.42), cross-checked to the County schedule.
- **Quotations:** every quoted phrase was checked against the source PDF/email text; see tab 5 of the workbook for the register.

## 5. Checks run before delivery

1. All of `208`, `150`, `4,160`, `71.7`, `4.21`, `2.31`, `3.28`, `0.98`, `1.375`, `12/23/2026`, `12/29/2026`, `11/25/2026`, `12/16/2026`, `$485`, `+$72,750`, `$2.85`, `$52,440`, `18,400`, `882`, `1,192`, `09/30/2026`, `$5,357,000`, `$389,340`, `+$45,150` appear in the PDF and match tabs 1–4 of the workbook.
2. Date logic re-derived independently and reconciled to tab 4; every weekday checked against the TAB calendar.
3. Cross-document counts verified: 64 = 58 + 6 (estimate 7.09), 58 = 18 + 22 + 18 (L-1), 18,400 sf identical on four documents.
4. Text extracted from the DOCX and from the PDF and diffed — identical apart from page furniture.
5. No placeholders (`TBD`, `XX`, bracketed fields) remain; the only underscores are the signature rule.
6. Layout checked with `pdftotext -bbox`: every word sits inside the 1-inch margins on all 15 pages; no table overflows the text block.
7. Nothing outside `output/` was written; source files re-read after the build and unchanged.

## 6. What the memo does **not** do

It does not mark L-2 or L-3 closed; does not adopt counsel's exemption position; does not cite 03/14/2026 or 03/14/2028 as an operative date; does not seal or re-seal any landscape sheet, estimate or worksheet; does not alter the tracker; and was not sent to the County.

## 7. Review corrections incorporated (second pass)

A reviewer pass found seven internal inconsistencies. All seven are fixed in the DOCX, the PDF, the workbook and the markdown.

| # | Issue | Fix |
|---|---|---|
| 1 | §5 said the 20-business-day second-round clock starts after Planning Commission action | Corrected: staff cannot act before design review concludes, but the County's 20-business-day clock runs from receipt of the complete 11/30 resubmittal (consistent with §1's 12/29 computation) |
| 2 | §1 said the calendar and statutory dates are "ten days apart" | Replaced with the actual gaps: target 12/18 is 5 days inside 12/23; the County's review cycle alone runs 6 days past it |
| 3 | §6.1 put a one-week slip at 12/11 with "nine" business days | Corrected to **12/07/2026** and **12 business days** (verified in python); workbook tab 4 row 6 aligned |
| 4 | §6 and §1 bundled "decisions 1–3" as due 11/06, but decision 3 is due 11/10 | §1, §6 and §6.1 now tie each decision to its own date: 1–2 on 11/06, 3 on 11/10, 4 on 11/13, 5 on 12/04; §6 gains a 11/10 row for decision 3 |
| 5 | §8 range said $425k–$465k and the unpriced-adder row included 7.01 | Range corrected to **$445,000–$465,000** ($434,500 + $20,000–$40,000 − up to $9,330); 7.01 removed from the unpriced row, since the 80,000 sf allowance already covers the planted footprint |
| 6 | Attachment C omitted two emails cited in the body | Added the Nokes direction email (10/22/2026, §§1 and 3.1) and the internal design coordination thread (07/28/2026–10/09/2026, §4) — matching rows 17–18 of workbook tab 5 |
| 7 | §3 said "L-1 and L-5 are drafting" | Corrected: L-5 is the drafting comment, L-6 the counting exercise, and L-1 the sealing task — the last step, not the first |

## 8. Second review pass

A second reviewer pass raised six points. All are fixed in the DOCX, the PDF, the workbook and the markdown.

| # | Issue | Fix |
|---|---|---|
| 1 | The Phase 3 park was called "Parcel A" and described as already HOA-owned, but the final map and civil plans designate it Common-Area Parcel **"D"**, and the recorded CC&Rs (Instrument No. 20241223-0004422, Book 175, Page 61) define "Common-Area Park" as Parcel A on the **first** final map — the Phases 1/2 park | §4 now reconciles the labels ("Common-Area Parcel D, called Parcel A on the Phase 3 landscape sheets"), quotes §§2.6, 3.2(c) and 3.3 of the declaration, and states HOA ownership/maintenance as an obligation **to be perfected on recordation** (Condition 16), not a completed conveyance. Attachment B and workbook tabs 2–3 relabelled; the CC&R added to Attachment C and to tab 5 (now 24 documents) |
| 2 | Workbook tab 4 omitted decision 5 (12/04) and put the notice to Comprehensive Planning on 11/10, against §6's 11/06 | Tab 4 rebuilt and now matches §6 row for row — separate 11/06 notice row, 11/10 decision-3 row, 11/13 decision-4 row, new **12/04 decision-5** row — plus the F-1, G-8 and 11/22 rows from item 6 |
| 3 | Irrigation deltas did not reconcile with the rounded totals (+0.92 vs 4.21−3.28 = 0.93) | Attachment B and tab 3 now show the computed totals **3.287 / 4.208 / 2.307** with the rounded form alongside, deltas **+0.921 / −0.980**, and an explicit rounding note explaining the difference against the rounded 3.28 |
| 4 | Attachment C still listed estimate line 7.01, which §8 deliberately excludes | Row now lists 7.02, 7.09, 7.11–7.14, 7.16, 7.17, 7.41 and 7.43 and states that 7.01 is **not** used, with the reason |
| 5 | §5 asserted design review "cannot conclude before 12/23/2026", but no Planning Commission date is of record | Rewritten: "No Planning Commission hearing is scheduled, and the County's review cycle alone ends 12/29/2026"; the §5 table now carries the PC date as "not scheduled — no date appears in the record" and adds a second-round row at 12/29/2026 as the controlling blocker |
| 6 | §6.1's non-landscape gate list omitted open General Comments F-1 and G-8 | Added F-1 (CCFD second access, call 11/10/2026, due 11/22/2026) and G-8 (NDEP NVR100000 NOI, status 11/13/2026, due 11/22/2026), plus a paragraph stating that the other 24 General Comments are being worked to the tracker's 11/22/2026 date and are not re-planned or vouched for here — if any slips, 11/30 slips |

A table-rendering defect found in the same pass was also fixed: the DOCX table helper stripped the first and last two characters of any cell beginning with `**` in a bold row, which truncated the new Attachment B total. The helper now strips bold markers only when a cell both opens and closes with `**`, and the documents were checked for any remaining literal markdown (none).
