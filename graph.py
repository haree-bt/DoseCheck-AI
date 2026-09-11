from langgraph.graph import StateGraph, END
from state import DoseCheckState
from rag.retriever import retrieve_relevant_documents

def log_step(state: DoseCheckState, node_name: str, output: dict, reason: str = "") -> dict:
    """Call this at the end of every node — this IS your observability requirement."""
    entry = {"node": node_name, "output": output, "reason": reason}
    return {"trace_log": state.get("trace_log", []) + [entry]}

# --- Stub nodes (replace with teammates' real implementations later) ---

def intake_agent(state: DoseCheckState) -> dict:
    result = {"extracted_intent": "interaction_check", "extracted_symptoms": []}
    return {**result, **log_step(state, "intake_agent", result)}

def red_flag_agent(state: DoseCheckState) -> dict:
    result = {"red_flag_triggered": False, "red_flag_reason": None}
    return {**result, **log_step(state, "red_flag_agent", result)}

def retrieval_agent(state: DoseCheckState) -> dict:
    rag_output = retrieve_relevant_documents(state.get("user_question", ""))
    chunks = [c["text"] for c in rag_output.get("top_chunks", [])]
    sources = [s["title"] for s in rag_output.get("sources", [])]
    
    result = {
        "retrieved_chunks": chunks,
        "retrieved_sources": sources
    }
    return {
        **result, 
        **log_step(state, "retrieval_agent", result, reason=f"decision={rag_output['decision']}, confidence={rag_output['confidence_score']}")
    }

def interaction_tool_node(state: DoseCheckState) -> dict:
    result = {"interaction_severity": "safe", "interaction_explanation": "stub: no known interaction"}
    return {**result, **log_step(state, "interaction_tool", result)}

def response_agent(state: DoseCheckState) -> dict:
    result = {"draft_answer": "Based on available info, this combination looks safe.",
              "cited_chunks": state.get("retrieved_chunks", [])}
    return {**result, **log_step(state, "response_agent", result)}

def safety_critic(state: DoseCheckState) -> dict:
    grounded = len(state.get("cited_chunks", [])) > 0
    confidence = 0.8 if grounded else 0.3
    result = {"grounded": grounded, "confidence_score": confidence, "risk_level": "low"}
    return {**result, **log_step(state, "safety_critic", result,
                                  reason=f"grounded={grounded}, confidence={confidence}")}

def router(state: DoseCheckState) -> dict:
    escalate = (
        state.get("red_flag_triggered", False)
        or not state.get("grounded", False)
        or (state.get("confidence_score") or 0) < 0.7
        or state.get("interaction_severity") == "dangerous"
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
    initial_state = {
        "current_medicines": ["metformin"],
        "new_medicine": "paracetamol",
        "user_question": "Can I take paracetamol with metformin?",
        "extracted_intent": None,
        "extracted_symptoms": [],
        "red_flag_triggered": True,
        "red_flag_reason": "chest pain and difficulty breathing reported",
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

    result = app.invoke(initial_state)

    print("\n=== FINAL ANSWER ===")
    print(result["final_answer"])

    print("\n=== TRACE LOG ===")
    for step in result["trace_log"]:
        print(step)