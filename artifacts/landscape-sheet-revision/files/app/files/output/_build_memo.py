# -*- coding: utf-8 -*-
import re, datetime as dt
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

NAVY = RGBColor(0x1F,0x38,0x64)
GREY = RGBColor(0x59,0x59,0x59)
DARK = RGBColor(0x1A,0x1A,0x1A)
RED  = RGBColor(0x9C,0x1B,0x1B)

doc = Document()

# ---------- page setup ----------
sec = doc.sections[0]
sec.page_width  = Inches(8.5)
sec.page_height = Inches(11)
sec.left_margin = sec.right_margin = Inches(1.0)
sec.top_margin = Inches(0.85)
sec.bottom_margin = Inches(0.85)
sec.header_distance = Inches(0.45)
sec.footer_distance = Inches(0.45)

# ---------- base styles ----------
st = doc.styles['Normal']
st.font.name = 'Calibri'
st.font.size = Pt(10)
st.font.color.rgb = DARK
st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
st.paragraph_format.space_after = Pt(5)
st.paragraph_format.space_before = Pt(0)
st.paragraph_format.line_spacing = 1.05

for nm, sz in (('Heading 1',13),('Heading 2',11.5)):
    h = doc.styles[nm]
    h.font.name='Calibri'; h.font.size=Pt(sz); h.font.bold=True; h.font.color.rgb=NAVY
    h.paragraph_format.space_before=Pt(13 if nm=='Heading 1' else 9)
    h.paragraph_format.space_after=Pt(4)
    h.paragraph_format.keep_with_next=True

lb = doc.styles['List Bullet']
lb.font.name='Calibri'; lb.font.size=Pt(10)
lb.paragraph_format.space_after=Pt(3)
lb.paragraph_format.line_spacing=1.05

# ---------- helpers ----------
def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement('w:shd'); sh.set(qn('w:val'),'clear'); sh.set(qn('w:color'),'auto'); sh.set(qn('w:fill'),hexcolor)
    tcPr.append(sh)

def cell_margins(table, top=40, bottom=40, left=80, right=80):
    tblPr = table._tbl.tblPr
    mar = OxmlElement('w:tblCellMar')
    for side,val in (('top',top),('left',left),('bottom',bottom),('right',right)):
        e = OxmlElement('w:'+side); e.set(qn('w:w'),str(val)); e.set(qn('w:type'),'dxa'); mar.append(e)
    tblPr.append(mar)

def set_borders(table, color='BFBFBF', sz='4'):
    tblPr = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV'):
        e = OxmlElement('w:'+edge)
        e.set(qn('w:val'),'single'); e.set(qn('w:sz'),sz); e.set(qn('w:space'),'0'); e.set(qn('w:color'),color)
        borders.append(e)
    tblPr.append(borders)

def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    e = OxmlElement('w:tblHeader'); e.set(qn('w:val'),'true'); trPr.append(e)

def no_split(row):
    trPr = row._tr.get_or_add_trPr()
    e = OxmlElement('w:cantSplit'); e.set(qn('w:val'),'true'); trPr.append(e)

def rich(p, text, size=None, color=None, italic=False):
    """**bold** and _italic_ inline."""
    tokens = re.split(r'(\*\*.+?\*\*|__.+?__)', text)
    for t in tokens:
        if not t: continue
        bold=False; ital=False
        if t.startswith('**') and t.endswith('**') and len(t)>4:
            t=t[2:-2]; bold=True
        elif t.startswith('__') and t.endswith('__') and len(t)>4:
            t=t[2:-2]; ital=True
        r = p.add_run(t)
        r.bold=bold; r.italic=(ital or italic)
        if size: r.font.size=Pt(size)
        if color: r.font.color.rgb=color
    return p

def body(text, size=None, space_after=6, align=None, color=None, italic=False, keep=False):
    p = doc.add_paragraph()
    rich(p, text, size=size, color=color, italic=italic)
    p.paragraph_format.space_after = Pt(space_after)
    if align: p.alignment = align
    if keep: p.paragraph_format.keep_with_next = True
    return p

def bullet(text, size=None):
    p = doc.add_paragraph()
    r = p.add_run('\u2022   ')
    r.font.size = Pt(size if size else 10)
    r.font.color.rgb = NAVY
    r.bold = True
    rich(p, text, size=size)
    p.paragraph_format.left_indent = Inches(0.30)
    p.paragraph_format.first_line_indent = Inches(-0.20)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.03
    return p

def numbered(text, size=None):
    p = doc.add_paragraph(style='List Number')
    rich(p, text, size=size)
    p.paragraph_format.left_indent = Inches(0.30)
    p.paragraph_format.first_line_indent = Inches(-0.20)
    p.paragraph_format.space_after = Pt(4)
    return p

def table(headers, rows, widths, font=9, header_fill='1F3864', zebra='EEF1F7', bold_rows=(), align_right=(), center=()):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    set_borders(t); cell_margins(t)
    hdr = t.rows[0]
    repeat_header(hdr)
    for i,h in enumerate(headers):
        c = hdr.cells[i]
        c.width = Inches(widths[i])
        c.text = ''
        p = c.paragraphs[0]
        r = p.add_run(h); r.bold=True; r.font.size=Pt(font); r.font.color.rgb=RGBColor(0xFF,0xFF,0xFF)
        p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.0
        shade(c, header_fill)
        if i in center: p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for ri,row in enumerate(rows):
        cells = t.add_row().cells
        no_split(t.rows[-1])
        for i,val in enumerate(row):
            cells[i].width = Inches(widths[i])
            cells[i].text = ''
            p = cells[i].paragraphs[0]
            txt = '' if val is None else str(val)
            bold = (ri in bold_rows) or (txt.startswith('**') and txt.endswith('**'))
            if txt.startswith('**') and txt.endswith('**') and len(txt) > 4:
                txt = txt[2:-2]
            rich(p, txt, size=font)
            if bold:
                for r in p.runs: r.bold=True
            p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.0
            if i in align_right: p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if i in center: p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if zebra and ri % 2 == 1: shade(cells[i], zebra)
    # enforce widths on grid
    tbl = t._tbl
    grid = tbl.tblGrid
    for i,gc in enumerate(grid.findall(qn('w:gridCol'))):
        gc.set(qn('w:w'), str(int(widths[i]*1440)))
    return t

def hr(space_before=2, space_after=8, color='1F3864', sz=8):
    p = doc.add_paragraph()
    p.paragraph_format.space_before=Pt(space_before); p.paragraph_format.space_after=Pt(space_after)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    b = OxmlElement('w:bottom'); b.set(qn('w:val'),'single'); b.set(qn('w:sz'),str(sz)); b.set(qn('w:space'),'1'); b.set(qn('w:color'),color)
    pBdr.append(b); pPr.append(pBdr)

def field_run(p, instr):
    r = p.add_run()
    f1 = OxmlElement('w:fldChar'); f1.set(qn('w:fldCharType'),'begin')
    it = OxmlElement('w:instrText'); it.set(qn('xml:space'),'preserve'); it.text = instr
    f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'),'separate')
    t = OxmlElement('w:t'); t.text='1'
    f3 = OxmlElement('w:fldChar'); f3.set(qn('w:fldCharType'),'end')
    r._r.append(f1); r._r.append(it); r._r.append(f2); r._r.append(t); r._r.append(f3)
    return r

def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ---------- running header / footer ----------
hp = sec.header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = hp.add_run('Callaway Land Partners · Desert Sage Ranch Phase 3 · L-series revision and schedule · October 31, 2026')
r.font.size=Pt(7.5); r.font.color.rgb=GREY
sec.different_first_page_header_footer = True
def build_footer(par):
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = par.add_run('Sundial Engineering & Survey · Job 2201-03 · Page ')
    r.font.size=Pt(7.5); r.font.color.rgb=GREY
    field_run(par,' PAGE ')
    r = par.add_run(' of '); r.font.size=Pt(7.5); r.font.color.rgb=GREY
    field_run(par,' NUMPAGES ')
build_footer(sec.footer.paragraphs[0])
build_footer(sec.first_page_footer.paragraphs[0])

# =====================================================================
# LETTERHEAD
# =====================================================================
p = doc.add_paragraph(); p.paragraph_format.space_after=Pt(0)
r = p.add_run('SUNDIAL ENGINEERING & SURVEY'); r.bold=True; r.font.size=Pt(19); r.font.color.rgb=NAVY
p2 = doc.add_paragraph(); p2.paragraph_format.space_after=Pt(0)
r = p2.add_run('Civil Engineering · Land Surveying · Land Planning')
r.font.size=Pt(8); r.font.color.rgb=GREY
p3 = doc.add_paragraph(); p3.paragraph_format.space_after=Pt(0)
r = p3.add_run('4720 South Rainbow Boulevard, Suite 210 · Las Vegas, Nevada 89103 · (702) 555-0142 · NV COA #C-3874')
r.font.size=Pt(8); r.font.color.rgb=GREY
hr(space_before=4, space_after=10, color='1F3864', sz=12)

p = doc.add_paragraph(); p.paragraph_format.space_after=Pt(8)
r = p.add_run('MEMORANDUM'); r.bold=True; r.font.size=Pt(14); r.font.color.rgb=NAVY
r.font.name='Calibri'

hdr_rows = [
 ('To','Garrett Nokes, Vice President — Land Development, Callaway Land Partners'),
 ('From','Max Braddock, Project Manager, Sundial Engineering & Survey'),
 ('Cc','Adrienne Vogel, Esq., Vogel & Marsh LLP\nJonathan R. Kessler, PE, Principal-in-Charge, Sundial Engineering & Survey'),
 ('Date','**October 31, 2026**'),
 ('Re','Desert Sage Ranch Phase 3 — the L-series street tree and turf revision: can Sundial commit to the 11/30/2026 resubmittal and the 12/18/2026 recordation on this revision, and what has to happen first?'),
 ('Job','2201-03  ·  TM-22-500041 / IP-26-100288 / FM-26-100290'),
 ('Response requested by','**Friday, November 6, 2026**'),
]
t = doc.add_table(rows=0, cols=2)
t.autofit=False
set_borders(t, color='FFFFFF', sz='2'); cell_margins(t, top=20, bottom=20, left=0, right=110)
for k,v in hdr_rows:
    cells = t.add_row().cells
    cells[0].width=Inches(1.88); cells[1].width=Inches(4.62)
    p0 = cells[0].paragraphs[0]; r0=p0.add_run(k); r0.bold=True; r0.font.size=Pt(9.5); r0.font.color.rgb=NAVY
    p0.paragraph_format.space_after=Pt(1)
    lines = v.split('\n')
    p1 = cells[1].paragraphs[0]
    rich(p1, lines[0], size=9.5)
    p1.paragraph_format.space_after=Pt(1)
    for ln in lines[1:]:
        pp = cells[1].add_paragraph(); rich(pp, ln, size=9.5); pp.paragraph_format.space_after=Pt(1)
grid = t._tbl.tblGrid
grid.findall(qn('w:gridCol'))[0].set(qn('w:w'), str(int(1.88*1440)))
grid.findall(qn('w:gridCol'))[1].set(qn('w:w'), str(int(4.62*1440)))
hr(space_before=6, space_after=2, color='1F3864', sz=8)

body('**Enclosures:** Attachments A, B and C.  **Basis of this memorandum:** the landscape sheets L-1 through L-4 issued for plan check on 08/21/2026, the CCPW first-round comment letter of 10/09/2026, the resubmittal tracker dated 10/31/2026, and the record documents listed in Attachment C. Nothing in this memorandum has been sent to the County.', size=8.5, color=GREY, space_after=4)


# =====================================================================
# 1. BOTTOM LINE
# =====================================================================
doc.add_heading('1.  Bottom line', level=1)

body('**No. We cannot commit Callaway to a 12/18/2026 recordation on this revision, and we should not let 11/30/2026 be represented — to the surety, the lender, the association or the County — as a date that protects the map.** Four things drive that answer, and only one of them is the landscape work.')

bullet('**The date that controls the map is 12/23/2026, not 12/18/2026 — and not 03/14/2026 or 03/14/2028.** Phase 3 is a successive final map in the TM-22-500041 series. NRS 278.360 gives two years from the recording of the immediately preceding final map, and Phases 1 and 2 recorded on 12/23/2024 at Book 175, Page 60. Presentation of FM-26-100290 is due Wednesday, 12/23/2026. The 12/18 date is our own tracker target, five days inside the statutory date; it is a buffer, not a deadline, and the buffer is already gone.')

bullet('**An 11/30/2026 resubmittal cannot produce a recordable map by 12/23/2026.** CCPW states that second-round review is "generally completed within twenty (20) business days of receipt of a complete resubmittal." Twenty business days from 11/30/2026, allowing for the 12/25 holiday, is **Tuesday, 12/29/2026** — six days past the statutory date and eleven days past 12/18. There are only **17 business days** between 11/30 and 12/23 in total. And second-round approval is not recordation: after it come the performance security and the Subdivision Improvement Agreement, the County Surveyor, Zoning, Division of Water Resources and Health District certificate signatures, and Recorder processing — every one of them serial, and none of them started.')

bullet('**L-2 and L-4 are substantive, not clerical.** L-4 alone is **150 additional street trees** (208 required against 58 shown), which moves the tree density from an average of 71.7 feet between trees to 20 feet — a 3.6-fold increase in planting along 4,160 linear feet — and brings with it a 30% shade-coverage exhibit, a revised plant schedule, a revised irrigation demand (3.28 acre-feet per year to 4.21, or 2.31 if the park lawn is deleted), a re-sealed engineer\'s estimate and a revised bond, and Condition 14 design review before TAB and the Planning Commission. L-2 cannot be answered by declaring an exemption; counsel\'s memorandum of 10/20/2026 does not close it (§4).')

bullet('**What we can commit to.** A complete, defensible package at the Development Review counter on **11/30/2026**, provided the decisions in §7 reach us in writing by their due dates — **11/06/2026** for the turf option and the tree authorization, **11/10/2026** for design review; a design-review application filed **11/25/2026** for the 12/16/2026 TAB; and a realistic recordation in **Q1 2027**, with an extension application drafted and ready to file on 12/24/2026 as a contingency we do not recommend relying on (§6).')

body('We are not asking to slow the job down. We are telling you that our own target sits five days inside the statutory date, that the County\'s review cycle alone runs six days past it, and that neither gap absorbs a missed decision. The only way to lose the map is to build a schedule that assumes the County, the bond, four certificate agencies and the Recorder all perform perfectly — on a package that still has an unresolved turf question in it.')

# =====================================================================
# 2. THE DATE THAT CONTROLS
# =====================================================================
doc.add_heading('2.  The date that controls the map', level=1)

body('Four dates are circulating on this project. Only one of them is operative.')

table(
 ['Source in the record','Date asserted','Status'],
 [
  ['NRS 278.360, as quoted in the TM-22-500041 approval letter (03/14/2022) and in the Department\'s letter of 12/30/2024 (Marchetti)',
   'Two years from recording of the immediately preceding final map. First map recorded **12/23/2024**, Book 175, Page 60.',
   '**Operative. Presentation deadline Wednesday, 12/23/2026.**'],
  ['Curtis Hallenbeck, Comprehensive Planning — email of 10/15/2026',
   '"you were up on 03/14/2026" (four years from tentative approval)',
   'Not correct. The four-year period governs the __first__ map in the series; that map recorded 12/23/2024 and the Department\'s 12/30/2024 letter confirms the four-year clock "is no longer at issue."'],
  ['Neil Petrosyan, Silver Butte Title — email of 10/26/2026',
   '"covered out to 03/14/2028" by a two-year extension',
   'Not correct. No extension is of record; the 10/28/2024 application was declined as jurisdictionally premature; a statutory extension is discretionary, is available only on an application filed **after** the period has expired, and cannot exceed two years. A title officer\'s reading is not a source of statutory deadlines.'],
  ['Our own resubmittal tracker — Milestones tab',
   '"CONFIRM WITH PLANNING"',
   'Open in the tracker; answered in this memorandum as 12/23/2026, subject to the Department\'s letterhead confirmation now requested.'],
 ],
 [1.55,1.9,3.05], font=8.5)

body('The statute, as the County quoted it in the approval letter, is unambiguous:')
p = doc.add_paragraph()
p.paragraph_format.left_indent=Inches(0.35); p.paragraph_format.right_indent=Inches(0.35)
p.paragraph_format.space_after=Pt(6)
r = p.add_run('"A final map presented for recordation as the first map in a series must be presented to the governing body within four (4) years after the date of approval or conditional approval of the tentative map. Each successive final map in the same series must be presented within two (2) years after the date on which the immediately preceding final map is recorded. Failure to timely present a map terminates all proceedings relating to the subdivision."')
r.italic=True; r.font.size=Pt(9.5); r.font.color.rgb=NAVY

body('Phases 1 and 2 recorded on 12/23/2024 — Book 175, Page 60, Instrument No. 20241223-0004421 — and the face of that map carries the Recorder\'s note. Two years from that date is 12/23/2026. The Department\'s own 12/30/2024 letter confirms that the four-year first-map clock "has accordingly been satisfied and is no longer at issue," and directs the applicant to "confirm the operative presentation deadline for any successive map." That is what we have done.')

body('**What we are doing about it.** Ms. Marchetti asked us on 10/16/2026 to confirm the recordation date and recording reference of the first final map in the series in writing, so that she can respond on Department letterhead rather than by email. We are sending that confirmation on **Monday, 2 November 2026**. We are also asking her to state the successive-map deadline expressly. We expect the answer to be 12/23/2026, and we are not scheduling to any later date in the meantime. We are **not** relying on the title officer\'s 03/14/2028 reading, and the record does not support it: the 10/28/2024 application was returned as premature because the statute permits an application only after the period has expired; the extension is discretionary with the governing body; and the entitlement is not extended by anything in the file.')

body('One practical consequence deserves to be stated plainly. If FM-26-100290 is not presented by 12/23/2026, "all proceedings relating to the subdivision" terminate, and the only route back is a written extension application filed after that date. That is a discretionary act by the governing body, not an entitlement, and it will be decided on a record that by then includes a missed deadline. It is a fallback, not a plan. The County made the same point in the first-round letter: comment M-1 directs the applicant \"to schedule the recordation with adequate margin before that deadline.\" An 11/30 submittal built around a 12/18 target provides none — 12/18 is five days inside the statutory date, and we would have to hit it with no margin at all.')

# =====================================================================
# 3. WHAT THE L-SERIES RESPONSE REQUIRES
# =====================================================================
doc.add_heading('3.  What the L-series response actually requires', level=1)

body('The County\'s six landscape comments are not of one kind, and they should not be handled as one kind. L-5 is a drafting comment and L-6 is a counting exercise that we can close with an L-2 count. L-1 is the sealing task — simple in itself, but it comes last, not first. L-2, L-3 and L-4 change what the sheets say, and one of them — L-4 — changes the design.')

table(
 ['#','What the County asked for (letter of 10/09/2026)','Sheet(s)','Work required','Owner'],
 [
  ['L-1','Landscape sheets L-1 through L-4 sealed by the landscape architect of record on the resubmittal. Current sheets bear an unsigned seal block.','All four','Bea Cortland signs and seals the revised set. Technically simple, but it is the last step, not the first: the set cannot be sealed until the turf and tree decisions are final.','Ocotillo'],
  ['L-2','Turf classification analysis and supporting tabulation, "including area, category, and configuration for each turf hydrozone."','L-1 / L-3','A new classification tabulation. It can be answered factually, but the answer on the current sheets is "nonfunctional"; it cannot be answered as "exempt" (§4).','Ocotillo, with counsel'],
  ['L-3','Revise the L-1 compliance note to cite the applicable code standard and address the functional turf classification requirements of Title 30 sec. 30.64.030(j).','L-1','New note language citing 30.64.030(j) and 30.64.030(k) and stating the classification actually shown. Must be coordinated with Ms. Vogel before it is sealed.','Ocotillo / counsel'],
  ['L-4','One tree per 20 linear feet of street frontage; based on 4,160 lf, 208 trees required and 58 shown; revised planting plan and revised annual irrigation demand.','**L-2 (plan) and L-1 (schedule)** — not Sheet L-4','150 additional trees laid out at 20 ft on centre; revised schedule; 30% shade-coverage exhibit; revised irrigation demand; revised sealed estimate and bond.','Ocotillo / Sundial'],
  ['L-5','Dimension the setback of planting from face of curb on the streetscape sections and confirm no turf within ten feet of a street or curb.','L-2','Dimension Sections A, B and C. Drafting only; the sections already carry the "no turf within 10\u2032-0\u2033" callout.','Ocotillo'],
  ['L-6','Update the plant schedule on L-1 so that scheduled quantities match the quantities plotted on the plan.','L-1 and L-2','An L-2 planting count. Of the 1,192 shrubs and accents in the L-1 schedule, only 310 are counted on L-3 and L-4; the remaining 882 have no count sheet anywhere in the set.','Ocotillo'],
 ],
 [0.42,2.05,0.95,2.33,0.75], font=8.3)

body('The County\'s letter is also explicit that comments "not addressed at resubmittal will be repeated in the second-round comment matrix." Filing the package without a substantive L-2 and L-4 answer therefore does not buy us a review cycle; it buys a repeat, at the back of another twenty-business-day queue that starts after the statutory date has already passed.')

doc.add_heading('3.1  L-4 in detail — and why "Sheet L-4" is not where the trees go', level=2)

body('Garrett\'s instruction refers to the "L-4 street tree revision." The comment numbered L-4 is about street frontage, and street frontage is drawn on **Sheet L-2** and scheduled on **Sheet L-1**. **Sheet L-4 is the entry monument** at Rainbow Boulevard and the interior collector; its six Red Push Pistache are unaffected, and its plant counts do not change. If we receive verbal direction to "put the trees on L-4," it will land on the wrong sheet. The revision triangles belong on L-1 and L-2.')

table(
 ['Frontage','Length (lf)','Required @ 20 lf','Shown','Add\'l','Current avg. spacing'],
 [
  ['Windmill Ln. — Phase 3 south boundary, landscape-strip side (the north side of Windmill Ln.; Sheet L-2 labels it the "north frontage")','2,560','128','34','+94','75.3 ft'],
  ['Phase 3 interior collector, both sides','1,180','59','16','+43','73.8 ft'],
  ['Rainbow Blvd. entry frontage, east side','420','21','8','+13','52.5 ft'],
  ['**Total**','**4,160**','**208**','**58**','**+150**','**71.7 ft**'],
 ],
 [2.6,0.72,0.85,0.6,0.6,0.85], font=8.5, align_right=(1,2,3,4,5), bold_rows=(3,))

body('The arithmetic is not in dispute and we should not re-open it. The County used 4,160 linear feet; that is the same figure on our own L-2 frontage summary and in the Ocotillo tabulation. Re-measuring from the final map now would only invite a different denominator in the middle of a review cycle. At the required spacing the trees alone occupy the whole frontage: 208 trees at 20 feet on centre is exactly 4,160 feet.')

body('Three consequences follow that are not in the County\'s comment:')
bullet('**The 30% shade standard needs an exhibit, not just a count.** CCPW guidance CP-PW-GM-2025-04 §3 applies a shade-coverage performance target of **30% of the streetscape area at 15-year canopy**, in addition to the numerical tree standard. Compliance is demonstrated by a **Shade Coverage Exhibit** — one sheet or overlay showing every proposed tree with its 15-year canopy circle drawn to scale over the streetscape area, with a tabulation of canopy area, streetscape area and the resulting ratio. Where the 30% target cannot be met at the minimum count, the guidance expects additional trees or higher-canopy species. We will prepare the exhibit concurrently with the plant schedule so that species and count are adjusted before the sheets are locked.')
bullet('**Locations are constrained.** The 20-foot dry utility joint trench runs the full length of the north boundary, the sight-distance triangle at Rainbow Boulevard and the interior collector must remain clear of planting that exceeds 24 inches in height, and General Note 12 forbids planting in a dedicated easement without the utility\'s written permission. Adding 150 trees into the remaining strip is a layout exercise, not a copy-and-paste.')
bullet('**The irrigation demand and the estimate move with it.** Comment L-4 asks for a revised annual irrigation demand, and Condition 28 requires the worksheet to be updated "to reflect any revision to the planting palette prior to landscape approval." Both are in Attachment B and §8.')

body('An Alternative Standards request under CC 30.64.050 remains available for genuine geometry or utility conflicts, but it is discretionary, it requires a written submittal and a written Department approval, and the guidance is explicit that it "is expressly not available to modify or waive the turf restrictions of sec. 30.64.030(j)." It is a tool for tree spacing, not a route around the turf question.')

# =====================================================================
# 4. TURF
# =====================================================================
doc.add_heading('4.  The turf question — why the 10/20 memorandum does not close L-2', level=1)

body('Adrienne Vogel\'s memorandum of 10/20/2026 concludes that the nonfunctional turf prohibition does not apply to Phase 3 because the property is zoned R-2 detached and is mapped single-family residential, and asks us to adopt that position in the response matrix and record L-2 as closed. We are not able to do that, and we would be doing Callaway no service by sealing a landscape sheet that says so.')

body('The administering agency\'s own compliance bulletin — SNWA WRC-2024-07, which supersedes WRC-2022-04 and carries the 12/31/2026 compliance deadline — addresses the point directly. It applies to "all properties within the SNWA service area other than individually-owned single-family residential lots," and then closes the door on the project-level reading:')

for q in ['"The single-family residential carve-out is lot-based, not project-based."',
          '"HOA-owned or HOA-managed common-area parcels of any description, including but not limited to park parcels, tot lots, greenbelts, drainage tracts, entry features, monument islands, and landscape maintenance strips" remain "fully subject to the prohibition even where they lie within a subdivision the zoning of which is single-family residential."',
          '"the presence of a single-family residential zoning designation on the underlying parcel does not confer the carve-out on common-area turf within that parcel; the operative distinction is the lot line, not the zoning district."']:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent=Inches(0.35); p.paragraph_format.right_indent=Inches(0.35)
    p.paragraph_format.space_after=Pt(4)
    r = p.add_run(q); r.italic=True; r.font.size=Pt(9); r.font.color.rgb=NAVY

body('The Phase 3 park is Common-Area Parcel **"D"** on the final map and on the civil plans (Sheet C-2), and it is called **Parcel A** on the Phase 3 landscape sheets. Those are two labels for the same 1.85-acre parcel. It is not the Parcel A of the recorded declaration: the CC&Rs recorded 12/23/2024 (Instrument No. 20241223-0004422, Book 175, Page 61) define the "Common-Area Park" as Parcel A on the first final map, which is the Phases 1 and 2 park. Phase 3 common area becomes subject to the declaration automatically on recordation of the Phase 3 map (\u00a73.2(c)), and the declarant may annex Phase 3 by supplemental declaration (\u00a73.3); Condition 16 separately requires CC&Rs establishing the association\'s common-area maintenance obligations, with a common-area maintenance exhibit, to be recorded concurrently with the Phase 3 map. Association ownership and maintenance of Parcel D is therefore an obligation to be perfected on recordation, not a completed conveyance today — but under the bulletin the parcel is squarely inside the prohibition either way, because the carve-out turns on the lot line and no part of Parcel D lies inside a single-family lot.')

body('On the functional categories, our own tabulation decides the question against us. It records **0 square feet** of Phase 3 turf "within a designated play area with playground amenities." The playground equipment — slides, swings and climbing structures — was value-engineered out in July 2026 — our coordination email of 28 July 2026 records the cut — and Sheet L-3 now describes the park as "a passive-use turf lawn." Bulletin §3.1 requires amenities that are "installed and operable" and states that "a designated play area lacking installed playground amenities does not qualify as playground turf, regardless of the sign or plan label attached to the area." §4 adds that such an area "cannot be waived under Section 3.1 by promising future amenities," and that "a lawn intended for passive use, decorative purpose, aesthetic frontage, or general open space cannot be waived under Section 3.2 by asserting occasional recreational use."')

body('The contrast with Phase 1 and 2 is the tell. The approved 2022 set carried 4,200 square feet of turf "within a clearly designated play area" with slides, swings and climbing structures installed, and its compliance note said so. Phase 3 carries 18,400 square feet — more than four times as much — with none of the qualifying elements. **The 18,400 square feet of cool-season sod at Parcel D (Parcel A on the landscape sheets) constitutes nonfunctional turf, and its conversion deadline is 12/31/2026.**')

body('There is a further point that forecloses the "we will deal with it when we build" fallback. The bulletin states that on and after 12/31/2026 "the presence of nonfunctional turf on a property subject to the prohibition constitutes a continuing violation." Installing new nonfunctional turf after the deadline is not a lawful alternative to converting existing turf; the prohibition is on the turf, not on the date it was planted. Deferring the decision to construction does not preserve the option.')

table(
 ['Option','What it would involve','Verdict'],
 [
  ['**A.  Delete the lawn and convert the area**','Remove the 18,400 sf of cool-season sod from L-3, convert the footprint to drip-irrigated desert planting and decomposed granite, revise the L-1 compliance note and the irrigation worksheet (3.28 → **2.31** ac-ft/yr), and delete estimate line 7.16.','**Recommended.** It is the only option that can be sealed and submitted on 11/30, it answers L-2 and L-3 truthfully, it removes the 12/31/2026 exposure entirely, it saves about 0.98 acre-feet of water a year, and it is the least expensive of the three.'],
  ['**B.  Reinstate a designated play area with installed amenities**','Rebuild the park program with a bordered play area and installed slides, swings and climbing structures so the turf qualifies as playground turf under §3.1.','**Not achievable on this schedule.** Installation must be complete on or before 12/31/2026; the parcel is unrecorded and unpermitted, no construction has started, and the equipment was removed from scope in July. It adds capital cost to the bond and a second design-review question. It can be pursued later as an HOA amenity — on a non-turf safety surface, which avoids the turf issue altogether — but it is not a 2026 answer.'],
  ['**C.  Waiver or special-use application**','Apply to SNWA under §4 (waiver) or §3.4 (special-use turf) to recognize the lawn as functional.','**Not available on this record.** §4 requires the application to show "substantial compliance" with a functional category; a passive lawn is expressly excluded and hardship or aesthetic preference is not a ground. §3.4 is directed at cemetery, historic-district and accessibility lawn, not a subdivision amenity lawn. It is discretionary, it does not move the 12/31/2026 date, and it would not close a County comment that asks for a classification.'],
 ],
 [1.35,2.5,2.65], font=8.3)

body('**What we will put on the sheet.** We will answer L-2 with the classification tabulation the County asked for — area, category and configuration for each turf hydrozone — rather than with a legal conclusion. If Ms. Vogel wishes to preserve her position, the place for it is a separate counsel letter accompanying the resubmittal, and we will include one if she authors it. What we cannot do is seal a compliance note that asserts an exemption the administering agency\'s own bulletin rejects: that exposes Bea Cortland\'s seal, the County will repeat the comment in the second round, and it leaves a recorded park that is in violation on the day it is built. A counsel letter preserves the argument; a sealed sheet does not.')

body('**The association.** Sagebrook wrote on 10/17/2026 asking whether Phase 3 will carry the Phase 1/2 playground amenities, and has told us that a group of homeowners will address the Phase 3 park at the 11/18/2026 TAB public comment. The letter also puts a number on delay: at the **$2.85 per square foot** the association has been quoted for turf-to-desert conversion, the 18,400 square feet would cost about **$52,440** to convert later, after it is built and while the HOA owns it. Deleting it now avoids that cost and avoids handing the association a conversion obligation in its first reserve cycle. We recommend taking up Sagebrook\'s offer of a joint working session before 11/18 — the amenity question and the turf question are related, and it is better answered with the association in the room than at a public hearing.')

# =====================================================================
# 5. PROCESS GATE
# =====================================================================
doc.add_heading('5.  The process gate: Condition 14 design review', level=1)

body('Condition 14 of the TM-22-500041 approval is not discretionary language, and it is the gate that makes a 2026 recordation impossible regardless of how fast we work:')
p = doc.add_paragraph()
p.paragraph_format.left_indent=Inches(0.35); p.paragraph_format.right_indent=Inches(0.35); p.paragraph_format.space_after=Pt(6)
r = p.add_run('"Any significant change to approved plans, including but not limited to landscape and streetscape treatments in common areas, shall be subject to design review as a public hearing before the applicable Town Advisory Board and Planning Commission prior to staff-level action."')
r.italic=True; r.font.size=Pt(9.5); r.font.color.rgb=NAVY

body('Deleting 18,400 square feet of park lawn and adding 150 street trees to the common-area streetscape is a significant change to approved landscape and streetscape treatment in common areas. Advisory comment A-3 in the County\'s letter says the same thing: a revision that "materially changes the approved plan character may require additional process steps before plan approval can proceed." There is no version of the L-2/L-4 response that avoids this — even Option A, which deletes rather than adds, changes the approved park character.')

table(
 ['Step','Date','Status'],
 [
  ['Enterprise TAB, 11/18/2026 — application submittal cut-off (21 days prior)','10/28/2026','**Passed.** We cannot be on the 11/18 agenda.'],
  ['Next regular Enterprise TAB, 12/16/2026 — application submittal cut-off; agenda posting','11/25/2026; posted 12/06/2026','Available, if the application is complete and filed by 11/25.'],
  ['Planning Commission hearing on the design review','**Not scheduled** — no date appears in the record','The County will not set it until the TAB record exists. We are not relying on a date we do not have.'],
  ['Staff-level action on the revised landscape sheets','After the Planning Commission acts','Cannot be scheduled; the hearing that must precede it has not been noticed.'],
  ['Second-round CCPW review of the resubmittal','20 business days from a complete resubmittal','**11/30 + 20 business days = 12/29/2026** — the controlling blocker.'],
  ['NRS 278.360 presentation of FM-26-100290','**12/23/2026**','Statutory.'],
 ],
 [2.7,1.75,2.05], font=8.5)

body('**No Planning Commission hearing is scheduled, and the County\'s review cycle alone ends 12/29/2026.** The Board\'s recommendation on 12/16 must be followed by a Planning Commission hearing and action, and no Planning Commission date appears anywhere on this record; our own schedule carries it as "to be scheduled." Even if that hearing were noticed and held the week after TAB, design review would still have to finish before staff could act — and the County\'s 20-business-day second-round review clock runs from receipt of the complete 11/30 resubmittal, not from the end of design review, so it ends on 12/29/2026 at the earliest, whether or not design review is finished. The landscape revision and the statutory deadline are therefore not in series; they conflict. The controlling blocker is the review cycle, not a Planning Commission date we do not have.')

body('We also cannot keep the item off the TAB calendar. The association has said its members will attend on 11/18 regardless, and a public hearing we did not request is worse for Callaway than one we did: without an application there is no staff report, no applicant presentation and no record of our position, and Mr. Yeoman still cannot act on the sheets. Filing on 11/25 is the only way to have our own record before the Board in December.')

# =====================================================================
# 6. WHAT HAS TO HAPPEN FIRST
# =====================================================================
doc.add_heading('6.  What has to happen first — and what we can commit to', level=1)

body('The sequence below is the shortest one that produces a package the County can act on and Bea Cortland can seal. Every date is a working date; the 11/30 entry is the one that matters commercially, and it holds only if the 11/06 and 11/10 decisions are in writing. We will also state on the transmittal, in the response matrix and in a cover note to Mr. Yeoman that the landscape sheets are submitted **pending Condition 14 design review** — we are not going to file this package as though that review were behind us.')

table(
 ['Date','Action','Owner'],
 [
  ['Mon 11/02/2026','Recording reference (12/23/2024; Book 175, Page 60) sent to Ms. Marchetti; written request for the Department\'s letterhead determination of the successive-map deadline','Sundial'],
  ['Mon 11/02/2026','Written renewal request to CCWRD — capacity confirmation CCWRD-SCC-2025-1187 **expired 09/30/2026** (see below)','Callaway / Sundial'],
  ['Tue 11/03/2026','Ocotillo and Sundial design kick-off on the 208-tree layout, the shade exhibit and the L-3 conversion','Sundial / Ocotillo'],
  ['**Fri 11/06/2026**','**Callaway decisions 1 and 2 in §7 in writing** — park turf option, and 208-tree authorization with the Ocotillo supplement','**Callaway**'],
  ['Fri 11/06/2026','Written notice to Comprehensive Planning that the landscape revision will be filed for design review','Sundial'],
  ['Tue 11/10/2026','**Callaway decision 3 in §7 (design review) due**; revised L-1 note and the turf classification tabulation to Ms. Vogel for review','**Callaway** / Ocotillo'],
  ['Fri 11/13/2026','Signatory confirmation for the Owner\'s Certificate (comment M-5); palette locked for the revised irrigation worksheet','Callaway / Ocotillo'],
  ['Fri 11/20/2026','Internal: L-1, L-2 and L-3 revised; shade exhibit drafted; estimate re-priced and re-sealed for principal review','Ocotillo / Sundial'],
  ['**Wed 11/25/2026**','**Design-review application filed with Comprehensive Planning for the 12/16/2026 TAB** (21-day cut-off)','Sundial'],
  ['**Mon 11/30/2026**','**Resubmittal to Mr. Yeoman** — sealed L-1 through L-4, revised irrigation demand, revised sealed estimate, annotated matrix, red-lined and clean sets. L-2 and L-3 answered in full and recorded as **pending design review**, not closed','Sundial'],
  ['Wed 12/16/2026','Enterprise TAB hearing','Callaway / Sundial'],
  ['**Wed 12/23/2026**','**NRS 278.360 presentation deadline for FM-26-100290**','—'],
  ['Thu 12/24/2026','If the map has not been presented: written extension application filed after expiry (the statutory precondition)','Callaway, with counsel'],
  ['Q1 2027','Planning Commission action; second-round CCPW approval; performance security and SIA; certificate-set signatures; recordation','Joint'],
 ],
 [0.95,4.35,1.2], font=8.3)

doc.add_heading('6.1  Gates that are not landscape, and that we have been treating as though they were closed', level=2)

bullet('**The CCWRD capacity confirmation has already expired.** Confirmation CCWRD-SCC-2025-1187 was issued 09/30/2025 for one year and "expires on 09/30/2026." The District\'s terms are that "[r]enewal must be requested in writing prior to expiration; expired confirmations require re-review of downstream conditions and reissuance before plan approval," and Condition 22 requires the confirmation to be current at final map recordation. We are 31 days past expiry as of this memorandum. A renewal request should go out on 11/02; the District\'s re-review time is outside our control and we should not assume it is short.')
bullet('**The title report runs out on 01/01/2027.** Report SBT-2026-04188 is effective 07/01/2026 and satisfies the six-month currency test in comment M-4 for an 11/30/2026 resubmittal. It will have to be updated for a Q1 2027 recordation — another reason not to represent this as a December closing.')
bullet('**The bond has to move with the estimate.** Condition 8 requires security "in the full amount of the engineer\'s estimate of probable cost," and Advisory comment A-6 reminds us that the estimate "forms the basis of the performance security." The 10/10/2026 sealed estimate changes under any of the three turf options (see §8). It must be re-sealed by Mr. Kessler, and the SIA and bond amount revised, before recordation.')
bullet('**The Owner\'s Certificate still needs a signatory.** Comment M-5 requires the current authorized signatory for Callaway Land Partners in the Nevada statutory notary form. The 2024 map was executed before Karen L. Montoya, whose commission runs to 01/31/2027, so the same notary is available if you sign again. We need written confirmation by 11/13.')
bullet('**F-1 \u2014 permanent second point of access.** Comment F-1 is a binding General Comment and remains open in the tracker (owner M. Braddock, due 11/22/2026). The coordination call with Capt. Roark of CCFD is targeted for **11/10/2026**, and the alignment, cross-section and arterial connection must be shown on Sheet C-2. Nothing in the landscape work closes F-1, and no landscape response is credible in a package that still lacks a documented second point of access.')
bullet('**G-8 \u2014 erosion and sediment control and NDEP NVR100000.** The stand-alone ESC sheet and the NOI number are a binding General Comment, open in the tracker (owner M. Braddock, due 11/22/2026), with the NDEP coverage and NOI status targeted for **11/13/2026**. That is a new sheet, not a revision to an existing one, and it carries its own review time.')
bullet('**The water will-serve is not a constraint.** LVVWD letter LVVWD-WS-2026-3341 dated 07/22/2026 runs to 07/22/2028 — but note that it also binds the project to the District\'s conservation rules "including limitations on turf and landscape irrigation," which is another reason the turf answer has to be right rather than asserted.')

body('The rest of the General Comments \u2014 G-1 through G-8, F-1 through F-4, U-1 through U-5 and M-1 through M-7 \u2014 are being worked to the tracker\'s 11/22/2026 internal completion date and are not re-planned here. This memorandum addresses the L-series and the gates that sit outside the tracker\'s critical path; it does not vouch for the other twenty-four comments. If any of them slips, the 11/30 resubmittal slips with it whatever happens on the landscape sheets \u2014 which is the other reason the 12/18 recordation is not a date we can commit to.')

body('**If the 11/06 decisions slip, 11/30 slips with them.** A one-week slip in the decisions moves the resubmittal to **12/07/2026**, which leaves **12 business days** before the statutory date — fewer than the County needs for second-round review alone. At that point the extension application stops being a contingency and becomes the plan.')

# =====================================================================
# 7. DECISIONS
# =====================================================================
doc.add_heading('7.  Decisions we need from Callaway', level=1)

body('Five decisions, each with a date. The consequence of silence is listed because on this schedule silence is itself a decision.')

table(
 ['#','Decision','Due','Cost / effect','If we do not have it'],
 [
  ['1','**Park turf: Option A, B or C** in §4. Our recommendation is A (delete the lawn and convert the area).','Fri 11/06/2026','A removes $39,560 of sod and about 0.98 ac-ft/yr of demand; B adds playground capital cost not now in the estimate; C costs application time and is unlikely to succeed.','L-2 and L-3 cannot be answered or sealed, the 11/30 submittal slips, and the 12/31/2026 conversion exposure stays open.'],
  ['2','**Written authorization of the 208-tree design**, acknowledging that it triggers Condition 14 design review, together with the Ocotillo supplement in §8.','Fri 11/06/2026','Approximately **+$45,000** in direct estimate movement (§8), plus the supplement (recommended not less than $10,000).','The L-4 layout cannot be drawn; L-4 stays open in the second round.'],
  ['3','**Design review: confirm we file for the 12/16/2026 TAB on 11/25.**','Tue 11/10/2026','Included in the resubmittal phase; no additional agency fee beyond the County application fee already budgeted at B-08.','We do not file, the Board hears the park without our record, and Mr. Yeoman cannot act on the sheets.'],
  ['4','**Signatory confirmation** for the Owner\'s Certificate and Dedication, in the Nevada statutory notary form.','Fri 11/13/2026','No cost; notary available (K. Montoya, commission to 01/31/2027).','The certificate set cannot be routed and recordation is blocked independently of everything else.'],
  ['5','**Extension application: prepare it or not.** If yes, it is filed on 12/24/2026 after the period expires.','Fri 12/04/2026','Counsel time; filing fee per the County schedule. It is discretionary with the governing body.','If the map is not presented by 12/23, the proceedings terminate with no application on file.'],
 ],
 [0.3,1.82,0.88,1.7,1.8], font=8.2)

# =====================================================================
# 8. COST AND FEE
# =====================================================================
doc.add_heading('8.  Cost, fee and bond', level=1)

body('The landscape changes move the sealed estimate of 10/10/2026 and therefore the bond. The line arithmetic below uses the County\'s own unit prices as they appear in that estimate.')

table(
 ['Line','Description','Current','Revised','Change'],
 [
  ['7.09','Tree, 24-inch box, planted, staked and mulched (@ $485/EA)','64 EA','214 EA','**+$72,750**'],
  ['7.16','Turf sod, cool-season blend (@ $2.15/sf)','18,400 sf','0 sf (Option A)','**−$39,560**'],
  ['7.41','Drip tubing, subsurface, 12-inch emitters (@ $0.65/sf)','55,000 sf','73,400 sf','**+$11,960**'],
  ['**Net, direct line changes**','','','','**+$45,150**'],
  ['7.43 / 7.17','Spray heads and mow strip no longer required (40 EA @ $42; 600 lf @ $12.75)','—','—','up to −$9,330'],
  ['7.02 / 7.11–7.14','Plant stock and decomposed granite for the converted 18,400 sf — not yet priced','—','—','roughly +$20,000 to +$40,000'],
 ],
 [0.9,2.2,1.1,1.12,1.18], font=8.2, align_right=(2,3,4))

body('Section 6 of the estimate is $389,340 today. The direct changes take it to about **$434,500**, and once the converted-area planting, the granite and the mow-strip and spray-head credits are priced we expect it to land between roughly **$445,000 and $465,000**. The bonded total — $5,357,000 today — moves by the same amount. These are order-of-magnitude figures for planning; Ocotillo\'s takeoff governs, and we will not re-seal until it is in hand. What matters for the schedule is that the direction is **up**, because 150 twenty-four-inch box trees cost far more than 18,400 square feet of sod saves.')

body('**Why the estimate has to move whichever option you choose.** Section 7 of the County\'s Uniform Unit Cost Schedule, note (a), provides that "[t]urf items shall be estimated only for functional turf classifications recognized under Chapter 30.64 and SNWA guidance; nonfunctional turf shall not be included in the engineer\'s estimate for bonding." The sealed 10/10/2026 estimate carries 18,400 square feet of turf at line 7.16. On the record as it stands, that line is not bondable. Option A is the only option that lets us delete it and re-seal at 11/30; Options B and C both leave the estimate in its present position until the turf question is resolved.')

body('**Fee.** Resubmittal fee line B-04 — $14,300 to Ocotillo — was scoped for sheet revisions, the compliance note and the irrigation worksheet. It does not cover the 208-tree layout, the 30% shade-coverage exhibit, the L-3 conversion, the re-seal and the re-priced estimate. We recommend a supplement of **not less than $10,000**, with Ocotillo confirming its scope within five business days of your direction so that the number is theirs and not ours. Sundial\'s added coordination — the TAB package, Planning Commission coordination, the re-sealed estimate and the extension filing — will be absorbed within the approved resubmittal-phase fee (B-02, $58,400); we are not asking for an increase on our side.')

# =====================================================================
# 9. RECOMMENDATION
# =====================================================================
doc.add_heading('9.  Recommendation', level=1)

body('Do not commit to 12/18/2026 recordation, and do not tell the surety, the lender or the association that the 11/30 resubmittal protects the map — it does not. Give us the park turf direction and the tree-design authorization by 11/06, let us file design review by 11/25, and let us hold a draft extension application ready to file on 12/24. That sequence gives Callaway the only realistic path to a recorded Phase 3 map, and it keeps every document we put our seal on defensible.')

body('We are available at your convenience — the direct line, as you asked.')

sp = doc.add_paragraph(); sp.paragraph_format.space_before=Pt(18); sp.paragraph_format.space_after=Pt(0)
r = sp.add_run('By:  ______________________________________'); r.font.size=Pt(10.5)
p = doc.add_paragraph(); p.paragraph_format.space_after=Pt(0)
r = p.add_run('Max Braddock'); r.bold=True; r.font.size=Pt(10.5)
p = doc.add_paragraph(); p.paragraph_format.space_after=Pt(0)
r = p.add_run('Project Manager · Sundial Engineering & Survey · NV COA #C-3874'); r.font.size=Pt(9.5); r.font.color.rgb=GREY
p = doc.add_paragraph(); p.paragraph_format.space_after=Pt(0)
r = p.add_run('Date:  October 31, 2026'); r.font.size=Pt(9.5); r.font.color.rgb=GREY

p = doc.add_paragraph(); p.paragraph_format.space_before=Pt(14)
r = p.add_run('Attachments:  A — Street frontage and tree reconciliation (comment L-4);  B — Annual irrigation demand;  C — Documents relied on.')
r.font.size=Pt(9); r.font.color.rgb=GREY

# =====================================================================
# ATTACHMENT A
# =====================================================================
page_break()
doc.add_heading('Attachment A — Street frontage and tree reconciliation (comment L-4)', level=1)

body('Basis: Sheet L-2 Streetscape Frontage Summary (08/21/2026); Phase 3 Turf and Planting Tabulation, tab "Frontage & Trees" (08/15/2026); CCPW comment L-4 of 10/09/2026; CC 30.64.030(k) at the medium-canopy tier (one tree per 20 linear feet) as restated in guidance memorandum CP-PW-GM-2025-04 §2. Fractional lengths are rounded up to the nearest whole tree; no fraction arises on this tabulation.')

table(
 ['Frontage','Length (lf)','Canopy tier','Required (lf ÷ 20)','Trees shown','Add\'l required','Current avg. spacing'],
 [
  ['Windmill Ln. — Phase 3 south boundary, landscape-strip side (north side of Windmill Ln.)','2,560','Medium','128','34','+94','75.3 ft'],
  ['Phase 3 interior collector, both sides','1,180','Medium','59','16','+43','73.8 ft'],
  ['Rainbow Blvd. entry frontage, east side','420','Medium','21','8','+13','52.5 ft'],
  ['**Total**','**4,160**','','**208**','**58**','**+150**','**71.7 ft**'],
 ],
 [2.2,0.68,0.62,0.8,0.68,0.7,0.82], font=8.3, align_right=(1,3,4,5,6), bold_rows=(3,))

body('**Species shown on the street frontages** (Sheet L-1 plant schedule): Desert Willow (CHL) 18, Desert Museum Palo Verde (PAR) 22, Thornless Mesquite (PBR) 18 — **58**. Entry monument (Sheet L-4): **6** Red Push Pistache (PIE) — unchanged, and not part of the street frontage count. Park interior (Sheet L-3): **10** Evergreen Elm (ULP) — unchanged. Total Phase 3 trees 74; after the L-4 revision the street count becomes 208 and the total becomes 224, which is the tree count carried into Attachment B.')

doc.add_heading('A.1  Comment L-6 — plant schedule versus plotted quantities', level=2)

body('Comment L-6 asks that schedule quantities match the quantities plotted. Only Sheets L-3 and L-4 carry plant counts; there is no count sheet for Sheet L-2, which is where the streetscape shrub massing is drawn. Comparing the L-1 schedule against the L-3 and L-4 counts leaves 882 of 1,192 scheduled shrubs and accents unaccounted for:')

table(
 ['Symbol','Species','L-1 schedule','Counted on L-3','Counted on L-4','Accounted','Not shown on any count'],
 [
  ['LEU','Texas Sage','260','50','24','74','186'],
  ['DAS','Desert Spoon','96','14','8','22','74'],
  ['HES','Red Yucca','188','40','20','60','128'],
  ['ENC','Brittlebush','280','66','30','96','184'],
  ['MUH','Pink Muhly Grass','112','24','10','34','78'],
  ['AGE','Weber\'s Agave','48','—','8','8','40'],
  ['SAS','Autumn Sage','180','—','—','0','180'],
  ['YUC','Beaked Yucca','28','10','6','16','12'],
  ['**Total**','','**1,192**','**204**','**106**','**310**','**882**'],
 ],
 [0.6,1.35,0.85,0.85,0.85,0.8,1.2], font=8.3, align_right=(2,3,4,5,6), bold_rows=(8,))

body('The L-6 response cannot close until an L-2 planting count is prepared and the schedule reconciled to it. That work sits with Ocotillo and is part of the 11/30 package, but it is separate from — and should not be confused with — the L-4 tree count.')

body('**Note on the frontage label.** Sheet L-2 calls the Windmill frontage the "north frontage, Phase 3 extension" (the north side of Windmill Lane), while the tabulation calls it the "Phase 3 south frontage, landscape strip side" (the parcel\'s south boundary). They are the same 2,560 linear feet. We have used a description that reconciles both so that the second-round reviewer does not read them as two frontages.')

# =====================================================================
# ATTACHMENT B
# =====================================================================
page_break()
doc.add_heading('Attachment B — Annual irrigation demand', level=1)

body('Rates are unchanged from the Ocotillo worksheet of 08/15/2026 and follow the delivery-method approach described in guidance memorandum CP-PW-GM-2025-04 §5(4): spray-irrigated turf and drip-irrigated desert planting computed separately, with a per-tree allowance added for canopy trees. Conversions: 43,560 sf per acre; 325,851 gallons per acre-foot.')

table(
 ['Component','Rate basis','As issued 08/15/2026','Lawn retained + 208 street trees','Lawn deleted (Option A) + 208 street trees'],
 [
  ['Spray turf — 18,400 sf at Parcel D (Parcel A on the landscape sheets)','5.5 ft/yr','2.323 ac-ft','2.323 ac-ft','—'],
  ['Drip planting — 22,200 sf (40,600 sf under Option A)','1.0 ft/yr','0.510 ac-ft','0.510 ac-ft','0.932 ac-ft'],
  ['Trees — 74 as issued; 224 with 208 street trees','2,000 gal/tree/yr','0.454 ac-ft','1.375 ac-ft','1.375 ac-ft'],
  ['**Total**','','**3.287 ac-ft/yr** (3.28)','**4.208 ac-ft/yr** (4.21) — **+0.921**','**2.307 ac-ft/yr** (2.31) — **−0.980**'],
 ],
 [1.95,0.9,1.05,1.3,1.3], font=8.3, align_right=(2,3,4), bold_rows=(3,))

body('Calculations, so that the reviewer can follow them line by line:')
bullet('Spray turf: 18,400 sf × 5.5 ft/yr = 101,200 cu ft ÷ 43,560 = **2.323 ac-ft**.')
bullet('Drip planting, as issued: 22,200 sf × 1.0 ft/yr = 22,200 cu ft ÷ 43,560 = **0.510 ac-ft**; with the 18,400 sf converted: 40,600 cu ft ÷ 43,560 = **0.932 ac-ft**.')
bullet('Trees: 74 × 2,000 gal = 148,000 gal ÷ 325,851 = **0.454 ac-ft**; 224 × 2,000 gal = 448,000 gal ÷ 325,851 = **1.375 ac-ft**.')
bullet('Totals: 2.323 + 0.510 + 0.454 = **3.287**; 2.323 + 0.510 + 1.375 = **4.208** (+0.921); 0.932 + 1.375 = **2.307** (\u22120.980).')

p = doc.add_paragraph(); p.paragraph_format.left_indent=Inches(0.0); p.paragraph_format.space_after=Pt(6)
r = p.add_run('Rounding: the computed totals are 3.287 / 4.208 / 2.307. The issued worksheet \u2014 and this memorandum, for continuity with it \u2014 carries 3.28 / 4.21 / 2.31; the 3.28 is the worksheet\'s Summary figure, which adds its rounded components (2.83 + 0.45). The differences above are taken against the unrounded 3.287 and read +0.921 and \u22120.980 (shown as +0.92 and \u22120.98); subtracting the rounded 3.28 would give +0.93 and \u22120.97. No conclusion in this memorandum depends on which baseline is used: the lawn-retained case is about one acre-foot higher and the lawn-deleted case about one acre-foot lower either way.')
r.font.size=Pt(9.5); r.italic=True; r.font.color.rgb=GREY

body('The worksheet will be reissued with the 11/30 resubmittal as comment L-4 and Condition 28 require. Note that the tree increase alone raises demand by 0.92 acre-feet a year; deleting the park lawn more than offsets it, so Option A leaves the project using about 30% less water than the current sheets show even with 150 more trees.')

# =====================================================================
# ATTACHMENT C
# =====================================================================
page_break()
doc.add_heading('Attachment C — Documents relied on', level=1)

table(
 ['Document','Date / effective','What it establishes'],
 [
  ['CCPW first-round comment letter, IP-26-100288 / FM-26-100290 (D. Yeoman, PE)','10/09/2026','Comments L-1 through L-6 and the required resubmittal package; second-round review "generally completed within twenty (20) business days"; Advisory comments A-3 and A-6'],
  ['TM-22-500041 Notice of Approval and Conditions of Approval (O. Marchetti)','03/14/2022','NRS 278.360 quoted in full; Conditions 8, 14, 20, 21, 22 and 25–28; the direction that each applicant compute its own deadlines "from the events identified in the statute"'],
  ['Desert Sage Ranch Phases 1 & 2 final map, NFM-24-0118, Book 175, Page 60, Instrument No. 20241223-0004421','Recorded 12/23/2024','The start of the two-year successive-map clock'],
  ['Declaration of Covenants, Conditions and Restrictions for Desert Sage Ranch, with Common Area Maintenance Exhibit (Instrument No. 20241223-0004422)','Recorded 12/23/2024, Book 175, Page 61','Defines the "Common-Area Park" as Parcel A on the first final map (the Phases 1 and 2 park); Phase 3 common area becomes subject to the declaration on recordation of the Phase 3 map (\u00a73.2(c)) and may be annexed by supplemental declaration (\u00a73.3); maintenance obligations and common-area maintenance exhibit (Condition 16)'],
  ['Comprehensive Planning letter on the extension application (O. Marchetti)','12/30/2024','The four-year first-map clock "is no longer at issue"; the successive clock governs; an extension requires a written application filed after expiry and is capped at two years'],
  ['Comprehensive Planning emails (C. Hallenbeck 10/15/2026; O. Marchetti 10/16/2026)','10/2026','The two informal readings in circulation, and the Department\'s request for the recording reference before it responds on letterhead'],
  ['Silver Butte Title email (N. Petrosyan)','10/26/2026','The title officer\'s 03/14/2028 reading, which is not supported by the record'],
  ['SNWA Compliance Bulletin WRC-2024-07, Nonfunctional Turf Prohibition (supersedes WRC-2022-04)','Q4 2024; compliance deadline 12/31/2026','The lot-based carve-out; HOA common-area parcels expressly covered; functional turf tests at §§3.1–3.4; the limits on waivers at §4'],
  ['CC Guidance Memorandum CP-PW-GM-2025-04, Shade and Canopy Guidance','March 2025','CC 30.64.030(k) at the medium-canopy tier; the 30% shade-coverage target and Shade Coverage Exhibit at §3; the limits of CC 30.64.050 at §4; irrigation methodology at §5(4)'],
  ['Phase 3 landscape sheets L-1 through L-4 (Ocotillo Landscape Studio)','08/21/2026','Frontage summary, plant schedule, L-1 compliance note, 18,400 sf of park turf, L-4 entry monument counts, unsigned seal blocks'],
  ['Phase 3 Common Area Turf and Planting Tabulation (Ocotillo)','08/15/2026','Frontage and tree counts; "Phase 3 turf located within a designated play area with playground amenities: 0 sf"'],
  ['Phase 3 Irrigation Demand Worksheet (Ocotillo)','08/15/2026','The rate basis and the current 3.28 ac-ft/yr demand'],
  ['Engineer\'s Estimate of Probable Cost (J. R. Kessler, PE, sealed)','10/10/2026, Revision 0','The bond basis of $5,357,000 and the unit prices for lines 7.02, 7.09, 7.11–7.14, 7.16, 7.17, 7.41 and 7.43 (7.01 is __not__ used — its 80,000 sf soil-preparation allowance already covers the planted footprint)'],
  ['Clark County Uniform Unit Cost Schedule for Bonding of Subdivision Improvements','Effective 01/01/2026','The unit prices used in the estimate, and Section 7 note (a): nonfunctional turf "shall not be included in the engineer\'s estimate for bonding"'],
  ['Enterprise TAB 2026 Calendar and Standard Agenda','2026','The 21-day application cut-off and 10-day posting rule; the 11/18/2026 and 12/16/2026 meeting dates'],
  ['Sagebrook Community Management letter (R. Meeker), on behalf of the Desert Sage Ranch HOA','10/17/2026','The association\'s playground-amenity request; the 11/18/2026 TAB attendance; the $2.85/sf conversion rate'],
  ['Vogel & Marsh memorandum (A. Vogel, Esq.)','10/20/2026','The client\'s position on the applicability of the AB 356 prohibition — addressed in §4'],
  ['Callaway direction email (G. Nokes)','10/22/2026','Instruction to treat L-2 and L-4 as clerical redlines, to use counsel\'s memo, and to return the package to Mr. Yeoman before month end'],
  ['CCWRD Sanitary Sewer Capacity Confirmation CCWRD-SCC-2025-1187','09/30/2025; expired 09/30/2026','Sewer capacity for 60 lots, and the requirement for written renewal and reissuance before plan approval'],
  ['LVVWD Will-Serve Commitment LVVWD-WS-2026-3341','07/22/2026; expires 07/22/2028','Water service for 60 lots and the conservation conditions of service'],
  ['Silver Butte Title preliminary report SBT-2026-04188','Effective 07/01/2026','Schedule B exceptions; currency to 01/01/2027 under the six-month test in comment M-4'],
  ['Desert Sage Ranch Phases 1 & 2 approved landscape set (Ocotillo)','2022','The 4,200 sf designated play area with installed playground amenities, against which the Phase 3 park is classified'],
  ['Internal design coordination email thread (Sundial / Ocotillo)','07/28/2026 – 10/09/2026','The playground amenities value-engineered out of the Phase 3 park; the L-3 turf callout and L-1 note held as drawn'],
  ['Resubmittal tracker (Sundial)','10/31/2026','Comment owners and due dates; Milestones, Budget and Outstanding Items tabs; the 12/18/2026 recordation target'],
 ],
 [2.55,1.15,2.8], font=8.1)

body('Prepared by Sundial Engineering & Survey, Job No. 2201-03, on 31 October 2026. Figures trace to the accompanying workbook, LS-01, tabs 1 through 5. This memorandum was not transmitted to Clark County Public Works or any other agency.', size=8.5, color=GREY, italic=True, space_after=0)

out = '/app/files/output/Callaway_L-Series_Turf_and_Schedule_Memo_2026-10-31.docx'
doc.save(out)
print('saved', out)
