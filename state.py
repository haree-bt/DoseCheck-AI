from typing import TypedDict, Optional, Literal

class DoseCheckState(TypedDict):
    # raw input
    current_medicines: list[str]
    new_medicine: str
    user_question: str

    # Intake Agent output
    extracted_intent: Optional[str]
    extracted_symptoms: list[str]

    # Red-Flag Agent output
    red_flag_triggered: bool
    red_flag_reason: Optional[str]

    # Retrieval Agent output
    retrieved_chunks: list[str]
    retrieved_sources: list[str]
    retrieved_context: Optional[str]

    # Interaction Tool (MCP) output
    tool_result: Optional[dict]
    interaction_severity: Optional[Literal["safe", "caution", "dangerous", "unknown"]]
    interaction_explanation: Optional[str]

    # Response Agent output
    draft_answer: Optional[str]
    cited_chunks: list[str]

    # Safety Critic output
    confidence_score: Optional[float]
    grounded: Optional[bool]
    risk_level: Optional[str]

    # Router output
    route: Optional[Literal["safe_answer", "escalate"]]
    final_answer: Optional[str]

    # Observability
    trace_log: list[dict]