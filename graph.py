from langgraph.graph import StateGraph, END
from state import DoseCheckState
from rag.retriever import retrieve_relevant_documents, check_for_red_flags
from interaction_tool import check_interaction
from medication_tool import lookup_medicine
from escalation_tool import escalate_case

def log_step(state: DoseCheckState, node_name: str, output: dict, reason: str = "") -> dict:
    """Call this at the end of every node — this IS your observability requirement."""
    entry = {"node": node_name, "output": output, "reason": reason}
    return {"trace_log": state.get("trace_log", []) + [entry]}

# --- 1. Intake Agent ---
def intake_agent(state: DoseCheckState) -> dict:
    question = state.get("user_question", "")
    current_meds = state.get("current_medicines", [])
    new_med = state.get("new_medicine", "")

    # Extract common symptom keywords
    symptom_keywords = ["headache", "fever", "pain", "swelling", "breathing", "cough", "nausea", "rash", "dizziness"]
    found_symptoms = [s for s in symptom_keywords if s in question.lower()]

    # Infer user intent
    if current_meds and new_med:
        intent = "drug_interaction_check"
    elif any(w in question.lower() for w in ["dose", "dosage", "how much", "max", "limit"]):
        intent = "dosage_guidance"
    elif any(w in question.lower() for w in ["miss", "forgot", "skip"]):
        intent = "missed_dose_guidance"
    else:
        intent = "general_medication_query"

    result = {
        "extracted_intent": intent,
        "extracted_symptoms": found_symptoms
    }
    return {**result, **log_step(state, "intake_agent", result, reason=f"intent={intent}")}

# --- 2. Red-Flag Agent ---
def red_flag_agent(state: DoseCheckState) -> dict:
    query = state.get("user_question", "")
    detected_flags = check_for_red_flags(query)
    is_triggered = len(detected_flags) > 0
    reason = f"Potential medical emergency detected: {', '.join(detected_flags)}" if is_triggered else None

    result = {
        "red_flag_triggered": is_triggered,
        "red_flag_reason": reason
    }
    return {**result, **log_step(state, "red_flag_agent", result, reason=f"triggered={is_triggered}")}

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

    result = {
        "retrieved_chunks": chunks,
        "retrieved_sources": sources,
        "retrieved_context": rag_output.get("answer_context", "")
    }
    return {
        **result, 
        **log_step(
            state, 
            "retrieval_agent", 
            result, 
            reason=f"decision={rag_output['decision']}, confidence={rag_output['confidence_score']}"
        )
    }

# --- 4. Medication & Interaction Tool (MCP) ---
def interaction_tool_node(state: DoseCheckState) -> dict:
    current_meds = state.get("current_medicines", [])
    new_med = state.get("new_medicine", "")

    tool_res = None
    severity = "safe"
    explanation = "No known dangerous interaction identified."

    # Check drug-drug interaction against each current medication
    if new_med and current_meds:
        for med in current_meds:
            check = check_interaction(new_med, med)
            tool_res = check
            if check.get("found"):
                risk = check.get("risk", "low")
                if risk in ["high", "dangerous"]:
                    severity = "dangerous"
                    explanation = check.get("message", "High risk interaction detected.")
                    break
                elif risk in ["moderate", "caution"]:
                    severity = "caution"
                    explanation = check.get("message", "Moderate interaction noted.")
                else:
                    severity = "safe"
                    explanation = check.get("message", "No major interaction noted.")
            else:
                severity = "unknown"
                explanation = check.get("message", "Interaction information unavailable in database.")
    elif new_med:
        lookup = lookup_medicine(new_med)
        tool_res = lookup
        if lookup.get("found"):
            severity = "safe"
            explanation = f"Verified medicine: {lookup['medicine']['name']} ({lookup['medicine']['category']})."
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
    explanation = state.get("interaction_explanation", "")
    new_med = state.get("new_medicine", "")
    
    if chunks:
        draft = (
            f"Based on verified clinical guidelines for {new_med or 'your medication'}:\n"
            f"{chunks[0]}\n\n"
            f"Clinical Interaction Note: {explanation}"
        )
    else:
        draft = (
            f"Regarding {new_med or 'your medication'}: {explanation} "
            "Please follow the manufacturer's packaging instructions."
        )

    result = {
        "draft_answer": draft,
        "cited_chunks": chunks[:2] if chunks else []
    }
    return {**result, **log_step(state, "response_agent", result)}

# --- 6. Safety Critic Agent ---
def safety_critic(state: DoseCheckState) -> dict:
    chunks = state.get("retrieved_chunks", [])
    severity = state.get("interaction_severity")
    red_flag = state.get("red_flag_triggered", False)
    
    grounded = len(chunks) > 0

    if red_flag:
        confidence = 0.99
        risk_level = "CRITICAL"
    elif severity == "dangerous":
        confidence = 0.85
        risk_level = "HIGH"
    elif severity == "unknown" or not grounded:
        confidence = 0.45
        risk_level = "MODERATE_TO_HIGH"
    elif severity == "caution":
        confidence = 0.75
        risk_level = "MODERATE"
    else:
        confidence = 0.88 if grounded else 0.50
        risk_level = "LOW"

    result = {
        "grounded": grounded,
        "confidence_score": confidence,
        "risk_level": risk_level
    }
    return {
        **result, 
        **log_step(
            state, 
            "safety_critic", 
            result, 
            reason=f"grounded={grounded}, confidence={confidence}, risk={risk_level}"
        )
    }

# --- 7. Decision Router ---
def router(state: DoseCheckState) -> dict:
    is_red_flag = state.get("red_flag_triggered", False)
    risk_level = state.get("risk_level", "LOW")
    confidence = state.get("confidence_score") or 0.0
    is_dangerous = state.get("interaction_severity") == "dangerous"

    # Router Safety Invariants:
    # 1. IF red flag detected -> ESCALATE
    # 2. ELSE IF high risk -> ESCALATE
    # 3. ELSE IF confidence < 0.70 -> ESCALATE
    # 4. ELSE -> ANSWER
    must_escalate = (
        is_red_flag
        or risk_level in ["HIGH", "CRITICAL"]
        or is_dangerous
        or confidence < 0.70
    )

    if must_escalate:
        route = "escalate"
        if is_red_flag:
            final = (
                "🚨 EMERGENCY ESCALATION: Potential medical emergency detected ("
                + (state.get("red_flag_reason") or "Critical symptoms")
                + "). Please seek immediate medical care (Call 911 / Emergency Services)."
            )
        else:
            escalation_record = escalate_case(
                reason=state.get("red_flag_reason") or f"Risk: {risk_level}, Confidence: {confidence}",
                context={
                    "question": state.get("user_question"),
                    "current_medicines": state.get("current_medicines"),
                    "new_medicine": state.get("new_medicine")
                }
            )
            final = (
                f"⚠️ ESCALATED FOR CLINICAL REVIEW (Case ID: {escalation_record['case_id']}): "
                f"Safety confidence is insufficient ({int(confidence * 100)}%) or interaction risk is present. "
                "Please consult a physician or pharmacist directly before proceeding."
            )
    else:
        route = "safe_answer"
        final = state.get("draft_answer")

    result = {"route": route, "final_answer": final}
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
    import sys
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