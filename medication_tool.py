# medication_tool.py
import re

# Authoritative catalog of common prescription and OTC medications
MEDICINES = {
    "paracetamol": {
        "name": "Paracetamol / Acetaminophen",
        "category": "Analgesic / Antipyretic",
        "class": "pain_reliever",
        "max_daily_adult": "4,000 mg",
        "clinical_note": "Risk of hepatotoxicity (liver injury) if maximum daily dose is exceeded or combined with alcohol."
    },
    "ibuprofen": {
        "name": "Ibuprofen",
        "category": "Nonsteroidal Anti-inflammatory Drug (NSAID)",
        "class": "nsaid",
        "max_daily_adult": "1,200 mg OTC (up to 3,200 mg prescription)",
        "clinical_note": "Gastrointestinal bleeding and renal impairment risk. Contraindicated with other NSAIDs and blood thinners."
    },
    "aspirin": {
        "name": "Aspirin",
        "category": "NSAID / Antiplatelet",
        "class": "nsaid",
        "clinical_note": "Bleeding hazard when co-administered with anticoagulants or other NSAIDs."
    },
    "naproxen": {
        "name": "Naproxen",
        "category": "NSAID",
        "class": "nsaid",
        "clinical_note": "Do not combine with ibuprofen or other NSAIDs due to compounded GI bleeding risk."
    },
    "amlodipine": {
        "name": "Amlodipine",
        "category": "Calcium channel blocker (Antihypertensive)",
        "class": "antihypertensive",
        "clinical_note": "Used for hypertension. NSAIDs can blunt antihypertensive efficacy."
    },
    "warfarin": {
        "name": "Warfarin",
        "category": "Vitamin K Antagonist (Anticoagulant)",
        "class": "anticoagulant",
        "clinical_note": "High hemorrhage risk. Major interactions with NSAIDs, aspirin, and high-dose acetaminophen."
    },
    "apixaban": {
        "name": "Apixaban (Eliquis)",
        "category": "Direct Oral Anticoagulant (DOAC)",
        "class": "anticoagulant",
        "clinical_note": "Severe bleeding risk if combined with NSAIDs."
    },
    "rivaroxaban": {
        "name": "Rivaroxaban (Xarelto)",
        "category": "Direct Oral Anticoagulant (DOAC)",
        "class": "anticoagulant",
        "clinical_note": "Severe bleeding risk if combined with NSAIDs."
    },
    "blood_thinners": {
        "name": "Anticoagulants / Blood Thinners Class",
        "category": "Anticoagulant Class",
        "class": "anticoagulant",
        "clinical_note": "Includes warfarin, apixaban, rivaroxaban, heparin. High bleeding risk with NSAIDs."
    },
    "lisinopril": {
        "name": "Lisinopril",
        "category": "ACE Inhibitor (Antihypertensive)",
        "class": "antihypertensive",
        "clinical_note": "NSAIDs can reduce blood pressure effect and increase nephrotoxicity risk."
    },
    "metformin": {
        "name": "Metformin",
        "category": "Biguanide (Antidiabetic)",
        "class": "antidiabetic",
        "clinical_note": "Standard first-line therapy for type 2 diabetes. Risk of lactic acidosis with heavy alcohol."
    },
    "atorvastatin": {
        "name": "Atorvastatin (Lipitor)",
        "category": "HMG-CoA Reductase Inhibitor (Statin)",
        "class": "statin",
        "clinical_note": "Used for hyperlipidemia. Monitor for myopathy."
    },
    "simvastatin": {
        "name": "Simvastatin (Zocor)",
        "category": "HMG-CoA Reductase Inhibitor (Statin)",
        "class": "statin",
        "clinical_note": "Dose capped at 20mg when taken concurrently with amlodipine."
    },
    "metoprolol": {
        "name": "Metoprolol",
        "category": "Beta-Blocker",
        "class": "antihypertensive",
        "clinical_note": "Used for hypertension and angina."
    },
    "omeprazole": {
        "name": "Omeprazole",
        "category": "Proton Pump Inhibitor (PPI)",
        "class": "gastroprotective",
        "clinical_note": "Reduces gastric acid production."
    },
    "amoxicillin": {
        "name": "Amoxicillin",
        "category": "Aminopenicillin Antibiotic",
        "class": "antibiotic",
        "clinical_note": "Contraindicated in severe penicillin allergy."
    },
    "penicillin": {
        "name": "Penicillin",
        "category": "Beta-lactam Antibiotic",
        "class": "antibiotic",
        "clinical_note": "Severe anaphylaxis risk in allergic patients."
    },
    "ciprofloxacin": {
        "name": "Ciprofloxacin",
        "category": "Fluoroquinolone Antibiotic",
        "class": "antibiotic",
        "clinical_note": "Boxed warnings for tendonitis and tendon rupture."
    },
    "paxlovid": {
        "name": "Paxlovid (Nirmatrelvir/Ritonavir)",
        "category": "Antiviral",
        "class": "antiviral",
        "clinical_note": "Strong CYP3A inhibitor. Extensive, potentially life-threatening drug-drug interactions."
    },
    "st_johns_wort": {
        "name": "St. John's Wort",
        "category": "Herbal Supplement / CYP3A4 Inducer",
        "class": "supplement",
        "clinical_note": "Potent CYP3A4 and P-gp inducer. Severely reduces concentrations of Paxlovid, oral contraceptives, etc."
    },
    "alcohol": {
        "name": "Alcohol (Ethanol)",
        "category": "Depressant / Toxicant",
        "class": "substance",
        "clinical_note": "Compounded GI bleeding with NSAIDs; acute hepatotoxicity risk with acetaminophen."
    }
}

# Alias mapping from brand names and common synonyms to canonical keys
ALIASES = {
    "acetaminophen": "paracetamol",
    "paracetamol": "paracetamol",
    "tylenol": "paracetamol",
    "panadol": "paracetamol",
    "apap": "paracetamol",

    "ibuprofen": "ibuprofen",
    "advil": "ibuprofen",
    "motrin": "ibuprofen",
    "nurofen": "ibuprofen",

    "aspirin": "aspirin",
    "bayer": "aspirin",
    "ecotrin": "aspirin",
    "acetylsalicylic acid": "aspirin",

    "naproxen": "naproxen",
    "aleve": "naproxen",
    "naprosyn": "naproxen",

    "amlodipine": "amlodipine",
    "norvasc": "amlodipine",

    "warfarin": "warfarin",
    "coumadin": "warfarin",
    "jantoven": "warfarin",

    "apixaban": "apixaban",
    "eliquis": "apixaban",

    "rivaroxaban": "rivaroxaban",
    "xarelto": "rivaroxaban",

    "blood thinner": "blood_thinners",
    "blood thinners": "blood_thinners",
    "blood-thinner": "blood_thinners",
    "blood-thinners": "blood_thinners",
    "anticoagulant": "blood_thinners",
    "anticoagulants": "blood_thinners",

    "lisinopril": "lisinopril",
    "prinivil": "lisinopril",
    "zestril": "lisinopril",

    "metformin": "metformin",
    "glucophage": "metformin",

    "atorvastatin": "atorvastatin",
    "lipitor": "atorvastatin",

    "simvastatin": "simvastatin",
    "zocor": "simvastatin",

    "metoprolol": "metoprolol",
    "toprol": "metoprolol",
    "lopressor": "metoprolol",

    "omeprazole": "omeprazole",
    "prilosec": "omeprazole",

    "amoxicillin": "amoxicillin",
    "amoxil": "amoxicillin",
    "augmentin": "amoxicillin",

    "penicillin": "penicillin",

    "ciprofloxacin": "ciprofloxacin",
    "cipro": "ciprofloxacin",

    "paxlovid": "paxlovid",
    "nirmatrelvir": "paxlovid",

    "st. john's wort": "st_johns_wort",
    "st john's wort": "st_johns_wort",
    "st johns wort": "st_johns_wort",
    "st. johns wort": "st_johns_wort",
    "hypericum": "st_johns_wort",

    "alcohol": "alcohol",
    "beer": "alcohol",
    "wine": "alcohol",
    "liquor": "alcohol",
    "ethanol": "alcohol"
}


def canonicalize_drug(drug_name: str) -> str:
    """Resolve brand names, slang, or spaces to canonical medication key."""
    cleaned = drug_name.strip().lower()
    return ALIASES.get(cleaned, cleaned)


def lookup_medicine(medicine_name: str):
    """
    Look up a medicine in the clinical database using canonical key or alias.
    """
    canonical = canonicalize_drug(medicine_name)

    if canonical in MEDICINES:
        return {
            "found": True,
            "canonical_id": canonical,
            "medicine": MEDICINES[canonical]
        }

    return {
        "found": False,
        "canonical_id": canonical,
        "medicine": None,
        "message": f"Medicine '{medicine_name}' not found in the verified database. Clinician review required."
    }


def extract_known_medicines(text: str) -> list[str]:
    """
    Scan free-text query and return recognized medicine canonical keys.
    """
    lowered = text.lower()
    found = []
    # Sort aliases by descending length so multi-word terms (e.g. 'blood thinners') match first
    sorted_aliases = sorted(ALIASES.keys(), key=lambda x: len(x), reverse=True)

    for alias in sorted_aliases:
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, lowered):
            canonical = ALIASES[alias]
            if canonical not in found:
                found.append(canonical)

    return found


if __name__ == "__main__":
    print(lookup_medicine("tylenol"))
    print(lookup_medicine("Advil"))
    print(lookup_medicine("blood thinners"))
    print("Extracted from 'Can I take Advil with blood thinners?':", extract_known_medicines("Can I take Advil with blood thinners?"))