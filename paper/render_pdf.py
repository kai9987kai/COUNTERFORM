"""Rasterise every final PDF page for visual verification."""
from pathlib import Path
import json
import pypdfium2 as pdfium
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'output' / 'pdf' / 'counterform_pilot_paper.pdf'
output = ROOT / 'output' / 'paper-render'
output.mkdir(parents=True, exist_ok=True)
document = pdfium.PdfDocument(str(source))
reader = PdfReader(source)
pages = []
for i, page in enumerate(document):
    image = page.render(scale=1.5).to_pil()
    path = output / f'page-{i+1:02}.png'
    image.save(path)
    text = reader.pages[i].extract_text()
    assert '\ufffd' not in text
    pages.append({'page': i+1, 'words': len(text.split()), 'start': text[:180], 'end': text[-220:], 'image': path.name})
    page.close()
report = {'pdf': str(source), 'pages': pages, 'page_count': len(pages), 'total_words': sum(p['words'] for p in pages)}
(output / 'pdf-qa.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
