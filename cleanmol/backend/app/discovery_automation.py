"""
Automated discovery workflow for CleanMol.

This module turns CleanMol's extracted dataset and optional user/public datasets
into a ranked candidate packet. It is intentionally provenance-heavy: synthetic
or heuristic rows are marked as priors, not experimental truth.
"""
from __future__ import annotations

import csv
import datetime as dt
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .discovery_filters import enrich_modern_discovery_fields, is_generation_seed
from .dataset_quality import assess_dataset_quality
from .online_source_catalog import CURATED_SOURCE_CATALOG, get_sources_by_id
from .integrations.rdkit_baseline import MorganBaseline, build_morgan_baseline, score_candidate_against_baseline
from .integrations.status import get_integration_status

try:
    import requests
except ImportError:  # pragma: no cover - backend requirements install requests
    requests = None

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill
except ImportError:  # pragma: no cover - backend requirements install openpyxl
    Workbook = None
    load_workbook = None
    Font = None
    PatternFill = None


ProgressCallback = Optional[Callable[[str], None]]


HF_DATASET_PRESETS = [
    source
    for source in CURATED_SOURCE_CATALOG
    if source.get("connector") == "huggingface" and source.get("default_selected")
]


DEFAULT_STARTER_SEEDS = [
    {
        "molecule_id": "starter_qac_c12",
        "name": "modern QAC C12 starter",
        "smiles": "CCCCCCCCCCCC[N+](C)(C)C",
        "source": "cleanmol_starter_prior",
        "chain_lengths": [12],
    },
    {
        "molecule_id": "starter_benzyl_qac_c12",
        "name": "benzyl QAC C12 starter",
        "smiles": "CCCCCCCCCCCC[N+](C)(C)Cc1ccccc1",
        "source": "cleanmol_starter_prior",
        "chain_lengths": [12],
    },
    {
        "molecule_id": "starter_phosphonium_c12",
        "name": "phosphonium C12 starter",
        "smiles": "CCCCCCCCCCCC[P+](C)(C)C",
        "source": "cleanmol_starter_prior",
        "chain_lengths": [12],
    },
    {
        "molecule_id": "starter_gemini_qac_c10_l3",
        "name": "gemini bis-QAC C10 linker-3 starter",
        "smiles": "CCCCCCCCCC[N+](C)(C)CCC[N+](C)(C)CCCCCCCCCC",
        "source": "cleanmol_starter_prior",
        "chain_lengths": [10, 10],
        "linker_lengths": [3],
    },
]


PUBLIC_RELEASE_DISCLAIMER = (
    "CleanMol Discovery is an early-stage research triage tool.\n\n"
    "It helps organize chemistry data, generate disinfectant-relevant molecular hypotheses, "
    "and prioritize candidates for expert review.\n\n"
    "It does not prove antimicrobial activity, safety, synthesizability, formulation stability, "
    "environmental acceptability, regulatory compliance, or commercial suitability.\n\n"
    "Candidate rankings are not probabilities and are not laboratory results.\n\n"
    "Any candidate considered for real-world follow-up requires independent review by qualified "
    "chemists, microbiologists, toxicologists, formulation scientists, regulatory experts, and "
    "laboratory testing.\n"
)

TRIAGE_SCORE_LIMITATION = "Rank scores are triage scores. They are not probabilities and are not laboratory results."


def _emit(progress_callback: ProgressCallback, stage: str, event: str, **payload: Any) -> None:
    if not progress_callback:
        return
    progress_callback(json.dumps({"type": "discovery_progress", "stage": stage, "event": event, **payload}))


def _sanitize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _find_column(row: Dict[str, Any], candidates: Iterable[str]) -> Optional[str]:
    normalized = {key.lower().strip().replace(" ", "_"): key for key in row.keys()}
    for candidate in candidates:
        key = candidate.lower().strip().replace(" ", "_")
        if key in normalized:
            return normalized[key]
    for candidate in candidates:
        needle = candidate.lower().strip().replace(" ", "_")
        for norm_key, original in normalized.items():
            if needle in norm_key:
                return original
    return None


def _read_csv_rows(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        for row in reader:
            rows.append(dict(row))
            if limit and len(rows) >= limit:
                break
    return rows


def _read_xlsx_rows(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if load_workbook is None:
        raise RuntimeError("openpyxl is required to read Excel uploads")
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    iterator = ws.iter_rows(values_only=True)
    headers = [str(cell).strip() if cell is not None else "" for cell in next(iterator, [])]
    rows: List[Dict[str, Any]] = []
    for values in iterator:
        row = {headers[idx]: values[idx] if idx < len(values) else None for idx in range(len(headers))}
        rows.append(row)
        if limit and len(rows) >= limit:
            break
    return rows


def _read_table_rows(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return _read_xlsx_rows(path, limit=limit)
    return _read_csv_rows(path, limit=limit)


def _normalize_activity_row(row: Dict[str, Any], source_name: str) -> Optional[Dict[str, Any]]:
    smiles_col = _find_column(row, ["smiles", "canonical_smiles", "SMILES", "TargetMolecule"])
    if not smiles_col:
        return None
    smiles = _sanitize_text(row.get(smiles_col))
    if not smiles:
        return None

    name_col = _find_column(row, ["name", "molecule", "compound", "compound_name", "pubchem_name"])
    organism_col = _find_column(row, ["organism", "strain", "species", "target_organism"])
    endpoint_col = _find_column(row, ["endpoint", "assay_type", "property_name", "measurement_type"])
    units_col = _find_column(row, ["units", "unit"])
    value_col = _find_column(row, ["value", "mic", "mbc", "log_reduction", "activity"])

    mic_candidates = [
        row.get(key)
        for key in row
        if "mic" in key.lower() and _safe_float(row.get(key)) is not None
    ]
    mic_value = _safe_float(row.get(value_col)) if value_col else None
    if mic_value is None and mic_candidates:
        mic_value = min(_safe_float(value) for value in mic_candidates if _safe_float(value) is not None)

    activity_label = ""
    if mic_value is not None:
        activity_label = "active" if mic_value <= 32 else "inactive"

    return {
        "smiles": smiles,
        "molecule_name": _sanitize_text(row.get(name_col)) if name_col else "",
        "organism": _sanitize_text(row.get(organism_col)) if organism_col else "",
        "assay_type": _sanitize_text(row.get(endpoint_col)) if endpoint_col else "activity",
        "endpoint": _sanitize_text(row.get(endpoint_col)) if endpoint_col else "",
        "value": mic_value if mic_value is not None else (_safe_float(row.get(value_col)) if value_col else ""),
        "units": _sanitize_text(row.get(units_col)) if units_col else "",
        "activity_label": activity_label,
        "source": source_name,
        "provenance": "experimental_or_imported",
    }


def _normalize_toxicity_row(row: Dict[str, Any], source_name: str) -> Optional[Dict[str, Any]]:
    smiles_col = _find_column(row, ["smiles", "canonical_smiles", "SMILES", "TargetMolecule"])
    if not smiles_col:
        return None
    smiles = _sanitize_text(row.get(smiles_col))
    if not smiles:
        return None

    tox_values = []
    for key, value in row.items():
        key_lower = key.lower()
        if key_lower.startswith(("nr-", "sr-")) or "tox" in key_lower or "cytotox" in key_lower or "hemolysis" in key_lower:
            numeric = _safe_float(value)
            if numeric is not None:
                tox_values.append(numeric)

    tox_score = ""
    if tox_values:
        tox_score = round(sum(tox_values) / len(tox_values), 4)

    return {
        "smiles": smiles,
        "toxicity_endpoint": "toxicity_multitask_mean" if tox_values else "",
        "toxicity_value": tox_score,
        "toxicity_label": "risk_flag" if isinstance(tox_score, float) and tox_score >= 0.5 else "",
        "source": source_name,
        "provenance": "experimental_or_imported",
    }


def _load_existing_cleanmol_rows(output_dir: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    activity_rows: List[Dict[str, Any]] = []
    toxicity_rows: List[Dict[str, Any]] = []
    analysis_path = output_dir / "analysis_ready.csv"
    if not analysis_path.exists():
        return activity_rows, toxicity_rows

    for row in _read_csv_rows(analysis_path):
        normalized = _normalize_activity_row(row, "cleanmol_analysis_ready")
        if normalized:
            activity_rows.append(normalized)
        hc50 = _safe_float(row.get("HC50"))
        smiles = _sanitize_text(row.get("smiles"))
        if smiles and hc50 is not None:
            toxicity_rows.append(
                {
                    "smiles": smiles,
                    "toxicity_endpoint": "HC50",
                    "toxicity_value": hc50,
                    "toxicity_label": "lower_is_more_toxic",
                    "source": "cleanmol_analysis_ready",
                    "provenance": "experimental_or_imported",
                }
            )
    return activity_rows, toxicity_rows


def _load_uploaded_rows(path: Optional[Path], max_rows: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    if not path:
        return [], [], {"status": "not_provided"}
    if not path.exists():
        return [], [], {"status": "missing", "path": str(path)}

    rows = _read_table_rows(path, limit=max_rows)
    activity_rows = []
    toxicity_rows = []
    for row in rows:
        activity = _normalize_activity_row(row, f"chemist_upload:{path.name}")
        if activity:
            activity_rows.append(activity)
        toxicity = _normalize_toxicity_row(row, f"chemist_upload:{path.name}")
        if toxicity and toxicity.get("toxicity_value") != "":
            toxicity_rows.append(toxicity)

    return activity_rows, toxicity_rows, {
        "status": "loaded",
        "path": str(path),
        "rows_read": len(rows),
        "activity_rows": len(activity_rows),
        "toxicity_rows": len(toxicity_rows),
    }


def _resolve_hf_split(dataset_id: str, token: str = "") -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    if requests is None:
        return None, None, {"status": "dependency_missing", "dataset": dataset_id, "error": "requests is not installed"}
    url = "https://datasets-server.huggingface.co/splits"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.get(url, params={"dataset": dataset_id}, headers=headers, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    splits = payload.get("splits") or []
    if not splits:
        return None, None, {"status": "no_splits", "dataset": dataset_id}
    first = splits[0]
    return first.get("config"), first.get("split"), {"status": "resolved", "split": first}


def _fetch_hf_rows(dataset_id: str, max_rows: int, token: str = "") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    config, split, meta = _resolve_hf_split(dataset_id, token=token)
    if not config or not split:
        return [], meta
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    rows: List[Dict[str, Any]] = []
    offset = 0
    while len(rows) < max_rows:
        length = min(100, max_rows - len(rows))
        resp = requests.get(
            "https://datasets-server.huggingface.co/rows",
            params={"dataset": dataset_id, "config": config, "split": split, "offset": offset, "length": length},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        page_rows = [item.get("row") or {} for item in payload.get("rows", [])]
        if not page_rows:
            break
        rows.extend(page_rows)
        offset += len(page_rows)
        if len(page_rows) < length:
            break
    return rows, {"status": "loaded", "dataset": dataset_id, "config": config, "split": split, "rows": len(rows)}


def _fetch_chembl_antimicrobial_rows(max_rows: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if requests is None:
        return [], {"status": "dependency_missing", "source": "chembl", "error": "requests is not installed"}

    endpoint_terms = ["MIC", "MBC"]
    assay_terms = ["antibacterial", "antimicrobial", "bacteria", "biofilm", "Staphylococcus", "Escherichia", "Pseudomonas"]
    rows: List[Dict[str, Any]] = []
    errors = []

    for standard_type in endpoint_terms:
        for assay_term in assay_terms:
            if len(rows) >= max_rows:
                break
            try:
                resp = requests.get(
                    "https://www.ebi.ac.uk/chembl/api/data/activity.json",
                    params={
                        "limit": min(100, max_rows - len(rows)),
                        "standard_type": standard_type,
                        "assay_description__icontains": assay_term,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                payload = resp.json()
                for item in payload.get("activities", []):
                    smiles = _sanitize_text(item.get("canonical_smiles"))
                    if not smiles:
                        continue
                    rows.append(
                        {
                            "smiles": smiles,
                            "molecule_name": item.get("molecule_chembl_id") or "",
                            "organism": item.get("target_organism") or item.get("target_pref_name") or "",
                            "assay_type": item.get("assay_type") or "",
                            "endpoint": item.get("standard_type") or standard_type,
                            "value": item.get("standard_value") or "",
                            "units": item.get("standard_units") or "",
                            "activity_label": "active" if _safe_float(item.get("standard_value")) is not None else "",
                            "source": "chembl:antimicrobial-mic",
                            "provenance": "public_database",
                        }
                    )
                    if len(rows) >= max_rows:
                        break
            except Exception as exc:
                errors.append(f"{standard_type}/{assay_term}: {exc}")
        if len(rows) >= max_rows:
            break

    return rows, {
        "status": "loaded" if rows else "empty_or_error",
        "source": "chembl:antimicrobial-mic",
        "rows": len(rows),
        "errors": errors[:5],
    }


def _load_public_source_rows(options: Dict[str, Any], keys: Dict[str, str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not options.get("include_public_sources"):
        return [], [], [{"status": "skipped", "reason": "include_public_sources is false"}]

    max_rows = int(options.get("max_public_rows") or 250)
    token = keys.get("hf") or keys.get("huggingface") or ""
    selected_source_ids = options.get("selected_source_ids")
    selected_sources = get_sources_by_id(selected_source_ids)
    known_ids = {source["id"] for source in selected_sources}
    for source_id in selected_source_ids or []:
        if source_id in known_ids or not str(source_id).startswith("hf:"):
            continue
        dataset_id = str(source_id).replace("hf:", "", 1)
        selected_sources.append(
            {
                "id": source_id,
                "connector": "huggingface",
                "dataset_id": dataset_id,
                "role": "activity_reference",
                "use_guidance": "User-selected Hugging Face search result; inspect provenance before trusting labels.",
                "pull_supported": True,
            }
        )
    manifests: List[Dict[str, Any]] = []
    activity_rows: List[Dict[str, Any]] = []
    toxicity_rows: List[Dict[str, Any]] = []

    for preset in selected_sources:
        connector = preset.get("connector")
        if connector == "chembl" and preset.get("id") == "chembl:antimicrobial-mic":
            rows, meta = _fetch_chembl_antimicrobial_rows(max_rows=max_rows)
            meta.update({"role": preset.get("role"), "reason": preset.get("use_guidance")})
            manifests.append(meta)
            activity_rows.extend(rows)
            continue

        if connector != "huggingface" or not preset.get("pull_supported"):
            manifests.append(
                {
                    "status": "not_pulled",
                    "source": preset.get("id"),
                    "role": preset.get("role"),
                    "reason": preset.get("use_guidance") or "Pull not supported for this source yet.",
                }
            )
            continue

        dataset_id = preset.get("dataset_id") or preset.get("id", "").replace("hf:", "", 1)
        try:
            rows, meta = _fetch_hf_rows(dataset_id, max_rows=max_rows, token=token)
            meta.update({"role": preset.get("role"), "reason": preset.get("use_guidance")})
            manifests.append(meta)
            for row in rows:
                if preset.get("role") in {"activity_reference", "generative_prior"}:
                    activity = _normalize_activity_row(row, f"huggingface:{dataset_id}")
                    if activity:
                        activity["provenance"] = "public_dataset"
                        activity_rows.append(activity)
                if preset.get("role") == "toxicity_selectivity":
                    toxicity = _normalize_toxicity_row(row, f"huggingface:{dataset_id}")
                    if toxicity:
                        toxicity["provenance"] = "public_dataset"
                        toxicity_rows.append(toxicity)
                if preset.get("role") == "liability_filter":
                    toxicity = _normalize_toxicity_row(row, f"huggingface:{dataset_id}")
                    if toxicity:
                        toxicity["provenance"] = "public_dataset_liability_filter"
                        toxicity_rows.append(toxicity)
        except Exception as exc:
            manifests.append(
                {
                    "status": "error",
                    "dataset": dataset_id,
                    "role": preset.get("role"),
                    "reason": preset.get("use_guidance"),
                    "error": str(exc),
                }
            )

    return activity_rows, toxicity_rows, manifests


def _write_csv(path: Path, rows: List[Dict[str, Any]], headers: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _infer_uma_readiness(molecule: Dict[str, Any]) -> Tuple[str, str]:
    smiles = molecule.get("smiles")
    if not smiles:
        return "missing_smiles", "No SMILES available."
    if molecule.get("smiles_valid") is False:
        return "invalid_smiles", molecule.get("smiles_error") or "SMILES failed validation."

    fragment_count = molecule.get("fragment_count")
    formal_charge = molecule.get("formal_charge")
    if fragment_count is None or formal_charge is None:
        if molecule.get("stable_cationic_center_count", 0):
            return "needs_charge_review", "Charged candidate; confirm total charge, counterion handling, and spin multiplicity before UMA."
        return "needs_structure_review", "RDKit charge/fragment metadata is missing; rerun validation with RDKit before UMA."

    try:
        if int(fragment_count) > 1:
            return "needs_fragment_review", "Disconnected fragments or salt/counterion detected; decide what to model."
    except (TypeError, ValueError):
        pass

    try:
        if int(formal_charge) != 0:
            return "needs_charge_review", "Charged molecule; confirm total_charge and spin_multiplicity before UMA task omol."
    except (TypeError, ValueError):
        pass

    return "candidate", "Candidate for RDKit 3D conformer generation and UMA task omol; confirm spin multiplicity."


def _load_seed_molecules(output_dir: Path, activity_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seed_path = output_dir / "candidate_generation_seed.smi"
    seeds: List[Dict[str, Any]] = []
    if seed_path.exists():
        with seed_path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                parts = line.strip().split()
                if not parts:
                    continue
                molecule = {
                    "molecule_id": parts[1] if len(parts) > 1 else f"seed_{idx + 1}",
                    "name": parts[1] if len(parts) > 1 else f"seed_{idx + 1}",
                    "smiles": parts[0],
                    "source": "candidate_generation_seed.smi",
                }
                enrich_modern_discovery_fields(molecule)
                if is_generation_seed(molecule):
                    seeds.append(molecule)

    for idx, row in enumerate(activity_rows[:500]):
        smiles = _sanitize_text(row.get("smiles"))
        if not smiles:
            continue
        molecule = {
            "molecule_id": f"activity_seed_{idx + 1}",
            "name": row.get("molecule_name") or f"activity_seed_{idx + 1}",
            "smiles": smiles,
            "source": row.get("source") or "activity_table",
        }
        enrich_modern_discovery_fields(molecule)
        if is_generation_seed(molecule):
            seeds.append(molecule)

    if not seeds:
        for starter in DEFAULT_STARTER_SEEDS:
            molecule = dict(starter)
            enrich_modern_discovery_fields(molecule)
            seeds.append(molecule)

    deduped: Dict[str, Dict[str, Any]] = {}
    for seed in seeds:
        deduped.setdefault(seed["smiles"], seed)
    return list(deduped.values())


def _alkyl(length: int) -> str:
    return "C" * max(1, int(length))


def _builtin_generate_candidates(seeds: List[Dict[str, Any]], target_count: int) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    seen = set()
    tails = [8, 10, 12, 14, 16]
    linkers = [2, 3, 4, 6]

    templates = []
    for tail in tails:
        templates.extend(
            [
                ("qac_trimethyl", f"{_alkyl(tail)}[N+](C)(C)C", [tail], []),
                ("benzyl_qac", f"{_alkyl(tail)}[N+](C)(C)Cc1ccccc1", [tail], []),
                ("phosphonium", f"{_alkyl(tail)}[P+](C)(C)C", [tail], []),
                ("pyridinium", f"{_alkyl(tail)}[n+]1ccccc1", [tail], []),
            ]
        )
    for tail_a in [8, 10, 12, 14]:
        for tail_b in [6, 8, 10, 12, 14, 16]:
            templates.append(
                (
                    "dialkyl_dimethyl_qac",
                    f"{_alkyl(tail_a)}[N+](C)(C){_alkyl(tail_b)}",
                    [tail_a, tail_b],
                    [],
                )
            )
    for tail in [8, 10, 12]:
        for linker in linkers:
            templates.append(
                (
                    "gemini_bis_qac",
                    f"{_alkyl(tail)}[N+](C)(C){_alkyl(linker)}[N+](C)(C){_alkyl(tail)}",
                    [tail, tail],
                    [linker],
                )
            )

    seed_ids = [seed.get("molecule_id") or f"seed_{idx + 1}" for idx, seed in enumerate(seeds)]
    for idx, (family, smiles, chains, linkers_) in enumerate(templates):
        if smiles in seen:
            continue
        seen.add(smiles)
        source_seed = seed_ids[idx % len(seed_ids)] if seed_ids else "starter_prior"
        candidate = {
            "candidate_id": f"GEN-{len(candidates) + 1:04d}",
            "name": f"{family}_variant_{len(candidates) + 1:04d}",
            "smiles": smiles,
            "generator_engine": "cleanmol_builtin_de_novo",
            "source_seed_id": source_seed,
            "generation_provenance": "rule_based_de_novo_prior",
            "chain_lengths": chains,
            "linker_lengths": linkers_,
            "family": family,
        }
        enrich_modern_discovery_fields(candidate)
        candidates.append(candidate)
        if len(candidates) >= target_count:
            break

    return candidates


def _run_reinvent_if_available(
    discovery_dir: Path,
    seeds: List[Dict[str, Any]],
    target_count: int,
    timeout_seconds: int,
    config_path: Optional[str] = None,
    enabled: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not enabled:
        return [], {"status": "disabled", "reason": "REINVENT 4 integration disabled for this run"}

    reinvent = shutil.which("reinvent")
    if not reinvent:
        return [], {"status": "not_installed", "reason": "reinvent executable not found on PATH"}

    run_dir = discovery_dir / "reinvent_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    seed_file = run_dir / "reinvent_seed.smi"
    with seed_file.open("w", encoding="utf-8") as f:
        for seed in seeds:
            f.write(f"{seed['smiles']}\t{seed.get('molecule_id', 'seed')}\n")

    # REINVENT configs vary by installed version. CleanMol writes the seed file
    # and launches a user-provided TOML if present; otherwise it falls back.
    resolved_config_path = Path(config_path).expanduser() if config_path else run_dir / "reinvent.toml"
    if not resolved_config_path.exists():
        return [], {
            "status": "config_missing",
            "reason": "REINVENT is installed, but no reinvent.toml exists yet.",
            "seed_file": str(seed_file),
            "config_path": str(resolved_config_path),
        }

    log_path = run_dir / "reinvent.log"
    try:
        completed = subprocess.run(
            [reinvent, "-l", str(log_path), str(resolved_config_path)],
            cwd=str(run_dir),
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return [], {
            "status": "error",
            "error": str(exc),
            "seed_file": str(seed_file),
            "config_path": str(resolved_config_path),
        }

    generated_path_candidates = list(run_dir.glob("*.smi")) + list(run_dir.glob("*.csv"))
    candidates: List[Dict[str, Any]] = []
    for path in generated_path_candidates:
        if path.name == seed_file.name:
            continue
        try:
            if path.suffix.lower() == ".csv":
                rows = _read_csv_rows(path, limit=target_count)
                for row in rows:
                    smiles_col = _find_column(row, ["smiles", "SMILES"])
                    if smiles_col and row.get(smiles_col):
                        candidates.append(
                            {
                                "candidate_id": f"RINV-{len(candidates) + 1:04d}",
                                "name": row.get("name") or row.get("Name") or f"reinvent_{len(candidates) + 1}",
                                "smiles": row[smiles_col],
                                "generator_engine": "reinvent4",
                                "generation_provenance": "reinvent4_output",
                            }
                        )
            else:
                for line in path.read_text(encoding="utf-8").splitlines():
                    parts = line.split()
                    if parts:
                        candidates.append(
                            {
                                "candidate_id": f"RINV-{len(candidates) + 1:04d}",
                                "name": parts[1] if len(parts) > 1 else f"reinvent_{len(candidates) + 1}",
                                "smiles": parts[0],
                                "generator_engine": "reinvent4",
                                "generation_provenance": "reinvent4_output",
                            }
                        )
                    if len(candidates) >= target_count:
                        break
        except Exception:
            continue
        if len(candidates) >= target_count:
            break

    for candidate in candidates:
        enrich_modern_discovery_fields(candidate)
        candidate["reinvent_config_path"] = str(resolved_config_path)
        candidate["reinvent_log_path"] = str(log_path)

    status = "completed" if completed.returncode == 0 and candidates else "error"
    if completed.returncode == 0 and not candidates:
        status = "no_candidates"

    return candidates[:target_count], {
        "status": status,
        "return_code": completed.returncode,
        "config_path": str(resolved_config_path),
        "log_path": str(log_path),
        "stdout": completed.stdout[-2000:],
        "stderr": completed.stderr[-2000:],
        "candidates": len(candidates),
    }


def _string_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    set_a = {a[i : i + 3] for i in range(max(1, len(a) - 2))}
    set_b = {b[i : i + 3] for i in range(max(1, len(b) - 2))}
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _train_baseline_predictors(activity_rows: List[Dict[str, Any]], toxicity_rows: List[Dict[str, Any]]) -> MorganBaseline:
    # Toxicity rows are retained for quality gates; activity/reference rows drive the default Morgan baseline.
    return build_morgan_baseline(activity_rows)


def _estimate_scores(candidate: Dict[str, Any], seeds: List[Dict[str, Any]], baseline: Optional[MorganBaseline]) -> Dict[str, Any]:
    smiles = _sanitize_text(candidate.get("smiles"))
    enrich_modern_discovery_fields(candidate)
    modern_score = float(candidate.get("modern_disinfectant_score") or 0)
    chain_lengths = candidate.get("chain_lengths") or []
    if not isinstance(chain_lengths, list):
        chain_lengths = []
    max_chain = max([_safe_float(value) or 0 for value in chain_lengths] or [0])
    charge_centers = float(candidate.get("stable_cationic_center_count") or 0)
    seed_similarity = max((_string_similarity(smiles, seed.get("smiles", "")) for seed in seeds), default=0)
    novelty_score = round((1 - seed_similarity) * 100, 2)

    activity_prior = modern_score
    if 8 <= max_chain <= 14:
        activity_prior += 12
    if charge_centers >= 2:
        activity_prior += 8
    activity_prior = min(100, activity_prior)

    toxicity_risk = 25
    if max_chain >= 16:
        toxicity_risk += 20
    if charge_centers >= 2:
        toxicity_risk += 8
    if len(smiles) > 90:
        toxicity_risk += 10
    toxicity_risk = min(100, toxicity_risk)
    selectivity_prior = max(0, 100 - toxicity_risk)

    morgan_result = score_candidate_against_baseline(smiles, baseline)
    morgan_score = morgan_result.get("morgan_baseline_score")
    activity_neighbors = int(morgan_result.get("morgan_neighbor_count") or 0)

    score_sources_available = ["heuristic_discovery_profile"]
    score_sources_used = ["heuristic_discovery_profile"]
    score_sources_failed = ["chemprop_v2_scaffold_not_active", "external_imported_model_not_configured"]
    score_provenance = "heuristic_prior_no_reference_neighbors_available"
    if morgan_score is not None:
        activity_prior = round(0.55 * activity_prior + 0.45 * float(morgan_score), 2)
        score_sources_available.append("rdkit_morgan_baseline")
        score_sources_used.append("rdkit_morgan_baseline")
        score_provenance = "rdkit_morgan_fingerprint_baseline_plus_discovery_profile"

    uncertainty = 0.72
    if activity_neighbors:
        uncertainty = 0.6
    if candidate.get("generator_engine") == "reinvent4":
        uncertainty = 0.55
    if candidate.get("generation_provenance") == "external_model_prediction":
        uncertainty = 0.45

    rank_score = (
        0.42 * activity_prior
        + 0.25 * selectivity_prior
        + 0.2 * modern_score
        + 0.08 * min(novelty_score, 65)
        - 0.05 * toxicity_risk
    )

    status, notes = _infer_uma_readiness(candidate)
    return {
        "modern_disinfectant_score": round(modern_score, 2),
        "predicted_activity_score": round(activity_prior, 2),
        "predicted_selectivity_score": round(selectivity_prior, 2),
        "predicted_toxicity_risk": round(toxicity_risk, 2),
        "novelty_score": novelty_score,
        "uncertainty": uncertainty,
        "rank_score": round(max(0, min(100, rank_score)), 2),
        "uma_readiness_status": status,
        "uma_readiness_notes": notes,
        "activity_baseline_neighbors": activity_neighbors,
        "toxicity_baseline_neighbors": 0,
        **morgan_result,
        "score_sources_used": score_sources_used,
        "score_sources_available": score_sources_available,
        "score_sources_failed": score_sources_failed,
        "score_provenance": score_provenance,
        "score_limitations": TRIAGE_SCORE_LIMITATION,
    }


def _score_and_rank(candidates: List[Dict[str, Any]], seeds: List[Dict[str, Any]], baseline: Optional[MorganBaseline]) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    seen = set()
    for candidate in candidates:
        smiles = _sanitize_text(candidate.get("smiles"))
        if not smiles or smiles in seen:
            continue
        seen.add(smiles)
        candidate.update(_estimate_scores(candidate, seeds, baseline))
        if candidate.get("candidate_tier") == "legacy_or_low_priority":
            candidate["rank_score"] = max(0, candidate["rank_score"] - 25)
        ranked.append(candidate)

    ranked.sort(key=lambda row: row.get("rank_score", 0), reverse=True)
    for idx, row in enumerate(ranked, start=1):
        row["rank"] = idx
    return ranked


def _write_review_workbook(
    path: Path,
    ranked_rows: List[Dict[str, Any]],
    manifests: List[Dict[str, Any]],
    summary: Dict[str, Any],
    quality_report: Optional[Dict[str, Any]] = None,
) -> None:
    if Workbook is None:
        fallback = path.with_suffix(".csv")
        headers = [
            "rank", "candidate_id", "name", "smiles", "rank_score",
            "predicted_activity_score", "predicted_selectivity_score",
            "predicted_toxicity_risk", "uncertainty", "candidate_tier",
            "generation_recommendation", "uma_readiness_status",
            "generator_engine", "generation_provenance", "score_provenance",
            "score_sources_used", "score_sources_available", "score_sources_failed",
            "score_limitations", "chemist_review_status", "chemist_review_notes",
            "reject_reason", "follow_up_literature_needed", "synthesis_feasibility_review_needed",
            "toxicity_review_needed", "regulatory_review_needed", "lab_testing_priority",
        ]
        _write_csv(fallback, ranked_rows, headers)
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "READ ME FIRST"
    ws.append(["CleanMol Discovery Packet"])
    ws.append(["Disclaimer", PUBLIC_RELEASE_DISCLAIMER.strip()])
    ws.append(["Score Interpretation", TRIAGE_SCORE_LIMITATION])
    ws.append(["Quality Status", summary.get("dataset_quality_label", "")])
    ws.append(["Dataset Status", summary.get("dataset_quality_status", "")])
    ws.append(["Integrations Used", json.dumps(summary.get("integrations_used", []))])
    ws.append(["Integrations Unavailable", json.dumps(summary.get("integrations_unavailable", []))])
    ws.append(["Top Limitations", "Generated hypotheses require qualified expert review and independent laboratory validation."])
    ws.append(["Recommended Review Workflow", "Review disclaimer, source manifest, dataset quality, nearest references, toxicity flags, UMA readiness, then decide whether expert follow-up is justified."])
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 120
    for cell in ws["A"]:
        cell.font = Font(bold=True)

    ws = wb.create_sheet("Ranked Candidates")
    headers = [
        "rank", "candidate_id", "name", "smiles", "rank_score",
        "predicted_activity_score", "predicted_selectivity_score", "predicted_toxicity_risk",
        "uncertainty", "candidate_tier", "generation_recommendation",
        "modern_scaffold_tags", "legacy_flags", "uma_readiness_status",
        "nearest_reference_name", "nearest_reference_smiles", "nearest_reference_similarity",
        "nearest_reference_source", "nearest_reference_activity_label", "nearest_reference_endpoint",
        "nearest_reference_value", "nearest_reference_units", "morgan_baseline_score",
        "morgan_neighbor_count", "morgan_score_provenance",
        "generator_engine", "generation_provenance", "source_seed_id",
        "reinvent_config_path", "reinvent_log_path", "reinvent_status", "score_provenance",
        "score_sources_used", "score_sources_available", "score_sources_failed", "score_limitations",
        "chemist_review_status", "chemist_review_notes", "reject_reason", "follow_up_literature_needed",
        "synthesis_feasibility_review_needed", "toxicity_review_needed", "regulatory_review_needed",
        "lab_testing_priority",
    ]
    ws.append(headers)
    for row in ranked_rows:
        ws.append([
            row.get("rank", ""),
            row.get("candidate_id", ""),
            row.get("name", ""),
            row.get("smiles", ""),
            row.get("rank_score", ""),
            row.get("predicted_activity_score", ""),
            row.get("predicted_selectivity_score", ""),
            row.get("predicted_toxicity_risk", ""),
            row.get("uncertainty", ""),
            row.get("candidate_tier", ""),
            row.get("generation_recommendation", ""),
            json.dumps(row.get("modern_scaffold_tags") or []),
            json.dumps(row.get("legacy_flags") or []),
            row.get("uma_readiness_status", ""),
            row.get("nearest_reference_name", ""),
            row.get("nearest_reference_smiles", ""),
            row.get("nearest_reference_similarity", ""),
            row.get("nearest_reference_source", ""),
            row.get("nearest_reference_activity_label", ""),
            row.get("nearest_reference_endpoint", ""),
            row.get("nearest_reference_value", ""),
            row.get("nearest_reference_units", ""),
            row.get("morgan_baseline_score", ""),
            row.get("morgan_neighbor_count", ""),
            row.get("morgan_score_provenance", ""),
            row.get("generator_engine", ""),
            row.get("generation_provenance", ""),
            row.get("source_seed_id", ""),
            row.get("reinvent_config_path", ""),
            row.get("reinvent_log_path", ""),
            row.get("reinvent_status", ""),
            row.get("score_provenance", ""),
            json.dumps(row.get("score_sources_used") or []),
            json.dumps(row.get("score_sources_available") or []),
            json.dumps(row.get("score_sources_failed") or []),
            row.get("score_limitations", TRIAGE_SCORE_LIMITATION),
            "pending",
            "",
            "",
            "yes",
            "yes",
            "yes",
            "yes",
            "",
        ])

    header_fill = PatternFill(start_color="1F6FEB", end_color="1F6FEB", fill_type="solid")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
    ws.freeze_panes = "A2"

    summary_ws = wb.create_sheet("Run Summary")
    summary_ws.append(["Field", "Value"])
    for key, value in summary.items():
        summary_ws.append([key, json.dumps(value) if isinstance(value, (dict, list)) else value])

    source_ws = wb.create_sheet("Sources")
    source_ws.append(["source", "status", "role", "rows", "reason", "error"])
    for item in manifests:
        source_ws.append([
            item.get("dataset") or item.get("source") or item.get("path") or "",
            item.get("status", ""),
            item.get("role", ""),
            item.get("rows", ""),
            item.get("reason", ""),
            item.get("error", ""),
        ])

    if quality_report:
        quality_ws = wb.create_sheet("Quality Gates")
        quality_ws.append(["Status", quality_report.get("status_label", "")])
        quality_ws.append(["Quality Score", quality_report.get("quality_score", "")])
        quality_ws.append(["Gates Passed", f"{quality_report.get('gates_passed', 0)}/{quality_report.get('gates_total', 0)}"])
        quality_ws.append([])
        quality_ws.append(["Gate", "Passed", "Score", "Value", "Target", "Recommendation"])
        for gate in quality_report.get("gates", []):
            quality_ws.append([
                gate.get("name", ""),
                gate.get("passed", ""),
                gate.get("score", ""),
                json.dumps(gate.get("value")) if isinstance(gate.get("value"), (dict, list)) else gate.get("value", ""),
                gate.get("target", ""),
                gate.get("recommendation", ""),
            ])

    wb.save(path)


def _dependency_versions() -> Dict[str, str]:
    packages = ["fastapi", "uvicorn", "pydantic", "PyMuPDF", "requests", "openpyxl", "rdkit", "anthropic", "openai", "google-generativeai"]
    versions: Dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not_installed"
    return versions


def _write_disclaimer(path: Path) -> None:
    path.write_text(
        PUBLIC_RELEASE_DISCLAIMER
        + "\nThis CleanMol Discovery packet contains heuristic research triage outputs.\n\n"
        + "The ranked candidates are not validated antimicrobial agents.\n"
        + "The scores are not probabilities.\n"
        + "The outputs do not establish safety, efficacy, synthesizability, environmental acceptability, regulatory compliance, or commercial suitability.\n\n"
        + "Use only for qualified expert review and hypothesis generation.\n",
        encoding="utf-8",
    )


def _write_run_environment(
    path: Path,
    *,
    models: Dict[str, Any],
    options: Dict[str, Any],
    integrations: Dict[str, Any],
    input_files: List[str],
    output_files: List[str],
) -> Dict[str, Any]:
    payload = {
        "cleanmol_version": "0.1.0-public-preview",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "dependency_versions": _dependency_versions(),
        "models_requested": models,
        "models_resolved": models,
        "options": options,
        "integrations": integrations,
        "input_files": input_files,
        "output_files": output_files,
        "score_warning": TRIAGE_SCORE_LIMITATION,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def run_discovery_automation(
    output_dir: str,
    uploaded_dataset_path: Optional[str] = None,
    keys: Optional[Dict[str, str]] = None,
    options: Optional[Dict[str, Any]] = None,
    progress_callback: ProgressCallback = None,
) -> Dict[str, Any]:
    """Run the automated CleanMol discovery workflow."""
    start = time.time()
    options = options or {}
    keys = keys or {}
    output_path = Path(output_dir)
    discovery_dir = output_path / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)

    target_count = int(options.get("target_candidate_count") or 50)
    max_upload_rows = int(options.get("max_upload_rows") or 20000)

    manifests: List[Dict[str, Any]] = []

    _emit(progress_callback, "DATASET", "start", message="Building training tables")
    activity_rows, toxicity_rows = _load_existing_cleanmol_rows(output_path)
    manifests.append({"source": "cleanmol_analysis_ready", "status": "loaded", "activity_rows": len(activity_rows), "toxicity_rows": len(toxicity_rows)})

    upload_path = Path(uploaded_dataset_path) if uploaded_dataset_path else None
    upload_activity, upload_toxicity, upload_manifest = _load_uploaded_rows(upload_path, max_rows=max_upload_rows)
    manifests.append(upload_manifest)
    activity_rows.extend(upload_activity)
    toxicity_rows.extend(upload_toxicity)

    public_activity, public_toxicity, public_manifests = _load_public_source_rows(options, keys)
    manifests.extend(public_manifests)
    activity_rows.extend(public_activity)
    toxicity_rows.extend(public_toxicity)

    activity_path = discovery_dir / "training_activity_table.csv"
    toxicity_path = discovery_dir / "training_toxicity_table.csv"
    _write_csv(
        activity_path,
        activity_rows,
        ["smiles", "molecule_name", "organism", "assay_type", "endpoint", "value", "units", "activity_label", "source", "provenance"],
    )
    _write_csv(
        toxicity_path,
        toxicity_rows,
        ["smiles", "toxicity_endpoint", "toxicity_value", "toxicity_label", "source", "provenance"],
    )
    baseline = _train_baseline_predictors(activity_rows, toxicity_rows)
    _emit(
        progress_callback,
        "DATASET",
        "end",
        activity_rows=len(activity_rows),
        toxicity_rows=len(toxicity_rows),
        morgan_references=len(baseline.references),
        baseline_status=baseline.status,
    )

    _emit(progress_callback, "SEEDS", "start", message="Preparing generation seeds")
    seeds = _load_seed_molecules(output_path, activity_rows)
    seed_path = discovery_dir / "resolved_generation_seeds.smi"
    with seed_path.open("w", encoding="utf-8") as f:
        for seed in seeds:
            f.write(f"{seed['smiles']}\t{seed.get('molecule_id', 'seed')}\n")
    _emit(progress_callback, "SEEDS", "end", seeds=len(seeds))

    _emit(progress_callback, "GENERATE", "start", message="Generating candidates")
    generator_engine = options.get("generator_engine") or "auto"
    reinvent_meta: Dict[str, Any] = {"status": "skipped"}
    generated: List[Dict[str, Any]] = []
    if generator_engine in {"auto", "reinvent4"}:
        disabled_integrations = options.get("disabled_integrations") or []
        if isinstance(disabled_integrations, str):
            disabled_integrations = [item.strip() for item in disabled_integrations.split(",")]
        generated, reinvent_meta = _run_reinvent_if_available(
            discovery_dir,
            seeds,
            target_count=target_count,
            timeout_seconds=int(options.get("reinvent_timeout_seconds") or 1800),
            config_path=options.get("reinvent_config_path") or "",
            enabled="reinvent4" not in set(disabled_integrations),
        )
        for candidate in generated:
            if candidate.get("generator_engine") == "reinvent4":
                candidate["reinvent_status"] = reinvent_meta.get("status", "")
    if len(generated) < target_count and options.get("allow_builtin_generator", True):
        fallback_candidates = _builtin_generate_candidates(seeds, target_count=target_count - len(generated))
        for candidate in fallback_candidates:
            candidate["reinvent_status"] = "not_available_or_disabled"
            candidate["reinvent_config_path"] = reinvent_meta.get("config_path", "")
            candidate["reinvent_log_path"] = reinvent_meta.get("log_path", "")
        generated.extend(fallback_candidates)
    manifests.append({"source": "reinvent4", **reinvent_meta})
    if reinvent_meta.get("status") != "completed" and len(generated) > 0:
        manifests.append({
            "source": "advanced_generation_fallback",
            "status": "fallback_used",
            "warning": "REINVENT 4 was unavailable, disabled, or errored. CleanMol used the built-in rule-based hypothesis generator instead.",
        })
    _emit(progress_callback, "GENERATE", "end", generated=len(generated), reinvent_status=reinvent_meta.get("status"))

    _emit(progress_callback, "SCORE", "start", message="Scoring candidates")
    ranked_rows = _score_and_rank(generated, seeds, baseline)
    ranked_rows = ranked_rows[:target_count]
    ranked_path = discovery_dir / "ranked_lab_candidates.csv"
    ranked_headers = [
        "rank", "candidate_id", "name", "smiles", "rank_score",
        "predicted_activity_score", "predicted_selectivity_score", "predicted_toxicity_risk",
        "novelty_score", "uncertainty", "candidate_tier", "generation_recommendation",
        "modern_scaffold_tags", "legacy_flags", "uma_readiness_status", "uma_readiness_notes",
        "nearest_reference_name", "nearest_reference_smiles", "nearest_reference_similarity",
        "nearest_reference_source", "nearest_reference_activity_label", "nearest_reference_endpoint",
        "nearest_reference_value", "nearest_reference_units", "morgan_baseline_score",
        "morgan_neighbor_count", "morgan_score_provenance",
        "activity_baseline_neighbors", "toxicity_baseline_neighbors",
        "generator_engine", "generation_provenance", "source_seed_id", "score_sources_used",
        "reinvent_config_path", "reinvent_log_path", "reinvent_status",
        "score_sources_available", "score_sources_failed", "score_provenance", "score_limitations",
        "chemist_review_status", "chemist_review_notes", "reject_reason", "follow_up_literature_needed",
        "synthesis_feasibility_review_needed", "toxicity_review_needed", "regulatory_review_needed",
        "lab_testing_priority",
    ]
    serializable_rows = []
    for row in ranked_rows:
        item = dict(row)
        item["modern_scaffold_tags"] = json.dumps(item.get("modern_scaffold_tags") or [])
        item["legacy_flags"] = json.dumps(item.get("legacy_flags") or [])
        item["score_sources_used"] = json.dumps(item.get("score_sources_used") or [])
        item["score_sources_available"] = json.dumps(item.get("score_sources_available") or [])
        item["score_sources_failed"] = json.dumps(item.get("score_sources_failed") or [])
        item.setdefault("chemist_review_status", "pending")
        item.setdefault("chemist_review_notes", "")
        item.setdefault("reject_reason", "")
        item.setdefault("follow_up_literature_needed", "yes")
        item.setdefault("synthesis_feasibility_review_needed", "yes")
        item.setdefault("toxicity_review_needed", "yes")
        item.setdefault("regulatory_review_needed", "yes")
        item.setdefault("lab_testing_priority", "")
        serializable_rows.append(item)
    _write_csv(ranked_path, serializable_rows, ranked_headers)
    ranked_hypothesis_path = discovery_dir / "ranked_hypothesis_candidates.csv"
    _write_csv(ranked_hypothesis_path, serializable_rows, ranked_headers)
    quality_report = assess_dataset_quality(activity_rows, toxicity_rows, seeds, ranked_rows, manifests)
    _emit(
        progress_callback,
        "SCORE",
        "end",
        ranked=len(ranked_rows),
        quality_status=quality_report.get("status_label"),
        quality_score=quality_report.get("quality_score"),
    )

    _emit(progress_callback, "EXPORT", "start", message="Writing discovery packet")
    integration_status = get_integration_status(keys, options)
    integrations_used = sorted({
        source
        for row in ranked_rows
        for source in (row.get("score_sources_used") or [])
    })
    integrations_unavailable = [
        name
        for name, row in integration_status.items()
        if row.get("status") in {"not_installed", "installed_but_not_configured", "api_key_missing", "disabled", "error", "optional"}
        and not row.get("required")
    ]
    summary = {
        "status": "success",
        "elapsed_seconds": round(time.time() - start, 2),
        "activity_rows": len(activity_rows),
        "toxicity_rows": len(toxicity_rows),
        "seed_count": len(seeds),
        "generated_count": len(generated),
        "ranked_count": len(ranked_rows),
        "generator_engine": generator_engine,
        "reinvent_status": reinvent_meta.get("status"),
        "predictor_status": baseline.status,
        "morgan_reference_count": len(baseline.references),
        "dataset_quality_status": quality_report.get("status"),
        "dataset_quality_label": quality_report.get("status_label"),
        "dataset_quality_score": quality_report.get("quality_score"),
        "dataset_quality_gates": f"{quality_report.get('gates_passed')}/{quality_report.get('gates_total')}",
        "integrations_used": integrations_used,
        "integrations_unavailable": integrations_unavailable,
        "score_warning": TRIAGE_SCORE_LIMITATION,
        "safety_note": "Generated candidates are hypotheses for qualified chemist review; no synthesis instructions or efficacy claims are provided.",
    }
    disclaimer_path = discovery_dir / "DISCLAIMER.txt"
    workbook_path = discovery_dir / ("ranked_lab_candidates_review.xlsx" if Workbook is not None else "ranked_lab_candidates_review.csv")
    hypothesis_workbook_path = discovery_dir / ("ranked_hypothesis_candidates_review.xlsx" if Workbook is not None else "ranked_hypothesis_candidates_review.csv")
    _write_disclaimer(disclaimer_path)
    manifest_path = discovery_dir / "discovery_source_manifest.json"
    manifest_path.write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    quality_path = discovery_dir / "dataset_quality_report.json"
    quality_path.write_text(json.dumps(quality_report, indent=2), encoding="utf-8")
    summary_path = discovery_dir / "discovery_run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    run_environment_path = discovery_dir / "run_environment.json"
    output_files = [
        str(activity_path),
        str(toxicity_path),
        str(seed_path),
        str(ranked_path),
        str(ranked_hypothesis_path),
        str(manifest_path),
        str(quality_path),
        str(summary_path),
        str(disclaimer_path),
        str(run_environment_path),
        str(workbook_path),
        str(hypothesis_workbook_path),
    ]
    _write_run_environment(
        run_environment_path,
        models={},
        options=options,
        integrations=integration_status,
        input_files=[str(upload_path)] if upload_path else [],
        output_files=output_files,
    )
    _write_review_workbook(workbook_path, ranked_rows, manifests, summary, quality_report=quality_report)
    _write_review_workbook(hypothesis_workbook_path, ranked_rows, manifests, summary, quality_report=quality_report)
    _emit(progress_callback, "EXPORT", "end", files=10)

    return {
        "ok": True,
        "summary": summary,
        "files": {
            "training_activity_table": str(activity_path),
            "training_toxicity_table": str(toxicity_path),
            "resolved_generation_seeds": str(seed_path),
            "ranked_lab_candidates": str(ranked_path),
            "ranked_hypothesis_candidates": str(ranked_hypothesis_path),
            "review_workbook": str(workbook_path),
            "ranked_hypothesis_candidates_review": str(hypothesis_workbook_path),
            "source_manifest": str(manifest_path),
            "dataset_quality_report": str(quality_path),
            "run_summary": str(summary_path),
            "run_environment": str(run_environment_path),
            "disclaimer": str(disclaimer_path),
        },
        "dataset_quality": quality_report,
        "top_candidates": ranked_rows[:10],
    }
