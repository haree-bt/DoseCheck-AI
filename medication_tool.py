# medication_tool.py

MEDICINES = {
    "paracetamol": {
        "name": "Paracetamol",
        "category": "Pain reliever",
        "demo_note": "Demo database entry. Verify against an authoritative source."
    },

    "ibuprofen": {
        "name": "Ibuprofen",
        "category": "NSAID",
        "demo_note": "Demo database entry. Verify against an authoritative source."
    },

    "amlodipine": {
        "name": "Amlodipine",
        "category": "Calcium channel blocker",
        "demo_note": "Demo database entry. Verify against an authoritative source."
    }
}


def lookup_medicine(medicine_name: str):
    """
    Look up a medicine in the demo medicine database.
    """

    key = medicine_name.strip().lower()

    if key in MEDICINES:
        return {
            "found": True,
            "medicine": MEDICINES[key]
        }

    return {
        "found": False,
        "medicine": None,
        "message": "Medicine not found in the demo database. Review required."
    }


if __name__ == "__main__":
    print(lookup_medicine("paracetamol"))
    print(lookup_medicine("unknown_medicine"))