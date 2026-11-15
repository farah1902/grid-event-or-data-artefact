"""Check the highlights against the journal rules and write the Word copy for submission.

Rules (Applied Energy guide, recorded in paper/OUTLINE.md): 3-5 bullets, at most 85 characters each including spaces,
in a separate editable file with "highlights" in the file name. The source is paper/highlights.txt (one bullet per
line); this script checks it and writes paper/highlights.docx (one bulleted paragraph per highlight) without any
third-party package.
    python paper/tools/make_highlights.py
"""
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

PAPER = Path(__file__).resolve().parents[1]
SRC, OUT = PAPER / "highlights.txt", PAPER / "highlights.docx"
MAX_CHARS, N_RANGE = 85, (3, 5)

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def paragraph(text, bold=False):
    run_props = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:p><w:r>{run_props}<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def main():
    lines = [ln.strip() for ln in SRC.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ok = N_RANGE[0] <= len(lines) <= N_RANGE[1]
    print(f"{len(lines)} highlights ({'ok' if ok else 'must be 3-5'})")
    for ln in lines:
        flag = "ok" if len(ln) <= MAX_CHARS else "TOO LONG"
        print(f"  {len(ln):3d} {flag:8s} {ln}")
        ok &= len(ln) <= MAX_CHARS
    if not ok:
        sys.exit("highlights do not meet the rules; nothing written")
    body = paragraph("Highlights", bold=True) + "".join(paragraph("• " + ln) for ln in lines)
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"<w:body>{body}</w:body></w:document>")
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    print("written:", OUT)


if __name__ == "__main__":
    main()
