# escalation_tool.py

import uuid


def escalate_case(reason: str, context: dict):
    """
    Create an escalation case for human/professional review.
    """

    case_id = "DC-" + str(uuid.uuid4())[:8].upper()

    return {
        "escalated": True,
        "case_id": case_id,
        "reason": reason,
        "context": context,
        "message": "This case requires professional review."
    }


if __name__ == "__main__":

    result = escalate_case(
        reason="Interaction information is uncertain",
        context={
            "drug_a": "unknown_drug",
            "drug_b": "amlodipine"
        }
    )

    print(result)