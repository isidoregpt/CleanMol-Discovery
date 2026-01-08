import json
from pathlib import Path
from datetime import datetime

def export_jsonl(output_dir: Path, doc_id: str, extraction: dict) -> Path:
    exports = output_dir / "exports"
    exports.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base = exports / f"{doc_id}_{ts}"

    def write_jsonl(path: Path, rows):
        with path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    write_jsonl(Path(str(base) + "_molecules.jsonl"), extraction.get("molecules") or [])
    write_jsonl(Path(str(base) + "_experiments.jsonl"), extraction.get("experiments") or [])
    write_jsonl(Path(str(base) + "_results.jsonl"), extraction.get("results") or [])

    combined = []
    for m in extraction.get("molecules") or []:
        combined.append({"type": "molecule", **m})
    for e in extraction.get("experiments") or []:
        combined.append({"type": "experiment", **e})
    for r in extraction.get("results") or []:
        combined.append({"type": "result", **r})
    write_jsonl(Path(str(base) + "_dataset.jsonl"), combined)

    return exports
