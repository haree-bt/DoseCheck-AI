# interaction_tool.py

from medication_tool import canonicalize_drug, MEDICINES

# Direct pair interactions catalog
INTERACTIONS = {
    ("ibuprofen", "amlodipine"): {
        "risk": "moderate",
        "requires_review": True,
        "message": "Potential interaction: Ibuprofen (NSAID) can cause fluid retention and blunt the blood-pressure lowering efficacy of amlodipine."
    },
    ("paracetamol", "amlodipine"): {
        "risk": "low",
        "requires_review": False,
        "message": "No major interaction identified between paracetamol and amlodipine in clinical guidelines."
    },
    ("ibuprofen", "warfarin"): {
        "risk": "high",
        "requires_review": True,
        "message": "DANGEROUS INTERACTION: Co-administration of ibuprofen with warfarin dramatically elevates the risk of severe gastrointestinal bleeding and major hemorrhage."
    },
    ("ibuprofen", "blood_thinners"): {
        "risk": "high",
        "requires_review": True,
        "message": "DANGEROUS INTERACTION: NSAIDs combined with anticoagulants/blood thinners substantially increase the incidence of gastrointestinal bleeding."
    },
    ("ibuprofen", "aspirin"): {
        "risk": "high",
        "requires_review": True,
        "message": "DANGEROUS INTERACTION: Combining multiple NSAIDs compounds gastric ulceration and bleeding risk, and ibuprofen may interfere with low-dose aspirin's cardioprotective antiplatelet effect."
    },
    ("ibuprofen", "naproxen"): {
        "risk": "high",
        "requires_review": True,
        "message": "DANGEROUS INTERACTION: Concomitant use of multiple systemic NSAIDs is contraindicated due to additive gastrointestinal toxicity without increased efficacy."
    },
    ("ibuprofen", "alcohol"): {
        "risk": "moderate",
        "requires_review": True,
        "message": "MODERATE RISK: Chronic or excessive alcohol use with ibuprofen significantly heightens the hazard of stomach mucosal damage and GI bleeding."
    },
    ("paracetamol", "alcohol"): {
        "risk": "high",
        "requires_review": True,
        "message": "DANGEROUS INTERACTION: Chronic or concurrent alcohol consumption with acetaminophen drastically depletes hepatic glutathione, predisposing to severe hepatotoxicity (acute liver injury)."
    },
    ("paracetamol", "warfarin"): {
        "risk": "moderate",
        "requires_review": True,
        "message": "MODERATE RISK: Regular daily intake of paracetamol (>2,000 mg/day) can potentiate warfarin's hypoprothrombinemic effect and prolong INR."
    },
    ("paxlovid", "st_johns_wort"): {
        "risk": "high",
        "requires_review": True,
        "message": "CONTRAINDICATED INTERACTION: St. John's Wort significantly reduces Paxlovid (ritonavir) plasma concentrations via CYP3A induction, causing loss of virologic efficacy."
    },
    ("lisinopril", "ibuprofen"): {
        "risk": "high",
        "requires_review": True,
        "message": "DANGEROUS INTERACTION: NSAIDs attenuate the antihypertensive effect of ACE inhibitors and drastically increase the risk of acute renal failure (nephrotoxicity)."
    }
}


def _check_class_interaction(canon_a: str, canon_b: str):
    """
    Evaluate pharmacological class-level interactions when exact drug pair isn't keyed.
    """
    med_a = MEDICINES.get(canon_a, {})
    med_b = MEDICINES.get(canon_b, {})
    class_a = med_a.get("class", "")
    class_b = med_b.get("class", "")

    # NSAID + Anticoagulant rule
    if (class_a == "nsaid" and class_b == "anticoagulant") or (class_b == "nsaid" and class_a == "anticoagulant"):
        return {
            "risk": "high",
            "requires_review": True,
            "message": f"DANGEROUS CLASS INTERACTION: Combining NSAID ({med_a.get('name', canon_a)}) with Anticoagulant ({med_b.get('name', canon_b)}) markedly elevates systemic bleeding and gastrointestinal hemorrhage hazard."
        }

    # NSAID + NSAID rule
    if class_a == "nsaid" and class_b == "nsaid":
        return {
            "risk": "high",
            "requires_review": True,
            "message": f"DANGEROUS CLASS INTERACTION: Concurrent use of multiple NSAIDs ({med_a.get('name', canon_a)} and {med_b.get('name', canon_b)}) causes additive gastrointestinal and renal toxicity."
        }

    # NSAID + Antihypertensive rule
    if (class_a == "nsaid" and class_b == "antihypertensive") or (class_b == "nsaid" and class_a == "antihypertensive"):
        return {
            "risk": "moderate",
            "requires_review": True,
            "message": f"MODERATE INTERACTION: NSAIDs can induce sodium/water retention and counteract the blood pressure lowering effect of {med_b.get('name', canon_b)}."
        }

    return None


def check_interaction(drug_a: str, drug_b: str):
    """
    Check two medicines against the clinical interaction database and class rules.
    """
    a = canonicalize_drug(drug_a)
    b = canonicalize_drug(drug_b)

    # Check direct pair in both orders
    interaction = INTERACTIONS.get((a, b))
    if interaction is None:
        interaction = INTERACTIONS.get((b, a))

    # Check class-level rules if not explicitly keyed
    if interaction is None:
        class_interaction = _check_class_interaction(a, b)
        if class_interaction:
            interaction = class_interaction

    # If the combination is not in our database or rules, do not assume safety
    if interaction is None:
        return {
            "found": False,
            "drug_a": drug_a,
            "drug_b": drug_b,
            "canonical_a": a,
            "canonical_b": b,
            "risk": "unknown",
            "requires_review": True,
            "message": f"Specific interaction data between '{drug_a}' and '{drug_b}' is not in the local database. Professional clinician/pharmacist review is required."
        }

    return {
        "found": True,
        "drug_a": drug_a,
        "drug_b": drug_b,
        "canonical_a": a,
        "canonical_b": b,
        **interaction
    }


if __name__ == "__main__":
    print("Test 1 (Ibuprofen + Amlodipine):")
    print(check_interaction("ibuprofen", "amlodipine"))

    print("\nTest 2 (Ibuprofen + Blood thinners):")
    print(check_interaction("ibuprofen", "blood thinners"))

    print("\nTest 3 (Advil + Warfarin):")
    print(check_interaction("Advil", "Warfarin"))

    print("\nTest 4 (Tylenol + Alcohol):")
    print(check_interaction("tylenol", "alcohol"))