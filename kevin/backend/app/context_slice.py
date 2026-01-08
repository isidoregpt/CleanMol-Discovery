import re
from typing import Dict, List

def page_text_map(paper_md: str) -> Dict[int, str]:
    pages = {}
    current = None
    buf = []
    for line in paper_md.splitlines():
        m = re.match(r"\[\[PAGE\s+(\d+)\]\]", line.strip())
        if m:
            if current is not None:
                pages[current] = "\n".join(buf).strip()
            current = int(m.group(1))
            buf = []
        else:
            buf.append(line)
    if current is not None:
        pages[current] = "\n".join(buf).strip()
    return pages

def slice_pages(paper_md: str, pages: List[int], pad: int = 1) -> str:
    pm = page_text_map(paper_md)
    want = set()
    for p in pages:
        for q in range(p - pad, p + pad + 1):
            if q in pm:
                want.add(q)
    selected = sorted(want)
    chunks = []
    for p in selected:
        chunks.append(f"[[PAGE {p}]]\n{pm[p]}")
    return "\n\n".join(chunks).strip()
