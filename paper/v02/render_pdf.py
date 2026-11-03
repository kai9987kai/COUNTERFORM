"""Render all final pages with Poppler and extract independent PDF text checks."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
extra = ROOT / 'output/paper-deps'
if extra.exists(): sys.path.insert(0, str(extra))
from pypdf import PdfReader
from PIL import Image, ImageDraw

source = ROOT / 'output/pdf/counterform_v02_development_paper.pdf'
output = ROOT / 'output/paper-v02-render'
output.mkdir(parents=True, exist_ok=True)
for old_page in output.glob('page-*.png'):
    old_page.unlink()
subprocess.run(['pdftoppm', '-r', '110', '-png', str(source), str(output/'page')], check=True)
reader = PdfReader(source)
assert reader.metadata.author == 'kai9987kai'
pages = []
for index, page in enumerate(reader.pages):
    text = page.extract_text()
    assert '\ufffd' not in text and len(text.split()) > 12
    pages.append({'page':index+1,'words':len(text.split()),'start':text[:160],'end':text[-180:]})
all_text = '\n'.join(page.extract_text() for page in reader.pages)
for required in ('48', '12', '28', '29', 'Appendix A', 'kai9987kai', 'References'):
    assert required in all_text, required
assert 'TODO' not in all_text and 'placeholder' not in all_text.lower()
images = sorted(output.glob('page-*.png'))
assert len(images) == len(reader.pages)
for start in range(0,len(images),6):
    sheet = Image.new('RGB',(1300,2860),'#c9cdd1')
    draw = ImageDraw.Draw(sheet)
    for offset,path in enumerate(images[start:start+6]):
        with Image.open(path) as page:
            page.thumbnail((625,900))
            x,y = (offset%2)*650+12,(offset//2)*950+30
            sheet.paste(page,(x,y))
            draw.text((x,y-20),f'Page {start+offset+1}',fill='black')
    sheet.save(output/f'contact-{start//6+1}.png')
report = {'pdf':str(source),'page_count':len(reader.pages),'total_words':sum(p['words'] for p in pages),'pages':pages}
(output/'pdf-qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
