from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

doc=Document('Callaway_L-Series_Turf_and_Schedule_Memo_2026-10-31.docx')
def iter_block(parent):
    body=parent.element.body
    for child in body.iterchildren():
        if child.tag==qn('w:p'): yield Paragraph(child,parent)
        elif child.tag==qn('w:tbl'): yield Table(child,parent)

out=[]
out.append('# Callaway L-Series Turf and Schedule Memorandum — final text\n')
out.append('*Transcription of `Callaway_L-Series_Turf_and_Schedule_Memo_2026-10-31.docx` as issued. '
           'Generated directly from the DOCX so that the markdown, the DOCX and the PDF carry identical text. '
           'Formatting, letterhead and page furniture are omitted; nothing else is.*\n')
out.append('---\n')
for b in iter_block(doc):
    if isinstance(b, Paragraph):
        t=b.text.strip()
        if not t: continue
        style=b.style.name if b.style is not None else ''
        if style.startswith('Heading 1'):
            out.append('\n## '+t+'\n')
        elif style.startswith('Heading 2'):
            out.append('\n### '+t+'\n')
        elif t.startswith('\u2022'):
            out.append('- '+t.lstrip('\u2022').strip())
        else:
            out.append(t+'\n')
    else:
        rows=[[c.text.strip().replace('\n',' ') for c in r.cells] for r in b.rows]
        if not rows: continue
        hdr=rows[0]; body=rows[1:]
        out.append('| '+' | '.join(hdr)+' |')
        out.append('|'+'|'.join(['---']*len(hdr))+'|')
        for r in body:
            out.append('| '+' | '.join(r)+' |')
        out.append('')
open('drafts/Callaway_L-Series_Turf_and_Schedule_Memo_2026-10-31_DRAFT.md','w').write('\n'.join(out))
print('written', len('\n'.join(out)))
