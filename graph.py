import sys
from langgraph.graph import StateGraph, END
from state import DoseCheckState

# Teammates' modules
from safety_guardrail import (
    detect_red_flags,
    detect_toxic_dosage,
    detect_vulnerable_populations,
    ConfidenceInputs,
    compute_confidence,
    classify_risk,
    RiskThresholds,
)
from rag.retriever import retrieve_relevant_documents
from interaction_tool import check_interaction
from medication_tool import (
    lookup_medicine,
    extract_known_medicines,
    canonicalize_drug,
    MEDICINES
)
from escalation_tool import escalate_case
from clinical_synthesizer import synthesize_clinical_assessment, format_clinical_markdown


def log_step(state: DoseCheckState, node_name: str, output: dict, reason: str = "") -> dict:
    """Observability requirement: record each node execution into trace_log."""
    entry = {"node": node_name, "output": output, "reason": reason}
    return {"trace_log": state.get("trace_log", []) + [entry]}


# --- 1. Intake Agent ---
def intake_agent(state: DoseCheckState) -> dict:
    question = state.get("user_question", "")
    current_meds = list(state.get("current_medicines", []))
    new_med = state.get("new_medicine", "").strip()

    # Extract all recognized medicine entities from question
    found_meds = extract_known_medicines(question)

    # If new_medicine was omitted, infer it from the question
    if not new_med and found_meds:
        new_med = found_meds[0]
        extra_meds = found_meds[1:]
    else:
        extra_meds = [m for m in found_meds if m != canonicalize_drug(new_med)]

    # Merge any remaining medicines into current_meds if not already present
    current_meds_canon = [canonicalize_drug(m) for m in current_meds]
    for em in extra_meds:
        if em not in current_meds_canon:
            current_meds.append(em)
            current_meds_canon.append(em)

    all_extracted_meds = list(dict.fromkeys(([new_med] if new_med else []) + current_meds))

    # Extract symptoms from question
    symptom_keywords = [
        "headache", "fever", "pain", "swelling", "breathing", "cough",
        "nausea", "vomiting", "rash", "dizziness", "bleeding", "chest pain",
        "stomach pain", "heartburn", "diarrhea"
    ]
    found_symptoms = [s for s in symptom_keywords if s in question.lower()]

    # Infer intent
    if len(all_extracted_meds) >= 2 or (current_meds and new_med):
        intent = "drug_interaction_check"
    elif any(w in question.lower() for w in ["combine", "together", "with", "take both", "interaction", "mix"]):
        intent = "drug_interaction_check"
    elif any(w in question.lower() for w in ["dose", "dosage", "how much", "max", "limit"]):
        intent = "dosage_guidance"
    elif any(w in question.lower() for w in ["miss", "forgot", "skip"]):
        intent = "missed_dose_guidance"
    else:
        intent = "general_medication_query"

    result = {
        "extracted_intent": intent,
        "extracted_symptoms": found_symptoms,
        "extracted_medicines": all_extracted_meds,
        "new_medicine": new_med,
        "current_medicines": current_meds,
    }
    return {**result, **log_step(state, "intake_agent", result, reason=f"intent={intent}, meds={all_extracted_meds}")}


# --- 2. Red-Flag & Safety Agent ---
def red_flag_agent(state: DoseCheckState) -> dict:
    text_to_check = (
        state.get("user_question", "")
        + " "
        + state.get("new_medicine", "")
        + " "
        + " ".join(state.get("current_medicines", []))
        + " "
        + " ".join(state.get("extracted_symptoms", []))
    )

    red_flags = detect_red_flags(text_to_check)
    toxic_info = detect_toxic_dosage(text_to_check)
    vulnerable_pops = detect_vulnerable_populations(text_to_check)

    triggered = len(red_flags) > 0 or (toxic_info is not None)

    reasons = []
    if red_flags:
        reasons.append(f"Emergency symptoms: {', '.join(red_flags)}")
    if toxic_info:
        reasons.append(f"Toxic overdose: {toxic_info['reason']}")

    reason = " | ".join(reasons) if reasons else None
    pop_warnings = [p["message"] for p in vulnerable_pops]

    result = {
        "red_flag_triggered": triggered,
        "red_flag_reason": reason,
        "toxic_dose_detected": toxic_info is not None,
        "toxic_dose_reason": toxic_info["reason"] if toxic_info else None,
        "vulnerable_population_warnings": pop_warnings,
    }
    return {**result, **log_step(state, "red_flag_agent", result, reason=f"triggered={triggered}")}


# --- 3. Retrieval Agent (RAG) ---
def retrieval_agent(state: DoseCheckState) -> dict:
    query_parts = []
    if state.get("new_medicine"):
        query_parts.append(f"Medicine: {state['new_medicine']}")
    if state.get("current_medicines"):
        query_parts.append(f"Current medications: {', '.join(state['current_medicines'])}")
    if state.get("user_question"):
        query_parts.append(f"Question: {state['user_question']}")

    search_query = ". ".join(query_parts) if query_parts else state.get("user_question", "")
    rag_output = retrieve_relevant_documents(search_query)

    chunks = [c["text"] for c in rag_output.get("top_chunks", [])]
    sources = [s["title"] for s in rag_output.get("sources", [])]
    top_chunks = rag_output.get("top_chunks", [])
    closest_distance = top_chunks[0].get("distance") if top_chunks else None

    result = {
        "retrieved_chunks": chunks,
        "retrieved_sources": sources,
        "retrieved_context": rag_output.get("answer_context", ""),
        "retrieval_confidence": rag_output.get("confidence_score", 0.0),
        "retrieval_distance": closest_distance,
        "retrieved_top_chunks": top_chunks,
        "retrieved_source_details": rag_output.get("sources", []),
    }
    return {
        **result,
        **log_step(
            state,
            "retrieval_agent",
            result,
            reason=f"decision={rag_output['decision']}, confidence={rag_output['confidence_score']}, distance={closest_distance}"
        )
    }


# --- 4. Medication & Interaction Tool (MCP) ---
RISK_TO_SEVERITY = {
    "low": "safe",
    "moderate": "caution",
    "high": "dangerous",
    "unknown": "unknown",
}

def interaction_tool_node(state: DoseCheckState) -> dict:
    current_meds = list(state.get("current_medicines", []))
    new_med = state.get("new_medicine", "")
    all_meds = list(state.get("extracted_medicines", []))

    tool_res = None
    severity = "safe"
    explanation = "No potential interactions identified or single medication inquiry."

    if new_med and current_meds:
        explanations = []
        highest_severity = "safe"
        severity_rank = {"safe": 0, "caution": 1, "unknown": 2, "dangerous": 3}

        for med in current_meds:
            if canonicalize_drug(new_med) == canonicalize_drug(med):
                continue
            check = check_interaction(new_med, med)
            tool_res = check
            risk = check.get("risk", "unknown")
            sev = RISK_TO_SEVERITY.get(risk, "unknown")
            explanations.append(check.get("message", "Interaction checked."))
            if severity_rank.get(sev, 0) > severity_rank.get(highest_severity, 0):
                highest_severity = sev
            if highest_severity == "dangerous":
                break

        severity = highest_severity
        explanation = "\n\n".join(explanations) if explanations else "No interaction detected."
    elif len(all_meds) >= 2:
        check = check_interaction(all_meds[0], all_meds[1])
        tool_res = check
        risk = check.get("risk", "unknown")
        severity = RISK_TO_SEVERITY.get(risk, "unknown")
        explanation = check.get("message", "Interaction checked.")
    elif new_med:
        lookup = lookup_medicine(new_med)
        tool_res = lookup
        if lookup.get("found"):
            severity = "safe"
            med_info = lookup["medicine"]
            note = med_info.get("clinical_note", "")
            explanation = f"Verified medicine: {med_info['name']} ({med_info['category']}). {note}"
        else:
            severity = "unknown"
            explanation = lookup.get("message", "Medicine not found in database.")

    result = {
        "tool_result": tool_res,
        "interaction_severity": severity,
        "interaction_explanation": explanation
    }
    return {**result, **log_step(state, "interaction_tool", result, reason=f"severity={severity}")}


# --- 5. Response / Drafter Agent ---
def response_agent(state: DoseCheckState) -> dict:
    chunks = state.get("retrieved_chunks", [])
    summary = synthesize_clinical_assessment({**state, "route": "safe_answer"})
    draft = format_clinical_markdown(summary)

    result = {
        "draft_answer": draft,
        "cited_chunks": chunks[:2] if chunks else [],
        "clinical_summary": summary
    }
    return {**result, **log_step(state, "response_agent", result)}


# --- 6. Safety Critic Agent ---
def safety_critic(state: DoseCheckState) -> dict:
    chunks = state.get("retrieved_chunks", [])
    severity = state.get("interaction_severity", "unknown")
    red_flag = state.get("red_flag_triggered", False)
    pop_warnings = state.get("vulnerable_population_warnings", [])
    closest_dist = state.get("retrieval_distance")
    rag_conf = state.get("retrieval_confidence") or 0.0

    # 1. Special vulnerable populations (pediatric, pregnancy) immediately restrict confidence
    if pop_warnings:
        result = {
            "grounded": len(chunks) > 0,
            "confidence_score": 0.25,
            "risk_level": "HIGH",
        }
        return {
            **result,
            **log_step(
                state,
                "safety_critic",
                result,
                reason=f"grounded={len(chunks) > 0}, confidence=0.25, risk=HIGH (special population restriction)"
            )
        }

    # 2. Dynamic retrieval relevance based on vector distance
    if not chunks or (closest_dist is not None and closest_dist > 1.15):
        retrieval_relevance = max(0.10, min(0.40, rag_conf))
    elif closest_dist is not None:
        relevance = 1.0 - (closest_dist * 0.35)
        retrieval_relevance = round(max(0.35, min(0.96, relevance)), 2)
    else:
        retrieval_relevance = round(max(0.3, min(0.90, rag_conf)), 2)

    # 3. Completeness score
    completeness = 0.88 if len(chunks) >= 2 else (0.70 if chunks else 0.25)

    # 4. Safety critic score derived from interaction severity
    if severity == "safe":
        safety_critic_score = 0.92
    elif severity == "caution":
        safety_critic_score = 0.68
    elif severity == "dangerous":
        safety_critic_score = 0.15
    else:
        safety_critic_score = 0.40

    inputs = ConfidenceInputs(
        retrieval_relevance=retrieval_relevance,
        completeness=completeness,
        safety_critic_score=safety_critic_score,
    )
    confidence = compute_confidence(inputs)
    flags_list = [state.get("red_flag_reason")] if red_flag else []
    risk = classify_risk(confidence, red_flags=flags_list, thresholds=RiskThresholds())

    grounded = len(chunks) > 0
    result = {
        "grounded": grounded,
        "confidence_score": confidence,
        "risk_level": risk.value,
    }
    return {
        **result,
        **log_step(
            state,
            "safety_critic",
            result,
            reason=f"grounded={grounded}, distance={closest_dist}, confidence={confidence}, risk={risk.value}"
        )
    }


# --- 7. Decision Router ---
def router(state: DoseCheckState) -> dict:
    is_red_flag = state.get("red_flag_triggered", False)
    risk_level = state.get("risk_level", "LOW")
    confidence = state.get("confidence_score") or 0.0
    is_dangerous = state.get("interaction_severity") == "dangerous"
    pop_warnings = state.get("vulnerable_population_warnings", [])

    # Router Safety Decision Invariant:
    # 1. IF red flag detected -> ESCALATE (911)
    # 2. ELSE IF vulnerable population detected -> ESCALATE (Specialist referral)
    # 3. ELSE IF high risk -> ESCALATE
    # 4. ELSE IF confidence < 0.70 -> ESCALATE
    # 5. ELSE -> ANSWER
    must_escalate = (
        is_red_flag
        or bool(pop_warnings)
        or risk_level == "HIGH"
        or is_dangerous
        or confidence < 0.70
        or not state.get("grounded", False)
    )

    case_id = None
    if must_escalate:
        route = "escalate"
        reason = (
            state.get("red_flag_reason")
            or (pop_warnings[0] if pop_warnings else None)
            or (f"Dangerous interaction: {state.get('interaction_explanation')}" if is_dangerous else None)
            or f"Risk: {risk_level}, Confidence: {confidence}"
        )
        rec = escalate_case(
            reason=reason,
            context={
                "question": state.get("user_question"),
                "current_medicines": state.get("current_medicines"),
                "new_medicine": state.get("new_medicine")
            }
        )
        case_id = rec.get("case_id")
    else:
        route = "safe_answer"

    state_with_route = {**state, "route": route}
    clinical_sum = synthesize_clinical_assessment(state_with_route)
    if case_id:
        clinical_sum["escalation_case_id"] = case_id

    final = format_clinical_markdown(clinical_sum)

    result = {
        "route": route,
        "final_answer": final,
        "clinical_summary": clinical_sum
    }
    return {**result, **log_step(state, "router", result, reason=f"route={route}")}


def red_flag_check(state: DoseCheckState) -> str:
    return "escalate_early" if state.get("red_flag_triggered") else "continue"


# --- Build the graph ---
graph = StateGraph(DoseCheckState)
graph.add_node("intake", intake_agent)
graph.add_node("red_flag", red_flag_agent)
graph.add_node("retrieval", retrieval_agent)
graph.add_node("interaction_tool", interaction_tool_node)
graph.add_node("response", response_agent)
graph.add_node("safety_critic", safety_critic)
graph.add_node("router", router)

graph.set_entry_point("intake")
graph.add_edge("intake", "red_flag")

graph.add_conditional_edges(
    "red_flag",
    red_flag_check,
    {"escalate_early": "router", "continue": "retrieval"},
)

graph.add_edge("retrieval", "interaction_tool")
graph.add_edge("interaction_tool", "response")
graph.add_edge("response", "safety_critic")
graph.add_edge("safety_critic", "router")
graph.add_edge("router", END)

app = graph.compile()


# --- End-to-end Verification Tests ---
if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("==================================================")
    print("DoseCheck AI: Running Agent Workflow Integration Tests")
    print("==================================================")

    # Test 1: Grounded Safe Answer
    print("\n--- Test 1: Grounded Safe Query (Paracetamol) ---")
    state_1 = {
        "current_medicines": ["amlodipine"],
        "new_medicine": "paracetamol",
        "user_question": "Can I take paracetamol for my headache? What is the maximum daily dose?",
        "trace_log": []
    }
    res_1 = app.invoke(state_1)
    print(f"Route: {res_1['route']}")
    print(f"Confidence: {res_1['confidence_score']}")
    print(f"Risk: {res_1['risk_level']}")
    print(f"Answer:\n{res_1['final_answer']}")

    # Test 2: Emergency Red Flag Trigger
    print("\n--- Test 2: Emergency Red Flag Trigger (Difficulty Breathing) ---")
    state_2 = {
        "current_medicines": ["amlodipine"],
        "new_medicine": "ibuprofen",
        "user_question": "After taking this pill, I have severe difficulty breathing and throat swelling.",
        "trace_log": []
    }
    res_2 = app.invoke(state_2)
    print(f"Route: {res_2['route']}")
    print(f"Red Flag: {res_2['red_flag_triggered']}")
    print(f"Answer:\n{res_2['final_answer']}")

    # Test 3: Low Confidence / Unknown Drug Escalation
    print("\n--- Test 3: Low Confidence / Unknown Drug Escalation ---")
    state_3 = {
        "current_medicines": ["amlodipine"],
        "new_medicine": "mystery_pill_xyz",
        "user_question": "Can I take mystery_pill_xyz with amlodipine?",
        "trace_log": []
    }
    res_3 = app.invoke(state_3)
    print(f"Route: {res_3['route']}")
    print(f"Confidence: {res_3['confidence_score']}")
    print(f"Risk: {res_3['risk_level']}")
    print(f"Answer:\n{res_3['final_answer']}")

    print("\n==================================================")
    print("All integration tests finished successfully!")
    print("==================================================")
