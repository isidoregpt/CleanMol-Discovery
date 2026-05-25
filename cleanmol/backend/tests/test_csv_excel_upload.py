from pathlib import Path

import pytest

from app.discovery_automation import _load_uploaded_rows


def test_csv_upload_parser_normalizes_activity_rows(tmp_path: Path):
    upload = tmp_path / "upload.csv"
    upload.write_text(
        "name,smiles,endpoint,value,units\n"
        "qac,CCCCCCCCCCCC[N+](C)(C)C,MIC,8,ug/mL\n",
        encoding="utf-8",
    )
    activity, toxicity, manifest = _load_uploaded_rows(upload, max_rows=100)
    assert len(activity) == 1
    assert toxicity == []
    assert manifest["status"] == "loaded"
    assert activity[0]["activity_label"] == "active"


def test_xlsx_upload_parser_normalizes_activity_rows(tmp_path: Path):
    openpyxl = pytest.importorskip("openpyxl")
    upload = tmp_path / "upload.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["name", "smiles", "endpoint", "value", "units"])
    sheet.append(["qac", "CCCCCCCCCCCC[N+](C)(C)C", "MIC", 8, "ug/mL"])
    workbook.save(upload)

    activity, toxicity, manifest = _load_uploaded_rows(upload, max_rows=100)
    assert len(activity) == 1
    assert toxicity == []
    assert manifest["status"] == "loaded"
