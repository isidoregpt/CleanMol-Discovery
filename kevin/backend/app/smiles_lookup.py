"""
SMILES lookup via PubChem API.
Free, no API key required, rate limit ~5 requests/second.
"""
import requests
import time
import re
from typing import Optional


PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def normalize_name_for_search(name: str) -> str:
    """Clean up molecule name for PubChem search."""
    # Remove parenthetical abbreviations like "(BAC)" or "(CHX)"
    name = re.sub(r'\s*\([A-Z]{2,5}\)\s*', ' ', name)
    # Remove trailing/leading whitespace
    name = name.strip()
    return name


def lookup_smiles(name: str, timeout: float = 10.0) -> Optional[str]:
    """
    Look up SMILES for a compound name via PubChem.
    Returns canonical SMILES or None if not found.
    """
    clean_name = normalize_name_for_search(name)
    if not clean_name:
        return None

    try:
        # First, get CID from name
        url = f"{PUBCHEM_BASE}/compound/name/{requests.utils.quote(clean_name)}/cids/JSON"
        resp = requests.get(url, timeout=timeout)

        if resp.status_code == 404:
            return None
        resp.raise_for_status()

        data = resp.json()
        cids = data.get("IdentifierList", {}).get("CID", [])
        if not cids:
            return None

        cid = cids[0]  # Take first match

        # Now get SMILES for this CID
        url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/CanonicalSMILES/JSON"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()

        data = resp.json()
        props = data.get("PropertyTable", {}).get("Properties", [])
        if props and "CanonicalSMILES" in props[0]:
            return props[0]["CanonicalSMILES"]

        return None

    except Exception:
        return None


def enrich_molecules_with_smiles(molecules: list, logger=None, delay: float = 0.2) -> list:
    """
    Enrich a list of molecule dicts with SMILES from PubChem.
    Modifies molecules in place and returns the list.

    Args:
        molecules: List of molecule dicts with 'name_as_written' or 'normalized_name'
        logger: Optional PipelineLogger for progress
        delay: Delay between API calls to respect rate limits
    """
    total = len(molecules)
    found = 0

    for i, mol in enumerate(molecules):
        # Skip if already has SMILES
        if mol.get("smiles"):
            found += 1
            continue

        # Try normalized_name first, then name_as_written
        name = mol.get("normalized_name") or mol.get("name_as_written")
        if not name:
            continue

        smiles = lookup_smiles(name)
        if smiles:
            mol["smiles"] = smiles
            mol["smiles_source"] = "PubChem"
            found += 1
        else:
            # Mark as not found so we don't retry
            mol["smiles_source"] = "not_found"

        # Rate limiting
        if i < total - 1:
            time.sleep(delay)

    return molecules
