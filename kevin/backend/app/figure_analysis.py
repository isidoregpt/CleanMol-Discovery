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
    {"name": "compound name", "smiles": "SMILES string", "confidence": "high|medium|low", "notes": "observations"}
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


def match_figure_compounds_to_molecules(
    figure_compounds: list,
    extracted_molecules: list
) -> tuple:
    """
    Match figure-extracted SMILES to Opus-extracted molecules by name/code.

    Args:
        figure_compounds: List of compounds from figure extraction
        extracted_molecules: List of molecules from Opus extraction

    Returns:
        Tuple of (updated_molecules, match_count)
    """
    if not figure_compounds or not extracted_molecules:
        return extracted_molecules, 0

    matched = 0

    # Build lookup from figure compounds
    figure_lookup = {}
    for compound in figure_compounds:
        if compound.get("smiles") and compound.get("smiles_valid"):
            name = compound.get("name") or ""
            if name:
                name = name.strip().lower()
                if name:
                    figure_lookup[name] = compound

    # Try to match to extracted molecules
    for mol in extracted_molecules:
        # Skip if already has SMILES
        if mol.get("smiles"):
            continue

        # Try to match by various name fields (with null safety)
        names_to_try = []
        for field in ["name_as_written", "normalized_name", "molecule_id"]:
            val = mol.get(field)
            if val:
                names_to_try.append(val.strip().lower())

        for name in names_to_try:
            if name and name in figure_lookup:
                compound = figure_lookup[name]
                mol["smiles"] = compound["smiles"]
                mol["smiles_source"] = compound["source"]
                mol["smiles_confidence"] = compound.get("confidence", "medium")
                mol["smiles_valid"] = True
                matched += 1
                print(f"    Matched figure SMILES: {name} -> {mol['smiles'][:40]}...")
                break

    return extracted_molecules, matched
