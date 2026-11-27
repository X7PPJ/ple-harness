Corrected both files. The 139 °C absolute-temperature guardrail now correctly reads **155.9 min → 156 min** for `T_unexposed_avg_C` (at 155 min the mean is 138.0 °C; at 156 min it is 139.1 °C). The erroneous 93.9 min value, which belongs to `T_unexposed_max_C`, has been removed from both the memo and the worksheet.

**Updated deliverables**

- **`output/CFDME-2025-041_validation_memo_revA.docx`** — 8-page Word memo, DRAFT pending peer review, 13 sections plus Appendices A and B.
- **`output/CFDME-2025-041_validation_crossing_calc_revA.csv`** — 35-row unit-bearing crossing and rollup worksheet.

**Key results unchanged**

The companion simulation **does not validate**:

- **S = 131 min** — single-point analog crossed at 130.9 min.
- **D = 118 min** — RBFMT-25-0918 §5.3.
- **E = +13 min**.
- Acceptance criterion: **11.8 min** (10 % of D).
- Validation uncertainty: **±8.77 min**, reported **±9 min**.
- **|E| exceeds both** — by 1.2 min against the criterion and 4.23 min against the unrounded uncertainty. This is a resolved model error, not scatter.
- Largest prediction clearing the criterion: **129.8 min**, or **129 min or less** in whole minutes.

Geometry: revC conforms to all nine parameters in IWFPE-CERT-25-0374 §1.2. revD is outside the certification and requires an executed change order; panel plan size is a non-certified geometric idealization.

Bianca’s **129 min is inadmissible as D** — no reissued RBFMT-25-0918-R1, no TC-6 calibration certificate, no supersession statement. If substantiated, it would support a 2-hour rating, but only Red Butte and Ironwood can act.

Comparisons: test separation **45 min** versus run **45.2 min**; governing-point excess **≈85 °C** versus **91.2 °C**. The uniform 13 min lag points to a whole-assembly or exposure bias; rework belongs in the companion model and has not been started.

Checklist: **item 6 closed only**; items 2, 3, 4, 5, 7, 9, and 10 remain open.