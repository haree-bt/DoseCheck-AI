from safety_guardrail import detect_red_flags, ConfidenceInputs, compute_confidence, classify_risk, RiskThresholds
from langgraph.graph import StateGraph, END
from state import DoseCheckState
from fastmcp import Client
def log_step(state: DoseCheckState, node_name: str, output: dict, reason: str = "") -> dict:
    """Call this at the end of every node — this IS your observability requirement."""
    entry = {"node": node_name, "output": output, "reason": reason}
    return {"trace_log": state.get("trace_log", []) + [entry]}

# --- Stub nodes (replace with teammates' real implementations later) ---

def intake_agent(state: DoseCheckState) -> dict:
    result = {"extracted_intent": "interaction_check", "extracted_symptoms": []}
    return {**result, **log_step(state, "intake_agent", result)}

def red_flag_agent(state: DoseCheckState) -> dict:
    text_to_check = state["user_question"] + " " + " ".join(state.get("extracted_symptoms", []))
    red_flags = detect_red_flags(text_to_check)
    triggered = len(red_flags) > 0
    reason = f"Detected: {', '.join(red_flags)}" if triggered else None
    result = {"red_flag_triggered": triggered, "red_flag_reason": reason}
    return {**result, **log_step(state, "red_flag_agent", result)}

def retrieval_agent(state: DoseCheckState) -> dict:
    result = {"retrieved_chunks": ["stub chunk about paracetamol"], "retrieved_sources": ["stub_source"]}
    return {**result, **log_step(state, "retrieval_agent", result)}

RISK_TO_SEVERITY = {
    "low": "safe",
    "moderate": "caution",
    "high": "dangerous",
    "unknown": "unknown",
}

async def interaction_tool_node(state: DoseCheckState) -> dict:
    from pathlib import Path
    async with Client(Path("server.py")) as client:
        tool_result = await client.call_tool(
            "medication_interaction_check",
            {"drug_a": state["current_medicines"][0], "drug_b": state["new_medicine"]}
        )
        severity = RISK_TO_SEVERITY.get(tool_result.data.get("risk", "unknown"), "unknown")
    result = {
        "interaction_severity": severity,
        "interaction_explanation": tool_result.data.get("message", ""),
    }
    return {**result, **log_step(state, "interaction_tool", result)}

def response_agent(state: DoseCheckState) -> dict:
    severity = state.get("interaction_severity", "unknown")
    explanation = state.get("interaction_explanation", "")
    if severity == "safe":
        draft = "Based on available info, this combination looks safe."
    else:
        draft = f"Caution: {explanation}"
    result = {"draft_answer": draft, "cited_chunks": state.get("retrieved_chunks", [])}
    return {**result, **log_step(state, "response_agent", result)}

def safety_critic(state: DoseCheckState) -> dict:
    retrieval_relevance = 0.9 if state.get("retrieved_chunks") else 0.3
    completeness = 1.0 if state.get("cited_chunks") else 0.4
    safety_critic_score = 0.9 if state.get("grounded_hint", True) else 0.4  # placeholder until a real critic model exists

    inputs = ConfidenceInputs(
        retrieval_relevance=retrieval_relevance,
        completeness=completeness,
        safety_critic_score=safety_critic_score,
    )
    confidence = compute_confidence(inputs)
    risk = classify_risk(confidence, red_flags=[], thresholds=RiskThresholds())

    grounded = len(state.get("cited_chunks", [])) > 0
    result = {
        "grounded": grounded,
        "confidence_score": confidence,
        "risk_level": risk.value,
    }
    return {**result, **log_step(state, "safety_critic", result,
                                  reason=f"grounded={grounded}, confidence={confidence}, risk={risk.value}")}

def router(state: DoseCheckState) -> dict:
    escalate = (
        state.get("red_flag_triggered", False)
        or not state.get("grounded", False)
        or state.get("risk_level") == "HIGH"
        or state.get("interaction_severity") in ("caution", "dangerous")
    )
    route = "escalate" if escalate else "safe_answer"
    final = (
        "⚠️ Please consult a doctor or pharmacist directly — here's why: "
        + (state.get("red_flag_reason") or "confidence too low / insufficient verified data")
        if escalate else state.get("draft_answer")
    )
    result = {"route": route, "final_answer": final}
    return {**result, **log_step(state, "router", result, reason=f"escalate={escalate}")}

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

# --- Test run (so you can see it actually working) ---

if __name__ == "__main__":
    import asyncio

    async def main():
        initial_state = {
            "current_medicines": ["amlodipine"],
            "new_medicine": "ibuprofen",
            "user_question": "Can I take ibuprofen with my amlodipine?",
            "extracted_intent": None,
            "extracted_symptoms": [],
            "red_flag_triggered": False,
            "red_flag_reason": None,
            "retrieved_chunks": [],
            "retrieved_sources": [],
            "interaction_severity": None,
            "interaction_explanation": None,
            "draft_answer": None,
            "cited_chunks": [],
            "confidence_score": None,
            "grounded": None,
            "risk_level": None,
            "route": None,
            "final_answer": None,
            "trace_log": [],
        }
        result = await app.ainvoke(initial_state)
        print("\n=== FINAL ANSWER ===")
        print(result["final_answer"])
        print("\n=== TRACE LOG ===")
        for step in result["trace_log"]:
            print(step)

    asyncio.run(main())