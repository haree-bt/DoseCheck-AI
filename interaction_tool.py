# interaction_tool.py


INTERACTIONS = {
    ("ibuprofen", "amlodipine"): {
        "risk": "moderate",
        "requires_review": True,
        "message": "Potential interaction identified. Professional review is recommended."
    },

    ("paracetamol", "amlodipine"): {
        "risk": "low",
        "requires_review": False,
        "message": "No major interaction identified in the demo database."
    }
}


def check_interaction(drug_a: str, drug_b: str):
    """
    Check two medicines against the demo interaction database.
    """

    a = drug_a.strip().lower()
    b = drug_b.strip().lower()

    # Check both possible orders
    interaction = INTERACTIONS.get((a, b))

    if interaction is None:
        interaction = INTERACTIONS.get((b, a))

    # If the combination is not in our database,
    # we do NOT assume it is safe.
    if interaction is None:
        return {
            "found": False,
            "drug_a": drug_a,
            "drug_b": drug_b,
            "risk": "unknown",
            "requires_review": True,
            "message": "Interaction information is unavailable in the demo database. Review required."
        }

    return {
        "found": True,
        "drug_a": drug_a,
        "drug_b": drug_b,
        **interaction
    }


if __name__ == "__main__":

    print("Test 1:")
    print(check_interaction("ibuprofen", "amlodipine"))

    print("\nTest 2:")
    print(check_interaction("paracetamol", "amlodipine"))

    print("\nTest 3:")
    print(check_interaction("unknown_drug", "amlodipine"))