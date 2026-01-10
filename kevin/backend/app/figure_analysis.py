"""
Figure Analysis module for extracting chemical structures from PDF figures using Claude Vision.
"""
import base64
import json
import re
import time
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF


# Claude Vision prompt for structure extraction
STRUCTURE_EXTRACTION_PROMPT = """Analyze this image from a scientific paper. Look for chemical structure diagrams.

For EACH chemical structure visible in the image:

1. **Identify** the compound name, code, or label shown near the structure
2. **Interpret** the molecular structure carefully:
   - Count all atoms (C, N, O, S, P, etc.)
   - Note all bonds (single, double, triple, aromatic)
   - Identify charged atoms (N+, P+, S+, O-)
   - Note counterions (Cl-, Br-, I-)
   - Count carbon chain lengths precisely (e.g., C12H25 means 12 carbons)
3. **Generate** a valid SMILES string representing the structure
4. **Assess** your confidence: high (clearly visible, simple structure), medium (complex but clear), low (partially obscured or very complex)

**CRITICAL: Variable/Generic Structures**
If a structure shows variable components (e.g., "n = 2, 3, 4, 5, 6", "R = Me, Et, Pr", "m,n = various values"):
- Generate SEPARATE entries for EACH specific variant
- Use specific names (e.g., "P2P-10,10", "P3P-10,10" NOT "PnP series" or "Compound (n=2-6)")
- Generate complete SMILES with actual atoms for each variant (no variables like "n" in SMILES)
- Include a "variant_of" field noting the parent structure

Example: If structure shows "bis-phosphonium with n = 2, 3, 4, 5, 6, 8" for linker length:
- Create 6 separate entries: one for n=2, one for n=3, etc.
- Each with specific name like "P2P" (for n=2), "P3P" (for n=3)
- Each with complete SMILES containing the actual linker carbons

Important guidelines:
- Quaternary ammonium (N+) should be written as [N+]
- Quaternary phosphonium (P+) should be written as [P+]
- Include counterions as separate fragments: SMILES.[Cl-]
- For long alkyl chains like C12H25, write as CCCCCCCCCCCC (12 C's)
- Aromatic rings: benzene = c1ccccc1, pyridinium = [n+]1ccccc1

Return ONLY valid JSON:
{
  "figures_found": true,
  "compounds": [
    {"name": "specific compound name", "smiles": "complete SMILES string", "confidence": "high|medium|low", "notes": "observations", "variant_of": "parent structure name if applicable"}
  ]
}

If no chemical structures are visible, return:
{"figures_found": false, "compounds": []}
"""


def extract_images_from_pdf(pdf_path: str, min_width: int = 200, min_height: int = 200) -> list:
    """
    Extract embedded images from PDF using PyMuPDF (fitz).

    Args:
        pdf_path: Path to PDF file
        min_width: Minimum image width to extract
        min_height: Minimum image height to extract

    Returns:
        List of dicts with keys: page_num, image_bytes, format, width, height
    """
    images = []

    try:
        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                xref = img[0]

                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    width = base_image["width"]
                    height = base_image["height"]

                    # Filter by size
                    if width >= min_width and height >= min_height:
                        images.append({
                            "page_num": page_num + 1,  # 1-indexed
                            "image_bytes": image_bytes,
                            "format": image_ext,
                            "width": width,
                            "height": height,
                            "source": "embedded"
                        })
                        print(f"    Extracted embedded image from page {page_num + 1}: {width}x{height} ({image_ext})")
                except Exception as e:
                    print(f"    Warning: Could not extract image {img_index} from page {page_num + 1}: {e}")

        doc.close()

    except Exception as e:
        print(f"    Error opening PDF: {e}")

    return images


def extract_page_as_image(pdf_path: str, page_num: int, dpi: int = 150) -> Optional[bytes]:
    """
    Render entire PDF page as PNG image.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-indexed)
        dpi: Resolution for rendering

    Returns:
        PNG image bytes, or None on failure
    """
    try:
        doc = fitz.open(pdf_path)

        if page_num < 1 or page_num > len(doc):
            print(f"    Invalid page number: {page_num}")
            doc.close()
            return None

        page = doc[page_num - 1]  # Convert to 0-indexed

        # Render at specified DPI
        zoom = dpi / 72  # 72 is the default DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        image_bytes = pix.tobytes("png")

        doc.close()

        print(f"    Rendered page {page_num} as image: {pix.width}x{pix.height}")
        return image_bytes

    except Exception as e:
        print(f"    Error rendering page {page_num}: {e}")
        return None


def analyze_image_with_claude(
    image_bytes: bytes,
    image_format: str,
    api_key: str,
    model: str = "claude-opus-4-5-20251101"
) -> dict:
    """
    Send image to Claude Vision API with structure extraction prompt.

    Args:
        image_bytes: Image data
        image_format: Image format (png, jpeg, etc.)
        api_key: Anthropic API key
        model: Claude model to use

    Returns:
        Dict with figures_found (bool) and compounds (list)
    """
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)

        # Encode image to base64
        base64_data = base64.b64encode(image_bytes).decode("utf-8")

        # Map format to media type
        media_type_map = {
            "png": "image/png",
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp"
        }
        media_type = media_type_map.get(image_format.lower(), "image/png")

        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_data
                        }
                    },
                    {
                        "type": "text",
                        "text": STRUCTURE_EXTRACTION_PROMPT
                    }
                ]
            }]
        )

        response_text = message.content[0].text

        # Parse JSON response
        # Try to extract JSON from response (sometimes wrapped in markdown code blocks)
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            print(f"    Warning: Could not parse JSON from response")
            return {"figures_found": False, "compounds": []}

    except json.JSONDecodeError as e:
        print(f"    Warning: JSON decode error: {e}")
        return {"figures_found": False, "compounds": []}
    except Exception as e:
        print(f"    Warning: Claude Vision API error: {e}")
        return {"figures_found": False, "compounds": []}


def validate_smiles(smiles: str) -> dict:
    """
    Validate SMILES with RDKit, return canonical form and validity status.

    Args:
        smiles: SMILES string to validate

    Returns:
        Dict with keys: valid, canonical_smiles, error, validation_skipped
    """
    if not smiles or not smiles.strip():
        return {"valid": False, "canonical_smiles": None, "error": "Empty SMILES", "validation_skipped": False}

    try:
        from rdkit import Chem

        mol = Chem.MolFromSmiles(smiles)

        if mol is None:
            return {"valid": False, "canonical_smiles": None, "error": "Invalid SMILES structure", "validation_skipped": False}

        canonical = Chem.MolToSmiles(mol, canonical=True)
        return {"valid": True, "canonical_smiles": canonical, "error": None, "validation_skipped": False}

    except ImportError as e:
        # RDKit not available - skip validation but keep SMILES
        print(f"    [RDKit] Not available ({e}), skipping validation")
        return {"valid": True, "canonical_smiles": smiles, "error": None, "validation_skipped": True}
    except Exception as e:
        return {"valid": False, "canonical_smiles": None, "error": str(e), "validation_skipped": False}


def analyze_pdf_figures(
    pdf_path: str,
    api_key: str,
    figure_pages: list = None,
    model: str = "claude-opus-4-5-20251101",
    min_image_size: int = 200
) -> dict:
    """
    Main function: extract and analyze all figures, return validated compounds.

    Args:
        pdf_path: Path to PDF file
        api_key: Anthropic API key
        figure_pages: Specific pages to analyze (1-indexed), or None for auto-detect
        model: Claude model to use
        min_image_size: Minimum image dimension to analyze

    Returns:
        Dict with compounds list and stats
    """
    print(f"[FIGURE] Extracting images from PDF...")

    all_compounds = []
    stats = {
        "images_extracted": 0,
        "images_analyzed": 0,
        "structures_found": 0,
        "structures_valid": 0,
        "structures_invalid": 0
    }

    # Strategy 1: Extract embedded images
    images = extract_images_from_pdf(pdf_path, min_width=min_image_size, min_height=min_image_size)
    stats["images_extracted"] = len(images)
    print(f"[FIGURE] Found {len(images)} embedded images")

    # Strategy 2: If specific pages requested, also render those pages
    if figure_pages:
        for page_num in figure_pages:
            page_image = extract_page_as_image(pdf_path, page_num)
            if page_image:
                images.append({
                    "page_num": page_num,
                    "image_bytes": page_image,
                    "format": "png",
                    "width": 0,  # Unknown from render
                    "height": 0,
                    "source": "page_render"
                })

    if not images:
        print(f"[FIGURE] No suitable images found")
        return {"compounds": [], "stats": stats}

    # Analyze each image with Claude Vision
    for i, img in enumerate(images):
        print(f"[FIGURE] Analyzing image {i+1}/{len(images)} from page {img['page_num']}...")

        result = analyze_image_with_claude(
            image_bytes=img["image_bytes"],
            image_format=img["format"],
            api_key=api_key,
            model=model
        )

        stats["images_analyzed"] += 1

        if result.get("figures_found") and result.get("compounds"):
            for compound in result["compounds"]:
                compound["page_num"] = img["page_num"]
                compound["source"] = f"figure_extraction_page_{img['page_num']}"

                # Validate SMILES with RDKit
                if compound.get("smiles"):
                    validation = validate_smiles(compound["smiles"])
                    compound["smiles_valid"] = validation["valid"]

                    if validation["valid"]:
                        compound["smiles"] = validation["canonical_smiles"]
                        stats["structures_valid"] += 1
                        print(f"    ✓ Found: {compound.get('name', 'unknown')} -> {compound['smiles'][:50]}...")
                    else:
                        compound["smiles_error"] = validation["error"]
                        stats["structures_invalid"] += 1
                        print(f"    ✗ Invalid SMILES for {compound.get('name', 'unknown')}: {validation['error']}")

                stats["structures_found"] += 1
                all_compounds.append(compound)

        # Rate limiting between API calls
        if i < len(images) - 1:
            time.sleep(0.5)

    print(f"[FIGURE] Complete: {stats['structures_valid']} valid structures extracted from {stats['images_analyzed']} images")

    return {"compounds": all_compounds, "stats": stats}


def normalize_compound_name(name: str) -> str:
    """
    Normalize compound name for fuzzy matching.
    Removes common variations that differ between figure labels and text.
    """
    if not name:
        return ""
    # Lowercase
    name = name.lower()
    # Remove common separators and variations
    name = name.replace(",", "")      # MeP2P-12,12 → MeP2P-1212
    name = name.replace("-", "")      # MeP2P-12-12 → MeP2P1212
    name = name.replace(" ", "")
    name = name.replace("_", "")
    name = name.replace(".", "")
    # Remove parentheses but keep content: 12(2)12 → 12212
    name = name.replace("(", "").replace(")", "")
    # Remove quotes
    name = name.replace("'", "").replace('"', "")
    return name


def extract_scaffold_hints(name: str) -> dict:
    """
    Extract structural hints from a compound name for scaffold-based matching.

    Returns dict with:
        - scaffold_type: e.g., "phosphonium", "ammonium", "imidazolium"
        - is_bis: bool - whether it's a bis/gemini structure
        - linker_values: list of int - detected linker lengths (n values)
        - tail_values: list of int - detected tail lengths
        - has_range: bool - whether it specifies a range (n=2-6)
    """
    if not name:
        return {}

    name_lower = name.lower()
    hints = {
        "scaffold_type": None,
        "is_bis": False,
        "linker_values": [],
        "tail_values": [],
        "has_range": False,
        "raw_name": name
    }

    # Detect scaffold type
    if "phosphonium" in name_lower or name_lower.startswith("p") and "p" in name_lower[1:]:
        hints["scaffold_type"] = "phosphonium"
    elif "ammonium" in name_lower or "quat" in name_lower:
        hints["scaffold_type"] = "ammonium"
    elif "imidazolium" in name_lower:
        hints["scaffold_type"] = "imidazolium"
    elif "pyridinium" in name_lower:
        hints["scaffold_type"] = "pyridinium"

    # Detect bis/gemini structure
    if "bis" in name_lower or "gemini" in name_lower or "twin" in name_lower:
        hints["is_bis"] = True
    # P2P, P3P patterns suggest bis-phosphonium
    if re.search(r'p\d+p', name_lower):
        hints["is_bis"] = True
        hints["scaffold_type"] = "phosphonium"

    # Extract linker values (n=X patterns)
    # Match "n = 2, 3, 4, 5, 6, 8" or "n=2-6" or "n = 2 to 6"
    range_match = re.search(r'n\s*=\s*(\d+)\s*(?:to|-)\s*(\d+)', name_lower)
    if range_match:
        start, end = int(range_match.group(1)), int(range_match.group(2))
        hints["linker_values"] = list(range(start, end + 1))
        hints["has_range"] = True

    # Match "n = 2, 3, 4, 5, 6, 8" pattern
    list_match = re.search(r'n\s*=\s*([\d,\s]+)', name_lower)
    if list_match and not hints["linker_values"]:
        values_str = list_match.group(1)
        hints["linker_values"] = [int(v.strip()) for v in re.findall(r'\d+', values_str)]
        if len(hints["linker_values"]) > 1:
            hints["has_range"] = True

    # Extract specific linker from name like "P2P" -> linker=2, "P3P" -> linker=3
    pnp_match = re.search(r'p(\d+)p', name_lower)
    if pnp_match:
        hints["linker_values"] = [int(pnp_match.group(1))]

    # Extract tail lengths from patterns like "10,10" or "-10-10" or "C10"
    tail_match = re.findall(r'[\-,](\d{1,2})(?:[\-,](\d{1,2}))?', name_lower)
    for match in tail_match:
        for v in match:
            if v and int(v) >= 6:  # Tail lengths are typically 6+
                hints["tail_values"].append(int(v))

    return hints


def scaffold_match_score(figure_hints: dict, mol_hints: dict) -> tuple:
    """
    Calculate a match score between figure compound and molecule based on scaffold hints.

    Returns (score, reason) where:
        - score: 0 (no match), 1 (weak), 2 (medium), 3 (strong)
        - reason: explanation string
    """
    if not figure_hints or not mol_hints:
        return 0, "missing hints"

    score = 0
    reasons = []

    # Check scaffold type match
    if figure_hints.get("scaffold_type") and mol_hints.get("scaffold_type"):
        if figure_hints["scaffold_type"] == mol_hints["scaffold_type"]:
            score += 1
            reasons.append(f"same scaffold ({figure_hints['scaffold_type']})")
        else:
            return 0, "scaffold mismatch"

    # Check bis/gemini match
    if figure_hints.get("is_bis") == mol_hints.get("is_bis"):
        if figure_hints.get("is_bis"):
            score += 1
            reasons.append("both bis-structure")

    # Check if molecule's linker is within figure's range
    fig_linkers = figure_hints.get("linker_values", [])
    mol_linkers = mol_hints.get("linker_values", [])

    if fig_linkers and mol_linkers:
        mol_linker = mol_linkers[0] if mol_linkers else None
        if mol_linker and mol_linker in fig_linkers:
            score += 1
            reasons.append(f"linker {mol_linker} in range {fig_linkers}")

    # Check tail length compatibility
    fig_tails = set(figure_hints.get("tail_values", []))
    mol_tails = set(mol_hints.get("tail_values", []))
    if fig_tails and mol_tails and fig_tails & mol_tails:
        score += 1
        reasons.append(f"matching tails {fig_tails & mol_tails}")

    return score, "; ".join(reasons) if reasons else "no match criteria met"


def _save_debug_log(bundle_dir, debug_lines: list):
    """Save debug log to bundle directory."""
    if bundle_dir:
        try:
            debug_path = Path(bundle_dir) / "figure_matching_debug.txt"
            debug_path.write_text("\n".join(debug_lines), encoding="utf-8")
            print(f"    [DEBUG] Saved matching debug log to {debug_path}")
        except Exception as e:
            print(f"    [DEBUG] Failed to save debug log: {e}")


def match_figure_compounds_to_molecules(
    figure_compounds: list,
    extracted_molecules: list,
    bundle_dir=None
) -> tuple:
    """
    Match figure-extracted SMILES to Opus-extracted molecules by name/code.

    Uses three matching strategies:
    1. Exact name matching (case-insensitive)
    2. Normalized name matching (removes separators, etc.)
    3. Scaffold-based fuzzy matching (for generic/variable structures)

    Args:
        figure_compounds: List of compounds from figure extraction
        extracted_molecules: List of molecules from Opus extraction
        bundle_dir: Optional path to bundle directory for debug log output

    Returns:
        Tuple of (updated_molecules, match_count, unmatched_figure_compounds)
    """
    debug_lines = []
    debug_lines.append("=" * 80)
    debug_lines.append("FIGURE-TO-MOLECULE SMILES MATCHING DEBUG LOG")
    debug_lines.append("=" * 80)
    debug_lines.append("")

    # Track which figure compounds get matched
    matched_figure_indices = set()
    unmatched_figure_compounds = []

    # Log input counts
    debug_lines.append(f"INPUT SUMMARY:")
    debug_lines.append(f"  - Figure compounds received: {len(figure_compounds) if figure_compounds else 0}")
    debug_lines.append(f"  - Extracted molecules received: {len(extracted_molecules) if extracted_molecules else 0}")
    debug_lines.append("")

    if not figure_compounds or not extracted_molecules:
        debug_lines.append("EARLY EXIT: Empty input")
        debug_lines.append(f"  - figure_compounds is {'empty/None' if not figure_compounds else 'valid'}")
        debug_lines.append(f"  - extracted_molecules is {'empty/None' if not extracted_molecules else 'valid'}")
        _save_debug_log(bundle_dir, debug_lines)
        # Return all figure compounds as unmatched if we have them but no molecules
        if figure_compounds:
            for compound in figure_compounds:
                if compound.get("smiles"):
                    compound["matched"] = False
                    unmatched_figure_compounds.append(compound)
        return extracted_molecules, 0, unmatched_figure_compounds

    matched = 0

    # Log all figure compounds
    debug_lines.append("FIGURE COMPOUNDS (from Claude Vision):")
    debug_lines.append("-" * 40)
    for i, compound in enumerate(figure_compounds):
        name = compound.get("name", "<NO NAME>")
        smiles = compound.get("smiles", "<NO SMILES>")
        confidence = compound.get("confidence", "unknown")
        valid = compound.get("smiles_valid", "not checked")
        debug_lines.append(f"  [{i+1}] Name: '{name}'")
        debug_lines.append(f"       SMILES: {smiles[:80]}{'...' if len(str(smiles)) > 80 else ''}")
        debug_lines.append(f"       Confidence: {confidence}, Valid: {valid}")
    debug_lines.append("")

    # Build lookup from figure compounds - index by both exact and normalized names
    figure_lookup_exact = {}
    figure_lookup_normalized = {}
    figure_with_smiles = []  # Track compounds with SMILES for scaffold matching

    debug_lines.append("BUILDING LOOKUP TABLES:")
    debug_lines.append("-" * 40)

    for idx, compound in enumerate(figure_compounds):
        # Only require SMILES, not validation (validation may have been skipped)
        if not compound.get("smiles"):
            debug_lines.append(f"  SKIP (no SMILES): {compound.get('name', '<no name>')}")
            continue

        compound["_idx"] = idx  # Track original index
        figure_with_smiles.append(compound)

        name = compound.get("name") or ""
        if name:
            # Exact lowercase match
            exact_key = name.strip().lower()
            if exact_key:
                figure_lookup_exact[exact_key] = compound
                debug_lines.append(f"  EXACT KEY: '{exact_key}'")

            # Normalized match
            normalized_key = normalize_compound_name(name)
            if normalized_key:
                figure_lookup_normalized[normalized_key] = compound
                debug_lines.append(f"  NORMALIZED KEY: '{normalized_key}' (from '{name}')")
        else:
            debug_lines.append(f"  SKIP (no name): SMILES={compound.get('smiles', '')[:40]}...")

    debug_lines.append("")
    debug_lines.append(f"LOOKUP TABLE SUMMARY:")
    debug_lines.append(f"  - Exact keys: {len(figure_lookup_exact)}")
    debug_lines.append(f"  - Normalized keys: {len(figure_lookup_normalized)}")
    debug_lines.append(f"  - Exact keys list: {list(figure_lookup_exact.keys())}")
    debug_lines.append(f"  - Normalized keys list: {list(figure_lookup_normalized.keys())}")
    debug_lines.append("")

    print(f"    Figure lookup: {len(figure_lookup_exact)} exact keys, {len(figure_lookup_normalized)} normalized keys")

    # Pre-compute scaffold hints for all figure compounds (for fallback matching)
    figure_hints_list = []
    for compound in figure_with_smiles:
        hints = extract_scaffold_hints(compound.get("name", ""))
        figure_hints_list.append((compound, hints))

    # Log all extracted molecules and their matching attempts
    debug_lines.append("MOLECULE MATCHING ATTEMPTS:")
    debug_lines.append("-" * 40)

    # Try to match to extracted molecules
    for mol_idx, mol in enumerate(extracted_molecules):
        mol_id = mol.get("molecule_id", "<no id>")
        name_written = mol.get("name_as_written", "<no name>")
        norm_name = mol.get("normalized_name", "<no normalized>")
        existing_smiles = mol.get("smiles")

        debug_lines.append(f"  MOLECULE [{mol_idx+1}]:")
        debug_lines.append(f"    molecule_id: '{mol_id}'")
        debug_lines.append(f"    name_as_written: '{name_written}'")
        debug_lines.append(f"    normalized_name: '{norm_name}'")
        debug_lines.append(f"    existing_smiles: {existing_smiles[:50] if existing_smiles else 'None'}{'...' if existing_smiles and len(existing_smiles) > 50 else ''}")

        # Skip if already has SMILES
        if mol.get("smiles"):
            debug_lines.append(f"    RESULT: SKIPPED (already has SMILES)")
            continue

        # Try molecule_id first (most specific), then other fields
        fields_to_try = ["molecule_id", "name_as_written", "normalized_name"]
        found = False

        for field in fields_to_try:
            if found:
                break

            val = mol.get(field)
            if not val:
                debug_lines.append(f"    TRY {field}: <empty>")
                continue

            # Try exact match first
            exact_key = val.strip().lower()
            debug_lines.append(f"    TRY {field}: '{val}'")
            debug_lines.append(f"      exact_key: '{exact_key}' -> {'FOUND' if exact_key in figure_lookup_exact else 'NOT FOUND'}")

            if exact_key in figure_lookup_exact:
                compound = figure_lookup_exact[exact_key]
                mol["smiles"] = compound["smiles"]
                mol["smiles_source"] = compound.get("source", "figure_extraction")
                mol["smiles_confidence"] = compound.get("confidence", "medium")
                mol["smiles_valid"] = compound.get("smiles_valid", True)
                matched += 1
                matched_figure_indices.add(compound.get("_idx"))
                debug_lines.append(f"    RESULT: ✓ MATCHED (exact) -> {mol['smiles'][:50]}...")
                print(f"    ✓ Matched (exact): {val} -> {mol['smiles'][:50]}...")
                found = True
                break

            # Try normalized match
            normalized_key = normalize_compound_name(val)
            debug_lines.append(f"      normalized_key: '{normalized_key}' -> {'FOUND' if normalized_key in figure_lookup_normalized else 'NOT FOUND'}")

            if normalized_key in figure_lookup_normalized:
                compound = figure_lookup_normalized[normalized_key]
                mol["smiles"] = compound["smiles"]
                mol["smiles_source"] = compound.get("source", "figure_extraction")
                mol["smiles_confidence"] = compound.get("confidence", "medium")
                mol["smiles_valid"] = compound.get("smiles_valid", True)
                matched += 1
                matched_figure_indices.add(compound.get("_idx"))
                debug_lines.append(f"    RESULT: ✓ MATCHED (normalized) -> {mol['smiles'][:50]}...")
                print(f"    ✓ Matched (normalized): {val} -> {mol['smiles'][:50]}...")
                found = True
                break

        # FALLBACK: Try scaffold-based fuzzy matching
        if not found:
            mol_hints = extract_scaffold_hints(mol_id)
            # Also try name_as_written for hints
            if not mol_hints.get("scaffold_type"):
                mol_hints = extract_scaffold_hints(name_written)

            best_score = 0
            best_compound = None
            best_reason = ""

            for compound, fig_hints in figure_hints_list:
                # Only consider compounds with range/variable structures for fuzzy matching
                if not fig_hints.get("has_range"):
                    continue

                score, reason = scaffold_match_score(fig_hints, mol_hints)
                if score >= 2 and score > best_score:  # Require at least score 2
                    best_score = score
                    best_compound = compound
                    best_reason = reason

            if best_compound:
                mol["smiles"] = best_compound["smiles"]
                mol["smiles_source"] = best_compound.get("source", "figure_extraction") + "_inferred"
                mol["smiles_confidence"] = "inferred"
                mol["smiles_valid"] = best_compound.get("smiles_valid", True)
                mol["smiles_match_reason"] = best_reason
                matched += 1
                matched_figure_indices.add(best_compound.get("_idx"))
                debug_lines.append(f"    RESULT: ✓ MATCHED (scaffold, score={best_score}) -> {mol['smiles'][:50]}...")
                debug_lines.append(f"             Reason: {best_reason}")
                print(f"    ✓ Matched (scaffold): {mol_id} -> {mol['smiles'][:50]}... ({best_reason})")
                found = True

        if not found:
            debug_lines.append(f"    RESULT: ✗ NO MATCH")

    # Collect unmatched figure compounds
    debug_lines.append("")
    debug_lines.append("UNMATCHED FIGURE COMPOUNDS:")
    debug_lines.append("-" * 40)

    for idx, compound in enumerate(figure_compounds):
        if compound.get("smiles") and idx not in matched_figure_indices:
            compound_copy = dict(compound)
            compound_copy["matched"] = False
            if "_idx" in compound_copy:
                del compound_copy["_idx"]
            unmatched_figure_compounds.append(compound_copy)
            debug_lines.append(f"  [{idx+1}] {compound.get('name', '<no name>')} - SMILES available but no molecule match")

    if not unmatched_figure_compounds:
        debug_lines.append("  (none - all figure compounds matched)")

    debug_lines.append("")
    debug_lines.append("=" * 80)
    debug_lines.append(f"FINAL RESULT:")
    debug_lines.append(f"  - Molecules matched with figure-derived SMILES: {matched}")
    debug_lines.append(f"  - Unmatched figure compounds (with SMILES): {len(unmatched_figure_compounds)}")
    debug_lines.append("=" * 80)

    print(f"    Total matched: {matched} molecules with figure-derived SMILES")
    if unmatched_figure_compounds:
        print(f"    Unmatched figure compounds: {len(unmatched_figure_compounds)}")

    # Save debug log
    _save_debug_log(bundle_dir, debug_lines)

    # Clean up _idx from compounds
    for compound in figure_compounds:
        if "_idx" in compound:
            del compound["_idx"]

    return extracted_molecules, matched, unmatched_figure_compounds
