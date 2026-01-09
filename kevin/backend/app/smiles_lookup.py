"""
SMILES lookup via PubChem API.
Free, no API key required, rate limit ~5 requests/second.
"""
import requests
from urllib.parse import quote
import time
import re
import sys
from typing import Optional


PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def normalize_name_for_search(name: str) -> str:
    """Clean up molecule name for PubChem search."""
    # Remove parenthetical abbreviations like "(BAC)" or "(CHX)"
    name = re.sub(r'\s*\([A-Z]{2,5}\)\s*', ' ', name)
    # Remove trailing/leading whitespace
    name = name.strip()
    return name


def lookup_smiles(name: str, timeout: float = 15.0) -> Optional[str]:
    """
    Look up SMILES for a compound name via PubChem.
    Returns canonical SMILES or None if not found.
    """
    clean_name = normalize_name_for_search(name)
    if not clean_name:
        return None

    try:
        # URL encode the name properly for the path
        encoded_name = quote(clean_name, safe='')
        url = f"{PUBCHEM_BASE}/compound/name/{encoded_name}/cids/JSON"

        # First, get CID from name
        resp = requests.get(url, timeout=timeout)

        if resp.status_code == 404:
            # Not found in PubChem
            return None

        if resp.status_code != 200:
            print(f"[SMILES] Unexpected status {resp.status_code} for '{clean_name}'", file=sys.stderr)
            return None

        data = resp.json()
        cids = data.get("IdentifierList", {}).get("CID", [])
        if not cids:
            return None

        cid = cids[0]  # Take first match

        # Now get SMILES for this CID
        smiles_url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/CanonicalSMILES/JSON"
        resp = requests.get(smiles_url, timeout=timeout)

        if resp.status_code != 200:
            print(f"[SMILES] Failed to get SMILES for CID {cid}: status {resp.status_code}", file=sys.stderr)
            return None

        data = resp.json()
        props = data.get("PropertyTable", {}).get("Properties", [])
        if props and "CanonicalSMILES" in props[0]:
            smiles = props[0]["CanonicalSMILES"]
            print(f"[SMILES] Found: {clean_name} -> {smiles[:60]}{'...' if len(smiles) > 60 else ''}")
            return smiles

        return None

    except requests.exceptions.Timeout:
        print(f"[SMILES] Timeout looking up '{clean_name}'", file=sys.stderr)
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"[SMILES] Connection error for '{clean_name}': {e}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"[SMILES] Request error for '{clean_name}': {e}", file=sys.stderr)
        return None
    except ValueError as e:
        # JSON decode error
        print(f"[SMILES] JSON parse error for '{clean_name}': {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[SMILES] Unexpected error for '{clean_name}': {type(e).__name__}: {e}", file=sys.stderr)
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
    already_had = 0
    looked_up = 0

    print(f"[SMILES] Starting enrichment for {total} molecules...")

    for i, mol in enumerate(molecules):
        # Skip if already has SMILES
        if mol.get("smiles"):
            already_had += 1
            found += 1
            continue

        # Try normalized_name first, then name_as_written
        name = mol.get("normalized_name") or mol.get("name_as_written")
        if not name:
            print(f"[SMILES] Skipping molecule {i+1}/{total}: no name available")
            continue

        looked_up += 1
        smiles = lookup_smiles(name)
        if smiles:
            mol["smiles"] = smiles
            mol["smiles_source"] = "PubChem"
            found += 1
        else:
            # Mark as not found so we don't retry
            mol["smiles_source"] = "not_found"
            print(f"[SMILES] Not found: {name}")

        # Rate limiting
        if i < total - 1:
            time.sleep(delay)

    print(f"[SMILES] Enrichment complete: {found}/{total} have SMILES ({already_had} pre-existing, {found - already_had} newly found)")

    if logger:
        logger.log_stage("SMILES Enrichment", {
            "total_molecules": total,
            "with_smiles": found,
            "pre_existing": already_had,
            "newly_found": found - already_had,
            "looked_up": looked_up
        })

    return molecules
