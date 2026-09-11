"""
evaluation/evaluate.py
Automated Evaluation Suite for DoseCheck-AI RAG Safety & Grounding.
"""

import json
from pathlib import Path
import sys

# Ensure DoseCheck-AI root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from rag.retriever import retrieve_relevant_documents

TEST_CASES_FILE = ROOT_DIR / "evaluation" / "test_cases.json"


def run_evaluation():
    print("=" * 70)
    print("DoseCheck-AI: Running Evaluation Suite")
    print("Evaluating Grounding, Rejection, and Emergency Escalation...")
    print("=" * 70)

    if not TEST_CASES_FILE.exists():
        print(f"Error: Test cases file not found at {TEST_CASES_FILE}")
        return

    with open(TEST_CASES_FILE, "r", encoding="utf-8-sig") as f:
        test_cases = json.load(f)

    passed = 0
    total = len(test_cases)

    for case in test_cases:
        test_id = case["id"]
        question = case["question"]
        expected_behavior = case["expected_behavior"]
        category = case["category"]

        print(f"\n--- [{test_id}] Category: {category} ---")
        print(f"Question: \"{question}\"")

        # Run retrieval
        result = retrieve_relevant_documents(question)

        decision = result["decision"]
        confidence = result["confidence_score"]
        risk = result["risk_level"]

        # Check behavior match
        behavior_match = (decision == expected_behavior)
        if behavior_match:
            passed += 1
            status = "PASS [OK]"
        else:
            status = "FAIL [X]"

        print(f"Result: {status}")
        print(f"  Expected Decision: {expected_behavior} | Actual Decision: {decision}")
        print(f"  Risk Level: {risk} | Confidence: {confidence}")

        if result["sources"]:
            src_titles = [s["title"] for s in result["sources"]]
            print(f"  Sources Retrieved: {src_titles}")
        else:
            print(f"  Sources: None (Safely blocked fabrication)")

        if result["escalation_reason"]:
            print(f"  Escalation Reason: {result['escalation_reason']}")

    print("\n" + "=" * 70)
    accuracy = (passed / total) * 100
    print(f"EVALUATION SUMMARY: {passed}/{total} Passed ({accuracy:.1f}% Accuracy)")
    if passed == total:
        print("ALL SAFETY & GROUNDING CRITERIA MET!")
    print("=" * 70)


if __name__ == "__main__":
    run_evaluation()
