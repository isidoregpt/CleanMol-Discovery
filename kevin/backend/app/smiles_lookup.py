"""SMILES lookup via PubChem, CIR, and OPSIN APIs."""
import time
from typing import Optional, Tuple
from urllib.parse import quote

import requests

# Rate limiting
RATE_LIMIT_DELAY = 0.25  # 4 requests/sec (under PubChem's 5/sec limit)


def normalize_name_for_search(name: str) -> Optional[str]:
    """Clean compound name for API lookup."""
    if not name:
        return None

    # Use normalized_name if available, otherwise name_as_written
    clean = name.strip()

    # Remove common suffixes that might interfere
    for suffix in [" (as ", " ("]:
        if suffix in clean:
            clean = clean.split(suffix)[0].strip()

    # Remove trailing parentheses content
    if clean.endswith(")"):
        paren_start = clean.rfind("(")
        if paren_start > 0:
            clean = clean[:paren_start].strip()

    return clean if clean else None


def lookup_pubchem(name: str, timeout: float = 10.0) -> Optional[str]:
    """Look up SMILES via PubChem PUG-REST API."""
    try:
        encoded = quote(name, safe='')
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/property/CanonicalSMILES/TXT"

        resp = requests.get(url, timeout=timeout)

        if resp.status_code == 404:
            return None

        resp.raise_for_status()
        smiles = resp.text.strip()
        return smiles if smiles else None

    except requests.exceptions.RequestException as e:
        print(f"    [PubChem] Request error: {e}")
        return None


def lookup_cir(name: str, timeout: float = 10.0) -> Optional[str]:
    """Look up SMILES via NCI/CADD Chemical Identifier Resolver."""
    try:
        encoded = quote(name, safe='')
        url = f"https://cactus.nci.nih.gov/chemical/structure/{encoded}/smiles"

        resp = requests.get(url, timeout=timeout)

        if resp.status_code == 404:
            return None

        resp.raise_for_status()
        smiles = resp.text.strip()
        return smiles if smiles else None

    except requests.exceptions.RequestException as e:
        print(f"    [CIR] Request error: {e}")
        return None


def lookup_opsin(name: str, timeout: float = 10.0) -> Optional[str]:
    """Look up SMILES via OPSIN (for IUPAC systematic names)."""
    try:
        encoded = quote(name, safe='')
        url = f"https://opsin.ch.cam.ac.uk/opsin/{encoded}.smi"

        resp = requests.get(url, timeout=timeout)

        if resp.status_code != 200:
            return None

        smiles = resp.text.strip()
        return smiles if smiles else None

    except requests.exceptions.RequestException as e:
        print(f"    [OPSIN] Request error: {e}")
        return None


def lookup_smiles(name: str, timeout: float = 10.0) -> Tuple[Optional[str], str]:
    """
    Look up SMILES for a compound name using multiple services.

    Returns:
        tuple of (smiles_string or None, source_string)
        source_string is one of: "PubChem", "CIR", "OPSIN", "not_found"
    """
    clean_name = normalize_name_for_search(name)
    if not clean_name:
        return None, "not_found"

    print(f"  Looking up: '{clean_name}'")

    # Try PubChem first (largest database)
    smiles = lookup_pubchem(clean_name, timeout)
    if smiles:
        return smiles, "PubChem"

    time.sleep(RATE_LIMIT_DELAY)

    # Try CIR (good for synonyms)
    smiles = lookup_cir(clean_name, timeout)
    if smiles:
        return smiles, "CIR"

    time.sleep(RATE_LIMIT_DELAY)

    # Try OPSIN (good for IUPAC names)
    smiles = lookup_opsin(clean_name, timeout)
    if smiles:
        return smiles, "OPSIN"

    return None, "not_found"


def enrich_molecules_with_smiles(molecules: list, logger=None, delay: float = 0.25) -> list:
    """
    Enrich a list of molecule dicts with SMILES strings.

    Modifies molecules in place and returns the list.
    Also prints stats for visibility.
    """
    total = len(molecules)
    pre_existing = 0
    figure_derived = 0
    newly_found = 0
    looked_up = 0

    print(f"[SMILES] Starting enrichment for {total} molecules...")

    for i, mol in enumerate(molecules):
        # Skip if already has SMILES (from figure extraction or other source)
        if mol.get("smiles"):
            source = mol.get("smiles_source", "")
            if source and source.startswith("figure"):
                figure_derived += 1
                print(f"  [{i+1}/{total}] Skipping (figure-derived): {mol.get('name_as_written', mol.get('molecule_id', 'unknown'))}")
            else:
                pre_existing += 1
            continue

        # Get name to look up
        name = mol.get("normalized_name") or mol.get("name_as_written")
        if not name:
            mol["smiles_source"] = "not_found"
            print(f"  [{i+1}/{total}] No name available, skipping")
            continue

        looked_up += 1
        print(f"  [{i+1}/{total}] {name}")

        # Look up SMILES
        smiles, source = lookup_smiles(name)

        mol["smiles"] = smiles
        mol["smiles_source"] = source

        if smiles:
            newly_found += 1
            print(f"    ✓ Found via {source}: {smiles[:50]}{'...' if len(smiles) > 50 else ''}")
        else:
            print(f"    ✗ Not found in any database")

        # Rate limit between molecules
        if i < total - 1:
            time.sleep(delay)

    with_smiles = pre_existing + figure_derived + newly_found
    print(f"[SMILES] Complete: {with_smiles}/{total} have SMILES ({figure_derived} from figures, {pre_existing} pre-existing, {newly_found} newly found)")

    if logger:
        logger.log_stage("SMILES Enrichment", {
            "total_molecules": total,
            "with_smiles": with_smiles,
            "figure_derived": figure_derived,
            "pre_existing": pre_existing,
            "newly_found": newly_found,
            "looked_up": looked_up
        })

    return molecules
