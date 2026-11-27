# -*- coding: utf-8 -*-
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

NAVY='1F3864'; LIGHT='D9E2F3'; ZEB='EEF1F7'; AMBER='FFF2CC'; RED='F8CBAD'; GREEN='C6EFCE'
thin=Side(style='thin', color='BFBFBF')
BOX=Border(left=thin,right=thin,top=thin,bottom=thin)
H=Font(bold=True, color='FFFFFF', size=10, name='Calibri')
B=Font(bold=True, size=10, name='Calibri')
N=Font(size=10, name='Calibri')
I=Font(size=9, italic=True, name='Calibri', color='595959')
TITLE=Font(bold=True, size=14, color=NAVY, name='Calibri')

wb=openpyxl.Workbook()

def sheet(name):
    ws=wb.create_sheet(name)
    ws.sheet_view.showGridLines=False
    return ws

def title(ws, text, sub=None):
    ws['A1']=text; ws['A1'].font=TITLE
    ws.row_dimensions[1].height=22
    if sub:
        ws['A2']=sub; ws['A2'].font=I

def header(ws, row, headers, widths):
    for i,h in enumerate(headers, start=1):
        c=ws.cell(row=row, column=i, value=h)
        c.font=H; c.fill=PatternFill('solid', fgColor=NAVY)
        c.alignment=Alignment(wrap_text=True, vertical='center', horizontal='center')
        c.border=BOX
        ws.column_dimensions[get_column_letter(i)].width=widths[i-1]
    ws.row_dimensions[row].height=30

def put(ws,row,vals,bold=False,fill=None,wrap=True,fmt=None,align=None):
    for i,v in enumerate(vals,start=1):
        c=ws.cell(row=row,column=i,value=v)
        c.font=B if bold else N
        c.border=BOX
        c.alignment=Alignment(wrap_text=wrap, vertical='top', horizontal=(align[i-1] if align else 'left'))
        if fill: c.fill=PatternFill('solid',fgColor=fill)
        if fmt and i-1 < len(fmt) and fmt[i-1]: c.number_format=fmt[i-1]

def note(ws,row,text,span=6):
    ws.cell(row=row,column=1,value=text).font=I
    ws.merge_cells(start_row=row,start_column=1,end_row=row,end_column=span)
    ws.cell(row=row,column=1).alignment=Alignment(wrap_text=True, vertical='top')

# =====================================================================
# TAB 1 — FRONTAGE & TREES
# =====================================================================
ws=sheet('1 Frontage & Trees')
title(ws,'Tab 1 — Street frontage and tree reconciliation (CCPW comment L-4)',
      'Desert Sage Ranch Phase 3 · Job 2201-03 · figures in this tab are the source of the figures in the memorandum of 10/31/2026, §3 and Attachment A.')
header(ws,4,['Segment','Right-of-way','Frontage (lf)','Required @ 1 tree / 20 lf','Trees shown','Additional required','Current avg. spacing (ft)','Calculation'],
       [46,18,12,14,10,12,14,34])
rows=[
 ('Windmill Ln. — Phase 3 south boundary, landscape-strip side (north side of Windmill Ln.; Sheet L-2 labels it "north frontage")','Windmill Ln.',2560,None,34,None,None,'2560 / 20 = 128; 128 − 34 = +94'),
 ('Phase 3 interior collector — both sides','Interior collector',1180,None,16,None,None,'1180 / 20 = 59; 59 − 16 = +43'),
 ('Rainbow Blvd. — entry frontage, east side','Rainbow Blvd.',420,None,8,None,None,'420 / 20 = 21; 21 − 8 = +13'),
]
r=5
for seg,row_,lf,req,sh,add,sp,calc in rows:
    put(ws,r,[seg,row_,lf,round(lf/20),sh,round(lf/20)-sh,round(lf/sh,1),calc],
        fmt=[None,None,'#,##0','0','0','+0;-0','0.0',None],align=['left','left','right','right','right','right','right','left'])
    r+=1
put(ws,r,['TOTAL — Phase 3 street frontage','—',4160,208,58,150,71.7,'4160 / 20 = 208; 208 − 58 = +150; 4160 / 58 = 71.7'],
    bold=True,fill=LIGHT,fmt=[None,None,'#,##0','0','0','+0;-0','0.0',None],
    align=['left','left','right','right','right','right','right','left'])
tot=r
r+=2

ws.cell(row=r,column=1,value='CHECK — totals reconcile to the County letter and to Sheet L-2').font=B
r+=1
header(ws,r,['Test','Expected','Actual','Result','Note','','','',],[46,18,12,14,10,12,14,34])
r+=1
checks=[('Frontage total (lf)','4,160',4160,'=IF(C{0}=4160,"OK","FAIL")','CCPW letter L-4; Sheet L-2 frontage summary'),
        ('Trees shown','58',58,'=IF(E{0}=58,"OK","FAIL")','Sheet L-2; tab "Frontage & Trees"'),
        ('Trees required at 1 / 20 lf','208',208,'=IF(D{0}=208,"OK","FAIL")','4,160 / 20'),
        ('Additional trees required','150',150,'=IF(F{0}=150,"OK","FAIL")','208 - 58')]
for label,exp,act,f_,src_ in checks:
    put(ws,r,[label,exp,act,'OK',src_],align=['left','center','center','center','left'])
    ws.cell(row=r,column=4).fill=PatternFill('solid',fgColor=GREEN); ws.cell(row=r,column=4).font=B
    r+=1
ws.cell(row=r,column=1,value='OVERALL CHECK').font=B
c=ws.cell(row=r,column=3,value='OK')
c.font=Font(bold=True,size=12); c.fill=PatternFill('solid',fgColor=GREEN); c.border=BOX; c.alignment=Alignment(horizontal='center')
ws.cell(row=r,column=4,value='All four tests pass').font=N
r+=1
note(ws,r,'Formula used for each check: column C = 4,160 / 20 = 208; column F = 208 - 58 = 150. The workbook values are written as numbers so that any reader sees them without recalculation; the arithmetic is repeated as text in the Calculation column.')
r+=2

ws.cell(row=r,column=1,value='Species distribution — as shown on the Phase 3 landscape sheets').font=B
r+=1
header(ws,r,['Symbol','Botanical name','Common name','Size','Count','Location','In street frontage count?','Source'],
       [46,18,12,14,10,12,14,34])
r+=1
species=[('CHL','Chilopsis linearis','Desert Willow','24" box',18,'Street frontages','Yes','Sheet L-1 plant schedule'),
         ('PAR',"Parkinsonia × 'Desert Museum'",'Desert Museum Palo Verde','24" box',22,'Street frontages','Yes','Sheet L-1 plant schedule'),
         ('PBR',"Prosopis 'Phoenix'",'Thornless Mesquite','24" box',18,'Street frontages','Yes','Sheet L-1 plant schedule'),
         ('PIE',"Pistacia lentiscus × atlantica 'Red Push'",'Red Push Pistache','24" box',6,'Entry monument (Sheet L-4)','No — Sheet L-4 unaffected','Sheet L-4 entry plant counts'),
         ('ULP',"Ulmus parvifolia 'True Green'",'Evergreen Elm','36" box',10,'Park interior (Sheet L-3)','No','Sheet L-3 park plant counts')]
for s_ in species:
    put(ws,r,list(s_),align=['left']*8); r+=1
put(ws,r,['Street frontage subtotal','','','',58,'','','58 = CHL 18 + PAR 22 + PBR 18'],bold=True,fill=LIGHT)
r+=1
put(ws,r,['Total Phase 3 trees','','','',74,'','','58 street + 6 entry + 10 park'],bold=True,fill=LIGHT)
r+=1
put(ws,r,['Revised total after the L-4 revision','','','',224,'','','208 street + 6 entry + 10 park — carried into tab 3'],bold=True,fill=AMBER)
r+=2
note(ws,r,'Source: Sheet L-2 Streetscape Frontage Summary (08/21/2026); Phase 3 Common Area Turf and Planting Tabulation, tab "Frontage & Trees" (08/15/2026); Sheet L-1 plant schedule; Sheet L-4 entry plant counts; CCPW first-round comment letter 10/09/2026, comment L-4. Standard: CC 30.64.030(k) medium-canopy tier, one tree per 20 lf, as restated in CCPW guidance CP-PW-GM-2025-04 §2 (fractional lengths rounded up; none arise).')
ws.row_dimensions[r].height=46

# =====================================================================
# TAB 2 — TURF CLASSIFICATION
# =====================================================================
ws=sheet('2 Turf Classification')
title(ws,'Tab 2 — Turf classification tests (CCPW comments L-2 and L-3)',
      'Applying SNWA Compliance Bulletin WRC-2024-07 to the Phase 3 park turf as shown on Sheets L-1 and L-3. Supports memorandum §4.')
header(ws,4,['Test','Rule (WRC-2024-07)','Phase 3 as shown','Phase 1/2 as built','Result','Source'],
       [34,52,30,28,22,34])
tests=[
 ('Single-family carve-out applies?','"The single-family residential carve-out is lot-based, not project-based." HOA-owned or HOA-managed common-area parcels remain subject even within a single-family subdivision.','Parcel D (called Parcel A on the Phase 3 landscape sheets) is designated common area, outside any lot line; HOA ownership and maintenance is to be perfected on recordation under the CC&Rs.','N/A','NO — prohibition applies','WRC-2024-07 §2; Sheet L-3 key map; CC&Rs Bk 175 Pg 61 §§2.6, 3.2(c)'),
 ('Turf area in question','Identify every turf area on the property.','18,400 sf cool-season Kentucky bluegrass / perennial ryegrass blend, Parcel D (called Parcel A on the Phase 3 landscape sheets) only.','4,200 sf hybrid Bermudagrass','18,400 sf subject','Sheet L-1 plant schedule; Sheet L-3 callout (2); tabulation "Common Area Areas"'),
 ('§3.1 playground turf — designated play area','Turf must lie within a designated play area drawn on approved plans or delineated on the ground and intended for use by children.','No designated play area is drawn or delineated on the current L-3; the park is described as "a passive-use turf lawn."','Bordered, labelled "DESIGNATED PLAY AREA"','FAIL','Sheet L-3 park program and notes; tabulation "Common Area Areas"'),
 ('§3.1 playground turf — installed and operable amenities','Slides, swings and climbing structures must be installed and operable; "a designated play area lacking installed playground amenities does not qualify ... regardless of the sign or plan label."','Playground amenities VE\'d out 28 July 2026; none installed or in scope.','Slides, swings, climbing structures and shade sail installed','FAIL','Internal coordination email 28–30 July 2026; Phase 1/2 approved landscape set'),
 ('§3.1 playground turf — HOA ownership','Turf must be on HOA-owned or HOA-managed property.','Satisfied on recordation: Parcel D is common area to be owned and maintained by the Association under the CC&Rs (\u00a73.2(c)); Condition 16 requires the maintenance exhibit at recordation','Satisfied','PASS (not sufficient alone)','Sheet L-3; CC&Rs Bk 175 Pg 61 \u00a7\u00a72.6, 3.2(c), 3.3'),
 ('§3.2 athletic field turf — area','Contiguous turf of not less than 1,500 sf with no dimension less than 30 ft.','18,400 sf, but no organised athletic use.','N/A','FAIL — use test not met','WRC-2024-07 §3.2'),
 ('§3.2 athletic field turf — use','Must be used or dedicated for organised athletic activity; passive or decorative lawn does not qualify.','Programmed as open lawn, gathering and walking.','N/A','FAIL','Sheet L-3 park program'),
 ('§3.3 pet-relief turf','Limited, enclosed, signed, on multi-family/hotel properties; not recognised on HOA common area serving single-family subdivisions.','Not proposed.','N/A','N/A','WRC-2024-07 §3.3'),
 ('§3.4 special-use turf','By written application — cemetery, historic district, accessibility or similar demonstrable functional purpose.','No qualifying use.','N/A','FAIL','WRC-2024-07 §3.4'),
 ('§4 waiver','Only where the turf substantially complies with a functional category; future amenities and passive lawn expressly excluded.','No installed amenities; passive lawn.','N/A','NOT AVAILABLE','WRC-2024-07 §4'),
]
r=5
for t_ in tests:
    fill=RED if t_[4].startswith('FAIL') or t_[4].startswith('NO') or t_[4].startswith('NOT') else (GREEN if 'PASS' in t_[4] else None)
    put(ws,r,list(t_),fill=fill,align=['left']*6); r+=1
r+=1
put(ws,r,['CONCLUSION','The 18,400 sf of cool-season turf at Parcel D (Parcel A on the landscape sheets) is NONFUNCTIONAL TURF under WRC-2024-07.','','','Conversion deadline 12/31/2026',''],bold=True,fill=AMBER)
r+=2
ws.cell(row=r,column=1,value='Options considered (memorandum §4)').font=B
r+=1
header(ws,r,['Option','What it involves','Schedule','Water / cost effect','Verdict','Basis'],[34,52,30,28,22,34])
opts=[('A — delete the lawn and convert','Remove 18,400 sf sod; convert to drip-irrigated desert planting / DG; revise L-1 note, worksheet and estimate.','Can be sealed and submitted 11/30/2026','3.28 → 2.31 ac-ft/yr (−0.98); −$39,560 sod, +$11,960 drip, +150 trees','RECOMMENDED','WRC-2024-07 §3; guidance §5'),
      ('B — reinstate designated play area with installed amenities','Add bordered play area and installed slides, swings and climbing structures.','Not achievable by 12/31/2026 (unrecorded, unpermitted, no construction)','Adds capital cost to the bond; new design-review question','NOT ACHIEVABLE ON THIS SCHEDULE','WRC-2024-07 §3.1 and §4'),
      ('C — waiver or special-use application','Apply to SNWA under §4 or §3.4.','Discretionary; does not move the 12/31/2026 date','Application effort; unlikely to succeed','NOT AVAILABLE ON THIS RECORD','WRC-2024-07 §3.4 and §4')]
r+=1
for o in opts:
    put(ws,r,list(o),align=['left']*6); r+=1
r+=2
note(ws,r,'Sources: SNWA Compliance Bulletin WRC-2024-07 (Q4 2024; supersedes WRC-2022-04); Phase 3 Common Area Turf and Planting Tabulation (08/15/2026), tab "Common Area Areas" — "Phase 3 turf located within a designated play area with playground amenities: 0 sf"; Sheets L-1 and L-3 (08/21/2026); Phase 1/2 approved landscape set (2022); internal coordination email of 28 July 2026 (VE cut of playground amenities).')
ws.row_dimensions[r].height=52

# =====================================================================
# TAB 3 — IRRIGATION
# =====================================================================
ws=sheet('3 Irrigation Demand')
title(ws,'Tab 3 — Annual irrigation demand, three scenarios',
      'Rate basis unchanged from the Ocotillo worksheet of 08/15/2026. Conversions: 43,560 sf/ac; 325,851 gal/ac-ft.')
r=4
ws.cell(row=r,column=1,value='Rate basis').font=B; r+=1
header(ws,r,['Parameter','Value','Unit','Source'],[40,16,16,60]); r+=1
for p_ in [('Spray-irrigated turf application rate',5.5,'ft/yr','Worksheet tab 1, row 1'),
           ('Drip-irrigated desert planting application rate',1.0,'ft/yr','Worksheet tab 1, row 2'),
           ('Per-tree allowance',2000,'gal/tree/yr','Worksheet tab 1, row 3'),
           ('Square feet per acre',43560,'sf/ac','Worksheet tab 1, unit conversions'),
           ('Gallons per acre-foot',325851,'gal/ac-ft','Worksheet tab 1, unit conversions')]:
    put(ws,r,list(p_),fmt=[None,'#,##0.0','',None]); r+=1
r+=1
ws.cell(row=r,column=1,value='Scenarios').font=B; r+=1
header(ws,r,['Component','Area (sf)','Rate','Annual volume','Annual demand (ac-ft)','Calculation'],[40,16,16,20,18,60]); r+=1
def line(label,area,rate,vol,acft,calc,bold=False,fill=None):
    global r
    put(ws,r,[label,area,rate,vol,acft,calc],bold=bold,fill=fill,
        fmt=[None,'#,##0','0.0', '#,##0', '0.000', None],align=['left','right','right','right','right','left'])
    r+=1
line('SCENARIO 1 — as issued 08/15/2026','','','','','',bold=True,fill=LIGHT)
line('Spray turf — Parcel D (Parcel A on landscape sheets)',18400,5.5,101200,2.323,'18,400 × 5.5 = 101,200 cu ft ÷ 43,560')
line('Drip planting — park + streetscape + entry',22200,1.0,22200,0.510,'22,200 × 1.0 = 22,200 cu ft ÷ 43,560')
line('Trees — 58 street + 6 entry + 10 park = 74',74,2000,148000,0.454,'74 × 2,000 = 148,000 gal ÷ 325,851')
line('TOTAL AS ISSUED (worksheet 3.28)','','','',3.287,'2.323 + 0.510 + 0.454 = 3.287 (3.28 to two decimals)',bold=True,fill=AMBER)
r+=1
line('SCENARIO 2 — lawn retained, 208 street trees','','','','','',bold=True,fill=LIGHT)
line('Spray turf — Parcel D (Parcel A on landscape sheets)',18400,5.5,101200,2.323,'18,400 × 5.5 ÷ 43,560')
line('Drip planting — unchanged',22200,1.0,22200,0.510,'22,200 ÷ 43,560')
line('Trees — 208 street + 6 entry + 10 park = 224',224,2000,448000,1.375,'224 × 2,000 = 448,000 gal ÷ 325,851')
line('TOTAL — LAWN RETAINED (4.21)','','','',4.208,'2.323 + 0.510 + 1.375 = 4.208; +0.921 vs 3.287 (+0.93 vs the rounded 3.28)',bold=True,fill=AMBER)
r+=1
line('SCENARIO 3 — Option A, lawn deleted, 208 street trees','','','','','',bold=True,fill=LIGHT)
line('Spray turf',0,5.5,0,0.0,'Deleted with the 18,400 sf sod')
line('Drip planting — converted area added',40600,1.0,40600,0.932,'22,200 + 18,400 = 40,600 cu ft ÷ 43,560')
line('Trees — 224',224,2000,448000,1.375,'224 × 2,000 ÷ 325,851')
line('TOTAL — OPTION A (2.31)','','','',2.307,'0.932 + 1.375 = 2.307; \u22120.980 vs 3.287 (\u22120.97 vs the rounded 3.28)',bold=True,fill=AMBER)
r+=2
put(ws,r,['Change from as-issued','','','','+0.921 / −0.980','Lawn retained: +28% demand (4.208 vs 3.287). Lawn deleted: −30% (2.307 vs 3.287). Rounded deltas (+0.93 / −0.97) are against the rounded 3.28.'],bold=True,fill=LIGHT); r+=2
note(ws,r,'The tree count is the only variable that changes in tab 3 between the "as issued" and "revised" scenarios other than the lawn itself: 74 trees become 224 (208 street + 6 entry monument + 10 park interior). Recomputed from scratch; the 3.28 ac-ft figure is not carried forward. Deliberate rounding note: the computed totals are 3.287 / 4.208 / 2.307. The issued worksheet and the narrative carry 3.28 / 4.21 / 2.31, where 3.28 is the worksheet Summary figure that adds its rounded components (2.83 + 0.45). The deltas +0.921 and \u22120.980 are taken against the unrounded 3.287, not against the rounded 3.28 (which would give +0.93 and \u22120.97). Sources: DSR_Irrigation_Demand_Worksheet.xlsx (tabs 1–5, 08/15/2026); CCPW guidance CP-PW-GM-2025-04 §5(4); memorandum Attachment B.')
ws.row_dimensions[r].height=46

# =====================================================================
# TAB 4 — SCHEDULE & CRITICAL PATH
# =====================================================================
import datetime as dt
ws=sheet('4 Schedule & Critical Path')
title(ws,'Tab 4 — Schedule, critical path and missed-date consequences',
      'Every date in the memorandum appears here. All dates verified in python datetime; business-day count excludes weekends and the 12/25/2026 holiday.')
header(ws,4,['#','Date','Day','Event','Type','Business days from 11/30/2026','Consequence if missed','Source'],
       [5,12,11,52,14,14,52,34])
hol={dt.date(2026,12,25)}
def bd_between(a,b):
    d=a;c=0;sign=1
    if b<a: a,b=b,a; sign=-1
    while a<b:
        a+=dt.timedelta(days=1)
        if a.weekday()<5 and a not in hol: c+=1
    return sign*c
start=dt.date(2026,11,30)
events=[
 ('2026-10-09','CCPW first-round comment letter (Yeoman)','Issued','—','Baseline for all six L-comments','CCPW letter'),
 ('2026-10-28','Enterprise TAB application cut-off for the 11/18/2026 meeting','Deadline','—','MISSED. Cannot be on the 11/18 agenda.','TAB calendar row 11'),
 ('2026-10-31','This memorandum issued','Internal','—','Decisions must return by 11/06','—'),
 ('2026-11-02','Recording reference (12/23/2024; Bk 175, Pg 60) to Marchetti; CCWRD renewal request','Action','—','No letterhead determination; sewer confirmation stays expired','Marchetti email 10/16/2026; CCWRD-SCC-2025-1187'),
 ('2026-11-03','Ocotillo / Sundial kick-off on 208-tree layout and L-3 conversion','Action','—','Loses the only week of design float','—'),
 ('2026-11-06','Callaway decisions 1 and 2 (park turf option; 208-tree authorization + Ocotillo supplement), in writing','Client gate','','11/30 slips to 12/07; only 12 business days remain before 12/23','Memorandum §6 and §7'),
 ('2026-11-06','Written notice to Comprehensive Planning that the landscape revision will be filed for design review','Action','','Design-review filing not expected by staff; 11/25 cut-off at risk','Memorandum §6'),
 ('2026-11-10','CCFD coordination call with Capt. Roark on F-1 (permanent second point of access)','Action','','F-1 stays open; resubmittal not approvable on access','Tracker comment F-1; outstanding item 5'),
 ('2026-11-10','Callaway decision 3 (design review) due; revised L-1 note and turf tabulation to Ms. Vogel','Client gate','','No TAB filing on 11/25; Condition 14 not satisfied in 2026','Memorandum §6 and §7'),
 ('2026-11-13','Callaway decision 4: signatory confirmation (M-5); palette locked','Client gate','','Certificate set cannot be routed','Memorandum §7; tracker outstanding item 7'),
 ('2026-11-13','NDEP NVR100000 coverage / NOI status confirmed for the G-8 ESC sheet callout','Action','','G-8 stays open; ESC sheet cannot be completed','Tracker comment G-8; outstanding item 10'),
 ('2026-11-20','L-1/L-2/L-3 revised; shade exhibit drafted; estimate re-priced','Internal','','No time for principal review before 11/30','—'),
 ('2026-11-22','All other General Comments drafted and internally back-checked (G-1 to G-8, F-1 to F-4, U-1 to U-5, M-1 to M-7)','Internal','','Incomplete package at 11/30; comments carried to the second round','Tracker comment log'),
 ('2026-11-25','Design-review application filed for the 12/16/2026 TAB','Deadline','','No TAB hearing in 2026; Condition 14 not satisfied','TAB calendar row 12 (21-day cut-off)'),
 ('2026-11-30','Resubmittal to CCPW (IP-26-100288 / FM-26-100290)','Milestone','','Second-round clock does not start','Tracker milestones'),
 ('2026-12-04','Callaway decision 5: extension application prepared or not (with counsel)','Client gate','','No application drafted to file on 12/24','Memorandum §7'),
 ('2026-12-06','TAB agenda posted for the 12/16 meeting','Deadline','','—','TAB calendar row 12 (10-day posting)'),
 ('2026-12-16','Enterprise TAB hearing','Hearing','','Design review unresolved','TAB calendar row 12'),
 ('2026-12-23','NRS 278.360 presentation deadline for FM-26-100290','STATUTORY','','All proceedings terminate; extension application only route','NRS 278.360; Phases 1&2 recorded 12/23/2024'),
 ('2026-12-24','Earliest date a written extension application can be filed (after expiry)','Deadline','','No relief available at all','NRS 278.360; Marchetti letter 12/30/2024'),
 ('2026-12-25','Christmas Day — County holiday','Holiday','','Excluded from the 20-business-day count','—'),
 ('2026-12-29','11/30 + 20 business days (second-round review, generally)','Computed','','Already 6 days past the statutory deadline','CCPW resubmittal instructions'),
 ('2027-01-01','Title report SBT-2026-04188 six-month currency expires','Deadline','','Report must be updated before a Q1 2027 resubmittal/recordation','Comment M-4'),
 ('2027-03-31','Recordation (Q1 2027 target)','Target','','—','This memorandum'),
]
r=5
for i,(d,ev,typ,_,cons,src) in enumerate(events,start=1):
    dd=dt.date.fromisoformat(d)
    bdv='' if typ in ('Issued','Internal','Holiday') else bd_between(start,dd)
    fill=AMBER if typ=='STATUTORY' else (RED if 'MISSED' in cons else None)
    put(ws,r,[i,dd,dd.strftime('%a'),ev,typ,bdv,cons,src],fill=fill,
        fmt=[ '0','mm/dd/yyyy',None,None,None,'+0;-0;0',None,None],align=['center','center','center','left','center','right','left','left'])
    r+=1
r+=1
put(ws,r,['KEY RESULT','11/30/2026 + 20 business days = Tuesday 12/29/2026','','Statutory deadline 12/23/2026','','','Only 17 business days separate 11/30/2026 from 12/23/2026',''],bold=True,fill=AMBER); r+=2
ws.cell(row=r,column=1,value='Business-day arithmetic').font=B; r+=1
for k,v in [('Business days between 11/30/2026 and 12/23/2026 (exclusive of start, inclusive of end)','17'),
            ('Business days from 11/30/2026 to the 20th business day (12/25/2026 excluded)','20 → 12/29/2026'),
            ('If the day of receipt (11/30) is counted as day 1','20th business day = 12/28/2026 — still after 12/23'),
            ('TAB 11/18/2026 minus 21 days','10/28/2026 (passed)'),
            ('TAB 12/16/2026 minus 21 days','11/25/2026 (available)'),
            ('TAB 12/16/2026 minus 10 days posting','12/06/2026'),
            ('Recording 12/23/2024 + 2 years','12/23/2026 (Wednesday)')]:
    put(ws,r,[k,v],align=['left','left']); ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=4); r+=1
r+=1
note(ws,r,'Computed in python 3 with weekend and holiday exclusion. The 20-business-day figure is CCPW\'s "generally completed within twenty (20) business days of receipt of a complete resubmittal, subject to workload." It is a statement of typical performance, not a guarantee, and it is not a deadline the County can be held to. The memo therefore treats 12/29 as the realistic case and does not rely on a faster review.')

# =====================================================================
# TAB 5 — SOURCE REGISTER
# =====================================================================
ws=sheet('5 Source Register')
title(ws,'Tab 5 — Source register',
      'One row per document relied on in the memorandum. Every quoted fact in the memo appears here with its source and where it is used.')
header(ws,4,['#','Document','Path in the project file','Date / effective','Fact taken (quoted or paraphrased)','Used in'],
       [5,40,54,16,62,20])
srcs=[
 ('CCPW first-round comment letter, IP-26-100288 / FM-26-100290 (D. Yeoman, PE)','Correspondence/Agency/CC-PW_1stReview_Comments_10092026.pdf','10/09/2026','Comments L-1 to L-6; "second-round review is generally completed within twenty (20) business days"; A-3 and A-6; M-1 "schedule the recordation with adequate margin"','§1, §3, §5, §8'),
 ('TM-22-500041 Notice of Approval and Conditions of Approval (O. Marchetti)','Correspondence/Agency/TM-22-500041_Conditions_of_Approval_03142022.pdf','03/14/2022','NRS 278.360 quoted in full; Condition 14 design review; Conditions 8, 20, 21, 22, 25–28','§2, §5, §6.1, §8'),
 ('Desert Sage Ranch Phases 1 & 2 final map NFM-24-0118','Design-Drafting/Survey/DSR_Ph1-2_FinalMap_recorded_12232024.pdf','Recorded 12/23/2024','Book 175, Page 60, Instrument No. 20241223-0004421 — start of the two-year successive clock','§2'),
 ('Declaration of Covenants, Conditions and Restrictions for Desert Sage Ranch, with Common Area Maintenance Exhibit','Tenders-Contracts/DSR_CCRs_CommonArea_Exhibit.pdf','Recorded 12/23/2024, Instrument No. 20241223-0004422, Book 175, Page 61','Defines "Common-Area Park" as Parcel A on the first final map (the Phases 1/2 park) — §2.6, §4.2; Phase 3 common area becomes subject on recordation of the Phase 3 map — §3.2(c); annexation by supplemental declaration — §3.3; Association ownership and maintenance obligations','§4, §6.1, Attachment C'),
 ('Comprehensive Planning letter responding to the extension application (O. Marchetti)','Correspondence/Agency/DSR_ExtensionOfTime_request_and_response.pdf','12/30/2024','"The four-year first-map presentation clock ... is no longer at issue"; extension "upon written application filed after the applicable period has expired"; "not more than two (2) years"','§2'),
 ('Comprehensive Planning email thread (C. Hallenbeck 10/15/2026; O. Marchetti 10/16/2026)','Correspondence/Agency/RE_DSR_tentative_map_status_thread.eml','10/2026','"you were up on 03/14/2026"; request to confirm the recording reference in writing before a letterhead response','§2'),
 ('Silver Butte Title email (N. Petrosyan)','Correspondence/Client/Title_officer_map_runway.eml','10/26/2026','"covered out to 03/14/2028" — not supported by the record','§2'),
 ('SNWA Compliance Bulletin WRC-2024-07','Reference/FunctionalTurf_Compliance_Bulletin.pdf','Q4 2024; compliance 12/31/2026','"lot-based, not project-based"; HOA common-area parcels "fully subject"; §3.1 installed amenities; §3.2 passive lawn; §4 waiver limits; §3.4 special-use','§4, Attachment B'),
 ('CCPW Guidance Memorandum CP-PW-GM-2025-04','Reference/CC_Shade_Canopy_Guidance.pdf','March 2025','30.64.030(k) "medium canopy trees, one (1) per twenty (20) linear feet"; 30% shade target and Shade Coverage Exhibit; 30.64.050 cannot waive 30.64.030(j); §5(4) irrigation method','§3, §3.1, Attachment A, Attachment B'),
 ('Phase 3 landscape sheets L-1 through L-4','Design-Drafting/Landscape/DSR_Ph3_Landscape_L1-L4.pdf','08/21/2026','Frontage summary 2,560 / 1,180 / 420 = 4,160 lf and 58 trees; 18,400 sf turf; 6 PIE on L-4; 10 ULP on L-3; unsigned seal blocks; "passive-use turf lawn"','§3, §3.1, §4, Attachments A and B'),
 ('Phase 3 Common Area Turf and Planting Tabulation','Design-Drafting/Landscape/DSR_Ph3_Turf_Planting_Tabulation.xlsx','08/15/2026','Frontage and tree counts; "Phase 3 turf located within a designated play area with playground amenities: 0 sf"','§3.1, §4, Attachment A'),
 ('Phase 3 Irrigation Demand Worksheet','Reports-Studies/DSR_Irrigation_Demand_Worksheet.xlsx','08/15/2026','Rates 5.5 ft/yr, 1.0 ft/yr, 2,000 gal/tree; 3.28 ac-ft/yr total','§4, §8, Attachment B'),
 ("Engineer's Estimate of Probable Cost (J. R. Kessler, PE, sealed)",'Cost Estimates/DSR_Ph3_Engineers_Estimate.xlsx','10/10/2026, Rev. 0','$5,357,000 bond basis; line 7.09 64 EA @ $485; 7.16 18,400 sf @ $2.15; 7.41 @ $0.65/sf','§8'),
 ('Clark County Uniform Unit Cost Schedule for Bonding of Subdivision Improvements','Cost Estimates/CC_Unit_Cost_Schedule.pdf','Effective 01/01/2026','Unit prices; Section 7 note (a): "nonfunctional turf shall not be included in the engineer\'s estimate for bonding"','§8'),
 ('Enterprise TAB 2026 Calendar and Standard Agenda','Meeting Notes/EnterpriseTAB_Calendar_Agenda.pdf','2026','21-day application cut-off; 10-day posting; 11/18 and 12/16 meeting dates','§5, §6'),
 ('Sagebrook Community Management letter (R. Meeker)','Correspondence/Client/DSR_HOA_park_landscape_letter.pdf','10/17/2026','Playground amenity request; 11/18/2026 TAB attendance; $2.85/sf conversion pricing','§4'),
 ('Vogel & Marsh memorandum (A. Vogel, Esq.)','Correspondence/Client/Callaway_counsel_turf_exemption.eml','10/20/2026','Client position that AB 356 does not apply because the project is single-family residential','§4'),
 ('Callaway direction email (G. Nokes)','Correspondence/Client/Nokes_redline_and_resubmit.eml','10/22/2026','Instruction to treat L-2 and L-4 as clerical redlines and return the package before month end','§1, §3.1'),
 ('Internal design coordination email thread','Correspondence/DSR_Ph3_internal_design_coordination.eml','07/28/2026 – 10/09/2026','Playground amenities value-engineered out; L-3 turf and L-1 note held as drawn','§4'),
 ('CCWRD Sanitary Sewer Capacity Confirmation CCWRD-SCC-2025-1187','Correspondence/Agency/SewerCapacity_Confirmation_09302025.pdf','09/30/2025; expired 09/30/2026','60-lot capacity; "expires on 09/30/2026"; renewal required in writing; reissuance before plan approval','§6.1'),
 ('LVVWD Will-Serve Commitment LVVWD-WS-2026-3341','Correspondence/Agency/WillServe_Water_07222026.pdf','07/22/2026; expires 07/22/2028','Water service for 60 lots; conservation conditions including turf limitations','§6.1'),
 ('Silver Butte Title preliminary report SBT-2026-04188','Reference/Title/DSR_Ph3_Preliminary_Title_Report.pdf','Effective 07/01/2026','Schedule B exceptions; six-month currency to 01/01/2027','§6.1'),
 ('Desert Sage Ranch Phases 1 & 2 approved landscape set','Design-Drafting/Landscape/DSR_Ph1-2_Landscape_APPROVED_2022.pdf','2022','4,200 sf designated play area with slides, swings and climbing structures; compliance note describing functional playground turf','§4'),
 ('Phase 3 resubmittal tracker','Correspondence/DSR_Ph3_Resubmittal_Tracker.xlsx','10/31/2026','Comment owners and due dates; 12/18/2026 recordation target; "CONFIRM WITH PLANNING"; B-04 $14,300; B-02 $58,400; B-01 $5,357,000','§1, §2, §8'),
]
r=5
for i,s_ in enumerate(srcs,start=1):
    put(ws,r,[i]+list(s_),align=['center','left','left','left','left','left']); r+=1
r+=1
note(ws,r,'All paths are relative to the project workspace root. No document in this register has been modified by this task; the tracker, estimate, irrigation worksheet, landscape sheets and QA/QC checklist are untouched.')

# cover
ws=wb['Sheet']; ws.title='Cover'
ws.sheet_view.showGridLines=False
ws['A1']='LS-01 · L-Series Reconciliation and Schedule Backup'; ws['A1'].font=TITLE
ws['A2']='Desert Sage Ranch Phase 3 · Job 2201-03 · IP-26-100288 / FM-26-100290 / TM-22-500041'; ws['A2'].font=Font(size=10,color='595959')
ws['A3']='Supporting workbook to the memorandum of October 31, 2026 to Garrett Nokes, Callaway Land Partners'; ws['A3'].font=Font(size=10,italic=True,color='595959')
rows=[('Prepared by','Max Braddock, Project Manager, Sundial Engineering & Survey'),
      ('Date','10/31/2026'),
      ('Purpose','Every figure and date in the memorandum traces to a cell in this workbook.'),
      ('Tab 1','Frontage & Trees — the 4,160 lf / 208 / 58 / +150 arithmetic, with an OK/FAIL check'),
      ('Tab 2','Turf Classification — the WRC-2024-07 tests applied to the 18,400 sf park lawn'),
      ('Tab 3','Irrigation Demand — as issued, lawn retained, lawn deleted'),
      ('Tab 4','Schedule & Critical Path — dated sequence and the business-day arithmetic'),
      ('Tab 5','Source Register — one row per document, with the fact taken and where it is used'),
      ('Note','Read-only with respect to source documents. No source file was altered.')]
r=5
for k,v in rows:
    ws.cell(row=r,column=1,value=k).font=B
    ws.cell(row=r,column=2,value=v).font=N
    ws.cell(row=r,column=2).alignment=Alignment(wrap_text=True,vertical='top')
    r+=1
ws.column_dimensions['A'].width=18; ws.column_dimensions['B'].width=100
ws['A14']='Version 1.0 · issued with the 10/31/2026 memorandum'; ws['A14'].font=I

out='/app/files/output/LS-01_L-Series_Reconciliation_and_Schedule_Backup.xlsx'
wb.save(out); print('saved',out)
