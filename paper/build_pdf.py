"""Render the editable Markdown manuscript to an embedded-font research PDF."""
from __future__ import annotations

from pathlib import Path
import html
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXTRA = ROOT / 'output' / 'paper-deps'
if EXTRA.exists():
    sys.path.insert(0, str(EXTRA))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image as PILImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether, PageBreak

PAPER = ROOT / 'paper'
OUT = ROOT / 'output' / 'pdf'
OUT.mkdir(parents=True, exist_ok=True)
TMP = ROOT / 'output' / 'paper-render'
TMP.mkdir(parents=True, exist_ok=True)
WIDTH = A4[0] - 108


def fonts():
    variants = [('Serif', 'DejaVu Serif', 'normal', 'normal'), ('SerifBold', 'DejaVu Serif', 'bold', 'normal'),
                ('SerifItalic', 'DejaVu Serif', 'normal', 'italic'), ('SerifBoldItalic', 'DejaVu Serif', 'bold', 'italic'),
                ('Sans', 'DejaVu Sans', 'normal', 'normal'), ('SansBold', 'DejaVu Sans', 'bold', 'normal'),
                ('Mono', 'DejaVu Sans Mono', 'normal', 'normal')]
    for name, family, weight, style in variants:
        path = font_manager.findfont(font_manager.FontProperties(family=family, weight=weight, style=style), fallback_to_default=False)
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily('Serif', normal='Serif', bold='SerifBold', italic='SerifItalic', boldItalic='SerifBoldItalic')
    pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='SansBold', italic='Sans', boldItalic='SansBold')


def inline(text):
    text = text.replace('–', '-').replace('—', '-').replace('−', '-')
    text = html.escape(text)
    text = re.sub(r'`([^`]+)`', r'<font name="Mono" size="8.7">\1</font>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(https://[^\s<]+)', r'<link href="\1" color="#163a5a">\1</link>', text)
    for token, value in [('w_tilde_h', '<i>w̃</i><sub>h</sub>'), ('omega_ref', 'ω<sub>ref</sub>'),
                         ('zeta_a', 'ζ<sub>a</sub>'), ('w_bar', '<i>w̄</i>'), ('H_*', '<i>H</i><sub>*</sub>'),
                         ('sum_h', 'Σ<sub>h</sub>'), ('min_j', 'min<sub>j</sub>')]:
        text = text.replace(token, value)
    for word, symbol in [('omega', 'ω'), ('alpha', 'α'), ('sigma', 'σ'), ('eta', 'η'), ('mu', 'μ')]:
        text = re.sub(r'\b'+word+r'\b', symbol, text)
    text = re.sub(r'\b([a-zA-Z])_([a-zA-Z])\b', r'<i>\1</i><sub>\2</sub>', text)
    text = re.sub(r'\^(-?\d+)', r'<super>\1</super>', text)
    return text


def equation(latex, number):
    path = TMP / f'equation-{number}.png'
    fig = plt.figure(figsize=(8, .6), dpi=320)
    fig.text(.5, .5, '$' + latex + '$', ha='center', va='center', fontsize=13,
             math_fontfamily='stix', color='black')
    fig.savefig(path, dpi=320, bbox_inches='tight', pad_inches=.04, facecolor='white')
    plt.close(fig)
    im = PILImage.open(path)
    w, h = im.size
    width = min(WIDTH-20, w/320*72)
    image = Image(str(path), width=width, height=width*h/w)
    image.hAlign = 'CENTER'
    return [Spacer(1, 3), image, Spacer(1, 8)]


def make_table(lines, styles):
    rows = [[c.strip() for c in line.strip().strip('|').split('|')] for line in lines]
    rows = [r for r in rows if not all(re.fullmatch(r':?-+:?', c or ' ') for c in r)]
    n = len(rows[0])
    if n == 5 and rows[0][0] == 'Condition':
        fractions = [.32, .14, .11, .10, .33]
    elif n == 5:
        fractions = [.16, .23, .18, .26, .17]
    elif n == 6:
        fractions = [.18, .08, .25, .16, .18, .15]
    else:
        fractions = [1/n]*n
    # Protocol column fractions sum to one after normalisation.
    widths = [WIDTH*v/sum(fractions) for v in fractions]
    data = [[Paragraph(inline(cell), styles['th' if ri == 0 else ('tdnum' if re.match(r'^[-+]?\d', cell) else 'td')])
             for cell in row] for ri, row in enumerate(rows)]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#d9d9d9')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8edf1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    return table


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Sans', 7.4)
    canvas.setFillColor(colors.HexColor('#626262'))
    canvas.drawString(54, 29, 'COUNTERFORM | Synthetic pilot study')
    canvas.drawRightString(A4[0]-54, 29, str(doc.page))
    canvas.restoreState()


def main():
    fonts()
    black = colors.black
    styles = {
        'body': ParagraphStyle('body', fontName='Serif', fontSize=10.45, leading=14.45, spaceAfter=7.5, textColor=black, allowWidows=0, allowOrphans=0),
        'title': ParagraphStyle('title', fontName='SerifBold', fontSize=19, leading=23.5, spaceAfter=12, textColor=black, keepWithNext=1),
        'h1': ParagraphStyle('h1', fontName='SansBold', fontSize=12, leading=16, spaceBefore=13, spaceAfter=7.5, textColor=black, keepWithNext=1),
        'h2': ParagraphStyle('h2', fontName='SansBold', fontSize=10.4, leading=14, spaceBefore=9, spaceAfter=5, textColor=black, keepWithNext=1),
        'caption': ParagraphStyle('caption', fontName='SerifItalic', fontSize=8.8, leading=12, spaceBefore=5, spaceAfter=11, textColor=black),
        'ref': ParagraphStyle('ref', fontName='Serif', fontSize=9.1, leading=12.6, spaceAfter=7, textColor=black, allowWidows=0, allowOrphans=0),
        'th': ParagraphStyle('th', fontName='SansBold', fontSize=8.5, leading=11.2, textColor=black),
        'td': ParagraphStyle('td', fontName='Sans', fontSize=8.5, leading=11.2, textColor=black),
        'tdnum': ParagraphStyle('tdnum', fontName='Sans', fontSize=8.5, leading=11.2, textColor=black, alignment=TA_RIGHT),
    }
    lines = (PAPER / 'manuscript.md').read_text(encoding='utf-8').splitlines()
    story, buffer = [], []
    i, eq_num, in_refs = 0, 0, False
    pending_math_intro = None

    def flush():
        nonlocal pending_math_intro
        if buffer:
            text = ' '.join(buffer).strip()
            style = styles['ref'] if in_refs else styles['body']
            para = Paragraph(inline(text), style)
            following = i
            while following < len(lines) and not lines[following].strip():
                following += 1
            if following < len(lines) and lines[following].strip() == '$$':
                pending_math_intro = para
            else:
                story.append(para)
            buffer.clear()

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            flush(); i += 1; continue
        if line.startswith('# '):
            flush(); story.append(Paragraph(inline(line[2:]), styles['title']))
        elif line.startswith('## '):
            flush()
            heading = line[3:]
            if heading.startswith('Appendix A'):
                story.append(PageBreak())
            in_refs = heading == 'References'
            story.append(Paragraph(inline(heading), styles['h1']))
        elif line.startswith('### '):
            flush(); story.append(Paragraph(inline(line[4:]), styles['h2']))
        elif line == '$$':
            flush(); math_lines = []; i += 1
            while i < len(lines) and lines[i].strip() != '$$':
                math_lines.append(lines[i].strip()); i += 1
            eq_num += 1
            story.append(KeepTogether(([pending_math_intro] if pending_math_intro else []) + equation(' '.join(math_lines), eq_num)))
            pending_math_intro = None
        elif line.startswith('|'):
            flush(); table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i]); i += 1
            table = make_table(table_lines, styles)
            while i < len(lines) and not lines[i].strip(): i += 1
            caption = None
            if i < len(lines) and lines[i].strip().startswith('*Table '):
                caption = Paragraph(inline(lines[i].strip().strip('*')), styles['caption']); i += 1
            story.append(KeepTogether([table] + ([caption] if caption else [])))
            continue
        elif line.startswith('!['):
            flush(); match = re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)', line)
            if not match: raise ValueError('Invalid image markup')
            path = PAPER / match.group(2)
            with PILImage.open(path) as im: w, h = im.size
            image = Image(str(path), width=WIDTH, height=WIDTH*h/w)
            i += 1
            while i < len(lines) and not lines[i].strip(): i += 1
            block = [Spacer(1, 6), image]
            if i < len(lines) and lines[i].strip().startswith('*Figure '):
                block.append(Paragraph(inline(lines[i].strip().strip('*')), styles['caption'])); i += 1
            story.append(KeepTogether(block)); continue
        elif line.startswith('*Figure ') or line.startswith('*Table '):
            flush(); story.append(Paragraph(inline(line.strip('*')), styles['caption']))
        else:
            buffer.append(line)
        i += 1
    flush()
    target = OUT / 'counterform_pilot_paper.pdf'
    doc = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=54, rightMargin=54, topMargin=43, bottomMargin=45,
                            title='COUNTERFORM A Synthetic Pilot Study of Experiment Selection and Model Adequacy',
                            author='kai9987kai', subject='Descriptive synthetic pilot and negative results',
                            pageCompression=1, allowSplitting=1)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(target)
    print(f'{eq_num} equations rendered; manuscript words:', len((PAPER/'manuscript.md').read_text(encoding='utf-8').split()))


if __name__ == '__main__':
    main()
