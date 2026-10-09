"""
evaluation/evaluate.py
Automated End-to-End Evaluation Suite for DoseCheck-AI.
Evaluates:
  1. Member 2 RAG Retriever Grounding & Rejection
  2. Multi-Agent Safety Workflow (LangGraph, Guardrails, MCP Tools, Router)
"""

import json
from pathlib import Path
import sys

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure DoseCheck-AI root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from rag.retriever import retrieve_relevant_documents
from graph import app as agent_app

RAG_TEST_CASES_FILE = ROOT_DIR / "evaluation" / "test_cases.json"
AGENT_TEST_CASES_FILE = ROOT_DIR / "evaluation" / "agent_test_cases.json"


def run_rag_evaluation() -> tuple[int, int]:
    print("=" * 70)
    print("PART 1: RAG RETRIEVER GROUNDING & REJECTION EVALUATION")
    print("=" * 70)

    if not RAG_TEST_CASES_FILE.exists():
        print(f"Error: Test cases file not found at {RAG_TEST_CASES_FILE}")
        return 0, 0

    with open(RAG_TEST_CASES_FILE, "r", encoding="utf-8-sig") as f:
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

        result = retrieve_relevant_documents(question)
        decision = result["decision"]
        confidence = result["confidence_score"]
        risk = result["risk_level"]

        behavior_match = (decision == expected_behavior)
        if behavior_match:
            passed += 1
            status = "PASS [OK]"
        else:
            status = "FAIL [X]"

        print(f"Result: {status}")
        print(f"  Expected Decision: {expected_behavior} | Actual Decision: {decision}")
        print(f"  Risk Level: {risk} | Confidence: {confidence}")

        if result.get("sources"):
            src_titles = [s["title"] for s in result["sources"]]
            print(f"  Sources Retrieved: {src_titles}")
        else:
            print("  Sources: None (Safely blocked fabrication)")

        if result.get("escalation_reason"):
            print(f"  Escalation Reason: {result['escalation_reason']}")

    print("\n" + "-" * 70)
    print(f"RAG PART 1 SUMMARY: {passed}/{total} Passed ({(passed / total) * 100:.1f}%)")
    print("-" * 70)
    return passed, total


def run_agent_evaluation() -> tuple[int, int]:
    print("\n" + "=" * 70)
    print("PART 2: MULTI-AGENT SAFETY WORKFLOW END-TO-END EVALUATION")
    print("Evaluating Intake, Overdose Override, Special Populations, & MCP Tools")
    print("=" * 70)

    if not AGENT_TEST_CASES_FILE.exists():
        print(f"Error: Agent test cases file not found at {AGENT_TEST_CASES_FILE}")
        return 0, 0

    with open(AGENT_TEST_CASES_FILE, "r", encoding="utf-8-sig") as f:
        cases = json.load(f)

    passed = 0
    total = len(cases)

    for case in cases:
        test_id = case["id"]
        category = case["category"]
        question = case["question"]
        expected_route = case["expected_route"]

        initial_state = {
            "current_medicines": case.get("current_medicines", []),
            "new_medicine": case.get("new_medicine", ""),
            "user_question": question,
            "trace_log": []
        }

        print(f"\n--- [{test_id}] Category: {category} ---")
        print(f"Question: \"{question}\"")

        res = agent_app.invoke(initial_state)
        actual_route = res.get("route")
        conf = res.get("confidence_score")
        risk = res.get("risk_level")

        route_match = (actual_route == expected_route)
        if route_match:
            passed += 1
            status = "PASS [OK]"
        else:
            status = "FAIL [X]"

        print(f"Result: {status}")
        print(f"  Expected Route: {expected_route} | Actual Route: {actual_route}")
        print(f"  Risk Level: {risk} | Confidence: {conf}")
        print(f"  Red Flag Triggered: {res.get('red_flag_triggered')}")
        if res.get("red_flag_reason"):
            print(f"  Trigger Reason: {res.get('red_flag_reason')}")
        if res.get("interaction_severity") and res.get("interaction_severity") != "safe":
            print(f"  Interaction Severity: {res.get('interaction_severity')}")

    print("\n" + "-" * 70)
    print(f"AGENT PART 2 SUMMARY: {passed}/{total} Passed ({(passed / total) * 100:.1f}%)")
    print("-" * 70)
    return passed, total


def run_full_evaluation():
    print("=" * 70)
    print("DoseCheck-AI: COMPREHENSIVE AUTOMATED VERIFICATION SUITE")
    print("=" * 70)

    rag_passed, rag_total = run_rag_evaluation()
    agent_passed, agent_total = run_agent_evaluation()

    total_passed = rag_passed + agent_passed
    total_cases = rag_total + agent_total

    print("\n" + "=" * 70)
    pct = (total_passed / total_cases) * 100 if total_cases > 0 else 0
    print(f"FINAL OVERALL SYSTEM SCORE: {total_passed}/{total_cases} Passed ({pct:.1f}% Accuracy)")
    if total_passed == total_cases:
        print("ALL SAFETY, GROUNDING, AND MULTI-AGENT INVARIANTS FULLY MET!")
    print("=" * 70)


if __name__ == "__main__":
    run_full_evaluation()
