import fitz
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import json

def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def stable_doc_id(pdf_path: Path) -> str:
    h = hashlib.sha256()
    h.update(str(pdf_path.resolve()).encode("utf-8"))
    h.update(str(pdf_path.stat().st_size).encode("utf-8"))
    return "doc_" + h.hexdigest()[:12]

def extract_bundle(pdf_path: Path, bundle_root: Path) -> dict:
    doc_id = stable_doc_id(pdf_path)
    bundle_dir = bundle_root / doc_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    pdf = fitz.open(pdf_path)

    md_lines = []
    for page_idx, page in enumerate(pdf, start=1):
        text = page.get_text("text").strip()
        if not text:
            continue
        md_lines.append(f"\n\n[[PAGE {page_idx}]]\n")
        md_lines.append(text)

    paper_md = "\n".join(md_lines)
    (bundle_dir / "paper.md").write_text(paper_md, encoding="utf-8")

    metadata = {
        "doc_id": doc_id,
        "source_type": "paper",
        "filename": pdf_path.name,
        "path": str(pdf_path.resolve()),
        "pages": pdf.page_count,
        "created_at": _utc_iso(),
    }
    provenance = {
        "extraction": {"method": "PyMuPDF get_text(text)", "born_digital": True, "page_anchors": "[[PAGE N]]"}
    }

    (bundle_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (bundle_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    pdf.close()
    return {"doc_id": doc_id, "bundle_path": str(bundle_dir), "metadata": metadata}
