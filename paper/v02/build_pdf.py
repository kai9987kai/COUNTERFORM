"""Build the separate v0.2 paper without rewriting the published v0.1 paper."""
from pathlib import Path
import html
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / 'output/paper-deps', ROOT / 'output/v02-paper-deps'):
    if extra.exists(): sys.path.insert(0, str(extra))
from matplotlib import font_manager
from PIL import Image as PILImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether, PageBreak

PAPER = Path(__file__).resolve().parent
TARGET = ROOT / 'output/pdf/counterform_v02_development_paper.pdf'
WIDTH = A4[0] - 108


def inline(text):
    text = html.escape(text.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-').replace('\u2212', '-'))
    def link(match):
        label, url = match.groups()
        if not url.startswith('https://'):
            path = (PAPER / html.unescape(url)).resolve().relative_to(ROOT).as_posix()
            url = 'https://github.com/kai9987kai/COUNTERFORM/blob/main/' + path
        return f'<link href="{url}" color="#244e6b">{label}</link>'
    text = re.sub(r'\[([^]]+)\]\(([^)]+)\)', link, text)
    text = re.sub(r'`([^`]+)`', r'<font name="Mono" size="8">\1</font>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
    return text


def main():
    for name, family, weight, style in [('Serif','DejaVu Serif','normal','normal'), ('SerifBold','DejaVu Serif','bold','normal'),
                                       ('SerifItalic','DejaVu Serif','normal','italic'), ('SerifBoldItalic','DejaVu Serif','bold','italic'),
                                       ('Sans','DejaVu Sans','normal','normal'), ('SansBold','DejaVu Sans','bold','normal'),
                                       ('Mono','DejaVu Sans Mono','normal','normal')]:
        path = font_manager.findfont(font_manager.FontProperties(family=family, weight=weight, style=style), fallback_to_default=False)
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily('Serif', normal='Serif', bold='SerifBold', italic='SerifItalic', boldItalic='SerifBoldItalic')
    pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='SansBold', italic='Sans', boldItalic='SansBold')
    styles = {
        'body': ParagraphStyle('body', fontName='Serif', fontSize=10.2, leading=14.2, spaceAfter=7, allowWidows=0, allowOrphans=0),
        'title': ParagraphStyle('title', fontName='SerifBold', fontSize=20, leading=24, spaceAfter=13, keepWithNext=1),
        'h1': ParagraphStyle('h1', fontName='SansBold', fontSize=11.5, leading=15, spaceBefore=12, spaceAfter=7, keepWithNext=1),
        'h2': ParagraphStyle('h2', fontName='SansBold', fontSize=10, leading=13.5, spaceBefore=9, spaceAfter=5, keepWithNext=1),
        'caption': ParagraphStyle('caption', fontName='SerifItalic', fontSize=8.4, leading=11.4, spaceAfter=10),
        'ref': ParagraphStyle('ref', fontName='Serif', fontSize=9, leading=12, spaceAfter=7, splitLongWords=1),
        'th': ParagraphStyle('th', fontName='SansBold', fontSize=7.8, leading=10),
        'td': ParagraphStyle('td', fontName='Sans', fontSize=7.8, leading=10),
        'num': ParagraphStyle('num', fontName='Sans', fontSize=7.8, leading=10, alignment=TA_RIGHT),
        'code': ParagraphStyle('code', fontName='Mono', fontSize=7.6, leading=11, spaceAfter=3, splitLongWords=1),
    }
    styles['tablecaption'] = ParagraphStyle('tablecaption', parent=styles['caption'], keepWithNext=1)
    lines = ((PAPER/'manuscript.md').read_text(encoding='utf-8') + '\n' + (PAPER/'appendix.md').read_text(encoding='utf-8')).splitlines()
    story, buffer, index, refs, fenced = [], [], 0, False, False
    def flush():
        if buffer:
            text = ' '.join(buffer)
            paragraph = Paragraph(inline(text), styles['ref' if refs else 'body'])
            story.append(KeepTogether([paragraph]) if 'SHA-256' in text else paragraph)
            buffer.clear()
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith('```'):
            flush(); fenced = not fenced
        elif fenced:
            story.append(Paragraph(html.escape(line) or ' ', styles['code']))
        elif not line:
            flush()
        elif line.startswith('# '):
            flush(); story.append(Paragraph(inline(line[2:]), styles['title']))
        elif line.startswith('## '):
            flush(); heading = line[3:]; refs = heading == 'References'
            if heading.startswith('Appendix A'): story.append(PageBreak())
            story.append(Paragraph(inline(heading), styles['h1']))
        elif line.startswith('### '):
            flush(); story.append(Paragraph(inline(line[4:]), styles['h2']))
        elif line.startswith('|'):
            flush(); rows = []
            while index < len(lines) and lines[index].strip().startswith('|'):
                cells = [cell.strip() for cell in lines[index].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', cell) for cell in cells): rows.append(cells)
                index += 1
            n = len(rows[0])
            if n == 7 and rows[0][0] == 'Seed': fractions = [.075,.20,.125,.125,.07,.24,.165]
            elif n == 7: fractions = [.14,.20,.14,.14,.12,.13,.13]
            elif n == 6: fractions = [.25,.15,.15,.15,.15,.15]
            else: fractions = [1/n]*n
            cells = [[Paragraph(inline(value), styles['th' if row==0 else ('num' if re.match(r'^[-+]?\d', value) else 'td')])
                      for value in values] for row, values in enumerate(rows)]
            table = Table(cells, colWidths=[WIDTH*f/sum(fractions) for f in fractions], repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.35,colors.HexColor('#d0d6dc')),
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef3')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.append(table)
            if any(item.strip() for item in lines[index:]): story.append(Spacer(1,7))
            continue
        elif line.startswith('!['):
            flush(); match = re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)', line)
            if not match: raise ValueError('Invalid figure markup')
            path = PAPER / match.group(2)
            with PILImage.open(path) as source: width, height = source.size
            image = Image(str(path), width=WIDTH, height=WIDTH*height/width)
            index += 1
            while index < len(lines) and not lines[index].strip(): index += 1
            block = [Spacer(1,6),image,Spacer(1,5)]
            if index < len(lines) and re.match(r'^\*{1,2}Figure ', lines[index].strip()):
                block.append(Paragraph(inline(lines[index].strip()),styles['caption'])); index += 1
            story.append(KeepTogether(block)); continue
        elif re.match(r'^\*{1,2}(Figure|Table) ', line):
            flush(); story.append(Paragraph(inline(line),styles['tablecaption' if 'Table ' in line[:10] else 'caption']))
        elif line.startswith('- '):
            flush(); story.append(Paragraph(inline(line[2:]),styles['body'],bulletText='-'))
        else:
            buffer.append(line)
        index += 1
    flush()
    def footer(canvas, doc):
        canvas.saveState(); canvas.setFillColor(colors.HexColor('#626b73')); canvas.setFont('Sans',7.2)
        canvas.drawString(54,29,'COUNTERFORM v0.2 | Synthetic development study')
        canvas.drawRightString(A4[0]-54,29,str(doc.page)); canvas.restoreState()
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    doc = SimpleDocTemplate(str(TARGET),pagesize=A4,leftMargin=54,rightMargin=54,topMargin=45,bottomMargin=47,
        title=lines[0].removeprefix('# '),
        author='kai9987kai',subject='48-run synthetic development study; negative acquisition result',pageCompression=1)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(TARGET)


if __name__ == '__main__':
    main()
