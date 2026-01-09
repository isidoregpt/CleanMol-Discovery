"""
SMILES validation and property enrichment using RDKit.
"""
from typing import Optional


def validate_and_enrich_smiles(molecules: list, compute_properties: bool = True) -> dict:
    """
    Final validation pass using RDKit.

    - Validates all SMILES
    - Canonicalizes valid SMILES
    - Computes properties: molecular_weight, molecular_formula, logp, tpsa, num_heavy_atoms
    - Flags invalid SMILES with error messages

    Args:
        molecules: List of molecule dicts with 'smiles' field
        compute_properties: Whether to compute molecular properties

    Returns:
        Stats dict with validation counts
    """
    stats = {
        "total": len(molecules),
        "with_smiles": 0,
        "valid_smiles": 0,
        "invalid_smiles": 0,
        "properties_computed": 0,
        "already_validated": 0
    }

    print(f"[VALIDATE] Validating SMILES for {len(molecules)} molecules...")

    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
    except ImportError:
        print("[VALIDATE] Warning: RDKit not installed, skipping validation")
        return stats

    for mol in molecules:
        smiles = mol.get("smiles")

        if not smiles:
            continue

        stats["with_smiles"] += 1

        # Skip if already validated
        if mol.get("smiles_valid") is not None:
            stats["already_validated"] += 1
            if mol.get("smiles_valid"):
                stats["valid_smiles"] += 1
            else:
                stats["invalid_smiles"] += 1
            continue

        # Validate with RDKit
        try:
            rdkit_mol = Chem.MolFromSmiles(smiles)

            if rdkit_mol is None:
                mol["smiles_valid"] = False
                mol["smiles_error"] = "Invalid SMILES structure"
                stats["invalid_smiles"] += 1
                print(f"    ✗ Invalid: {mol.get('name_as_written', mol.get('molecule_id', 'unknown'))}")
                continue

            # Valid - canonicalize
            canonical_smiles = Chem.MolToSmiles(rdkit_mol, canonical=True)
            mol["smiles"] = canonical_smiles
            mol["smiles_valid"] = True
            stats["valid_smiles"] += 1

            # Compute properties if requested
            if compute_properties:
                try:
                    mol["molecular_weight"] = round(Descriptors.ExactMolWt(rdkit_mol), 2)
                    mol["molecular_formula"] = rdMolDescriptors.CalcMolFormula(rdkit_mol)
                    mol["logp"] = round(Descriptors.MolLogP(rdkit_mol), 2)
                    mol["tpsa"] = round(Descriptors.TPSA(rdkit_mol), 2)
                    mol["num_heavy_atoms"] = rdkit_mol.GetNumHeavyAtoms()
                    mol["num_rotatable_bonds"] = rdMolDescriptors.CalcNumRotatableBonds(rdkit_mol)
                    mol["num_h_donors"] = rdMolDescriptors.CalcNumHBD(rdkit_mol)
                    mol["num_h_acceptors"] = rdMolDescriptors.CalcNumHBA(rdkit_mol)
                    mol["num_rings"] = rdMolDescriptors.CalcNumRings(rdkit_mol)
                    stats["properties_computed"] += 1
                except Exception as e:
                    print(f"    Warning: Could not compute properties for {mol.get('molecule_id', 'unknown')}: {e}")

        except Exception as e:
            mol["smiles_valid"] = False
            mol["smiles_error"] = str(e)
            stats["invalid_smiles"] += 1
            print(f"    ✗ Error validating {mol.get('name_as_written', mol.get('molecule_id', 'unknown'))}: {e}")

    print(f"[VALIDATE] Complete: {stats['valid_smiles']}/{stats['with_smiles']} SMILES valid, {stats['properties_computed']} properties computed")

    return stats


def compute_molecular_properties(smiles: str) -> Optional[dict]:
    """
    Compute molecular properties for a single SMILES string.

    Args:
        smiles: Valid SMILES string

    Returns:
        Dict with computed properties, or None on failure
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        return {
            "molecular_weight": round(Descriptors.ExactMolWt(mol), 2),
            "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
            "logp": round(Descriptors.MolLogP(mol), 2),
            "tpsa": round(Descriptors.TPSA(mol), 2),
            "num_heavy_atoms": mol.GetNumHeavyAtoms(),
            "num_rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
            "num_h_donors": rdMolDescriptors.CalcNumHBD(mol),
            "num_h_acceptors": rdMolDescriptors.CalcNumHBA(mol),
            "num_rings": rdMolDescriptors.CalcNumRings(mol)
        }

    except Exception:
        return None


def classify_amphiphile(smiles: str) -> Optional[dict]:
    """
    Classify an amphiphilic compound based on its structure.

    Args:
        smiles: Valid SMILES string

    Returns:
        Dict with classification info, or None on failure
    """
    try:
        from rdkit import Chem

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        classification = {
            "head_group_class": None,
            "charge_type": None,
            "tail_count": 0
        }

        smiles_upper = smiles.upper()

        # Detect head group type
        if "[N+]" in smiles:
            classification["head_group_class"] = "quaternary_ammonium"
            classification["charge_type"] = "cationic"
        elif "[P+]" in smiles:
            classification["head_group_class"] = "quaternary_phosphonium"
            classification["charge_type"] = "cationic"
        elif "[S+]" in smiles:
            classification["head_group_class"] = "sulfonium"
            classification["charge_type"] = "cationic"
        elif "N+" in smiles_upper and "C(=N)" in smiles:
            classification["head_group_class"] = "guanidinium"
            classification["charge_type"] = "cationic"
        elif "[O-]" in smiles or "C(=O)[O-]" in smiles:
            classification["head_group_class"] = "carboxylate"
            classification["charge_type"] = "anionic"
        elif "S(=O)(=O)[O-]" in smiles:
            classification["head_group_class"] = "sulfonate"
            classification["charge_type"] = "anionic"
        elif "P(=O)([O-])" in smiles:
            classification["head_group_class"] = "phosphate"
            classification["charge_type"] = "anionic"

        # Count long carbon chains (potential tails)
        # This is a simplified heuristic
        import re
        long_chains = re.findall(r'C{8,}', smiles)
        classification["tail_count"] = len(long_chains)

        return classification

    except Exception:
        return None
