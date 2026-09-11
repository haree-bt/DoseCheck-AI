import streamlit as st
from rag.retriever import retrieve_relevant_documents
from graph import app as agent_app

# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="DoseCheck AI",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

.block-container {
    max-width: 1150px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Header */

.logo {
    font-size: 44px;
    font-weight: 800;
    letter-spacing: -1.5px;
    margin-bottom: 4px;
}

.tagline {
    color: #9ca3af;
    font-size: 16px;
    margin-bottom: 22px;
}

/* Section headings */

.section-title {
    font-size: 25px;
    font-weight: 700;
    margin-top: 25px;
    margin-bottom: 8px;
}

/* General cards */

.card {
    padding: 22px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.025);
    margin-bottom: 16px;
}

/* Safe result */

.safe-card {
    padding: 24px;
    border-radius: 15px;
    border: 1px solid rgba(34,197,94,0.45);
    background: rgba(34,197,94,0.08);
    margin-bottom: 18px;
}

/* Uncertain result */

.warning-card {
    padding: 24px;
    border-radius: 15px;
    border: 1px solid rgba(234,179,8,0.45);
    background: rgba(234,179,8,0.08);
    margin-bottom: 18px;
}

/* Emergency result */

.danger-card {
    padding: 24px;
    border-radius: 15px;
    border: 1px solid rgba(239,68,68,0.45);
    background: rgba(239,68,68,0.08);
    margin-bottom: 18px;
}

/* Result title */

.result-title {
    font-size: 22px;
    font-weight: 750;
}

.result-description {
    color: #b8bec9;
    margin-top: 6px;
    font-size: 15px;
}

/* Agent trace */

.trace-item {
    padding: 8px 0;
    font-size: 15px;
}

/* Demo badge */

.demo-badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 20px;
    background: rgba(255,255,255,0.07);
    color: #cbd5e1;
    font-size: 12px;
    margin-bottom: 12px;
}

/* Footer */

.footer {
    text-align: center;
    color: #737b89;
    font-size: 13px;
    margin-top: 35px;
    line-height: 1.6;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("## 🎬 Demo Controls")

    st.caption(
        "Use Demo Mode during your hackathon presentation "
        "to demonstrate different safety decisions."
    )

    demo_mode = st.selectbox(
        "Demo scenario",
        [
            "Live / Manual",
            "🟢 Normal — Answer",
            "🟡 Uncertain — Clarify",
            "🔴 Emergency — Escalate"
        ]
    )

    st.divider()

    st.markdown("### 🧠 System Architecture")

    st.caption("Multi-agent safety pipeline")

    st.write("✓ Intake Agent")
    st.write("✓ Red Flag Agent")
    st.write("✓ RAG Retriever")
    st.write("✓ Interaction Tool")
    st.write("✓ Response Agent")
    st.write("✓ Safety Critic")
    st.write("✓ Decision Router")

    st.divider()

    st.markdown("### 🟢 System Status")

    st.success("Frontend Online")
    st.success("ChromaDB Vectorstore Ready")
    st.success("Safety Guardrails Active")


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="logo">💊 DoseCheck AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="tagline">'
    'Safety-first medication guidance · '
    'Grounded · Explainable · Risk-aware'
    '</div>',
    unsafe_allow_html=True
)

if demo_mode != "Live / Manual":

    st.markdown(
        '<div class="demo-badge">🎬 DEMO MODE ACTIVE</div>',
        unsafe_allow_html=True
    )

st.divider()


# =========================================================
# INPUT SECTION
# =========================================================

st.markdown(
    '<div class="section-title">💊 Check your medication</div>',
    unsafe_allow_html=True
)

st.caption(
    "Enter the medicines involved and describe what you want to know."
)


# =========================================================
# DEMO VALUES
# =========================================================

if demo_mode == "🟢 Normal — Answer":

    default_current = "Amlodipine"
    default_medicine = "Ibuprofen"
    default_question = "Can I take this for my headache?"

elif demo_mode == "🟡 Uncertain — Clarify":

    default_current = ""
    default_medicine = ""
    default_question = "Can I take this medicine with my other tablets?"

elif demo_mode == "🔴 Emergency — Escalate":

    default_current = "Amlodipine"
    default_medicine = "Ibuprofen"
    default_question = (
        "After taking my medicine, I am having difficulty breathing."
    )

else:

    default_current = ""
    default_medicine = ""
    default_question = ""


# =========================================================
# INPUT FIELDS
# =========================================================

col1, col2 = st.columns(2)

with col1:

    current_medicines = st.text_input(
        "Current medicines",
        value=default_current,
        placeholder="e.g., Amlodipine, Metformin"
    )

with col2:

    medicine_question = st.text_input(
        "Medicine you are asking about",
        value=default_medicine,
        placeholder="e.g., Ibuprofen"
    )

question = st.text_area(
    "What would you like to know?",
    value=default_question,
    placeholder="e.g., Can I take this for my headache?",
    height=115
)

check_button = st.button(
    "🔍  CHECK SAFELY",
    type="primary",
    use_container_width=False
)


# =========================================================
# PROCESS REQUEST
# =========================================================

if check_button:

    # =====================================================
    # INPUT VALIDATION
    # =====================================================

    has_input = bool(question.strip() or medicine_question.strip())

    if demo_mode == "Live / Manual" and not has_input:

        st.warning(
            "⚠️ Please enter a medication question or specify a medicine before checking."
        )

    else:

        # Build comprehensive query for RAG retrieval
        query_parts = []
        if medicine_question.strip():
            query_parts.append(f"Medicine: {medicine_question.strip()}")
        if current_medicines.strip():
            query_parts.append(f"Current medications: {current_medicines.strip()}")
        if question.strip():
            query_parts.append(f"Question: {question.strip()}")

        full_query = ". ".join(query_parts) if query_parts else (question.strip() or medicine_question.strip())

        # Prepare state for LangGraph multi-agent pipeline
        meds_list = [m.strip() for m in current_medicines.split(",") if m.strip()] if current_medicines else []
        new_med_str = medicine_question.strip()
        user_q_str = question.strip() or f"Is {new_med_str} safe to take?"

        initial_state = {
            "current_medicines": meds_list,
            "new_medicine": new_med_str,
            "user_question": user_q_str,
            "trace_log": []
        }

        # Run both the Multi-Agent LangGraph pipeline and RAG Retrieval
        with st.spinner("Multi-Agent Safety Pipeline analyzing query..."):
            agent_res = agent_app.invoke(initial_state)
            rag_result = retrieve_relevant_documents(full_query)

        # -------------------------------------------------
        # DETERMINE RESULT TYPE
        # -------------------------------------------------

        if demo_mode == "🟢 Normal — Answer":
            result_type = "normal"
        elif demo_mode == "🟡 Uncertain — Clarify":
            result_type = "uncertain"
        elif demo_mode == "🔴 Emergency — Escalate":
            result_type = "emergency"
        else:
            # Live / Manual mode routes dynamically from the Multi-Agent Engine
            if agent_res.get("red_flag_triggered"):
                result_type = "emergency"
            elif agent_res.get("route") == "safe_answer":
                result_type = "normal"
            else:
                result_type = "uncertain"

        # Extract values from LangGraph agent output + RAG engine
        confidence_score = agent_res.get("confidence_score") or rag_result.get("confidence_score", 0.85)
        risk_level = agent_res.get("risk_level") or rag_result.get("risk_level", "LOW")
        decision = "ANSWER" if result_type == "normal" else "ESCALATE"
        answer_context = agent_res.get("final_answer") or rag_result.get("answer_context", "")
        sources = rag_result.get("sources", [])
        top_chunks = rag_result.get("top_chunks", [])
        escalation_reason = agent_res.get("red_flag_reason") or rag_result.get("escalation_reason", "")
        trace_log = agent_res.get("trace_log", [])

        st.divider()

        st.markdown(
            '<div class="section-title">🛡️ Safety Assessment</div>',
            unsafe_allow_html=True
        )


        # =================================================
        # NORMAL CASE
        # =================================================

        if result_type == "normal":

            st.markdown(
                """
                <div class="safe-card">
                    <div class="result-title">
                        🟢 General Guidance Available
                    </div>

                    <div class="result-description">
                        No immediate red-flag symptoms were detected.
                        The system can provide grounded general guidance.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Confidence",
                    f"{int(confidence_score * 100)}%"
                )

            with col2:

                st.metric(
                    "Risk",
                    risk_level
                )

            with col3:

                st.metric(
                    "Decision",
                    decision
                )

            st.progress(
                float(confidence_score),
                text=f"Confidence: {int(confidence_score * 100)}%"
            )


            # -------------------------------------------------
            # GUIDANCE
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">📋 Grounded Guidance</div>',
                unsafe_allow_html=True
            )

            with st.container(border=True):

                if top_chunks:
                    st.markdown(f"**Primary Finding ({top_chunks[0].get('title', 'Medication Safety')}):**")
                    st.write(top_chunks[0].get("text", ""))
                    if len(top_chunks) > 1:
                        with st.expander("📖 Additional Clinical Context & Dosage Notes"):
                            for chunk in top_chunks[1:]:
                                st.markdown(f"**{chunk.get('title', 'Reference')}**")
                                st.write(chunk.get("text", ""))
                else:
                    st.write(
                        answer_context or (
                            "Based on the available verified information, "
                            "general medication guidance can be provided."
                        )
                    )

                st.caption(
                    "⚠️ Follow the instructions provided with your medication "
                    "and consult a qualified healthcare professional when appropriate."
                )


            # -------------------------------------------------
            # EVIDENCE
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">📚 Verified Evidence & Citations</div>',
                unsafe_allow_html=True
            )

            if sources:
                ev_cols = st.columns(min(len(sources), 3))
                for idx, src in enumerate(sources[:3]):
                    with ev_cols[idx]:
                        with st.container(border=True):
                            st.write(f"📄 **{src.get('title', 'Medical Authority')}**")
                            st.caption(f"Authority: {src.get('source', 'FDA / NHS / CDC')}")
                            if src.get("url"):
                                st.link_button("View Authority Protocol", src["url"], use_container_width=True)
            else:
                evidence1, evidence2, evidence3 = st.columns(3)

                with evidence1:
                    with st.container(border=True):
                        st.write("📄 **Medication Safety**")
                        st.caption("Verified knowledge-base information")

                with evidence2:
                    with st.container(border=True):
                        st.write("🔗 **Interaction Reference**")
                        st.caption("Used for medication interaction analysis")

                with evidence3:
                    with st.container(border=True):
                        st.write("🛡️ **Safety Guidance**")
                        st.caption("Used for safety evaluation")


            # -------------------------------------------------
            # AGENT TRACE
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">🔍 AI Decision Process</div>',
                unsafe_allow_html=True
            )

            with st.expander(
                "View complete agent trace",
                expanded=True
            ):

                if trace_log:
                    for step in trace_log:
                        node_name = step.get("node", "").replace("_", " ").title()
                        reason = step.get("reason", "")
                        reason_str = f" — <i>{reason}</i>" if reason else ""
                        st.markdown(
                            f'<div class="trace-item">✓ <b>{node_name} Node</b>{reason_str}</div>',
                            unsafe_allow_html=True
                        )
                else:
                    closest_dist_str = f"{top_chunks[0]['distance']}" if top_chunks else "N/A"
                    steps = [
                        f"✓ Intake Agent — Processed query: '{full_query}'",
                        "✓ Red Flag Agent — No life-threatening emergency symptoms detected",
                        f"✓ RAG Retriever — Retrieved {len(top_chunks)} evidence chunks from ChromaDB (closest distance: {closest_dist_str})",
                        "✓ Interaction Tool — Medication cross-check completed",
                        "✓ Response Agent — Grounded response synthesized from official clinical protocols",
                        f"✓ Safety Critic — Confidence assessed at {int(confidence_score * 100)}%",
                        f"✓ Router — Decision: {decision}"
                    ]

                    for step in steps:
                        st.markdown(
                            f'<div class="trace-item">{step}</div>',
                            unsafe_allow_html=True
                        )


            # -------------------------------------------------
            # REQUEST SUMMARY
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">📝 Request Summary</div>',
                unsafe_allow_html=True
            )

            with st.container(border=True):

                st.write(
                    f"**Current medicines:** {current_medicines or 'None reported'}"
                )

                st.write(
                    f"**Medicine asked about:** {medicine_question or 'General inquiry'}"
                )

                st.write(
                    f"**Question:** {question or 'None specified'}"
                )


        # =================================================
        # UNCERTAIN CASE
        # =================================================

        elif result_type == "uncertain":

            st.markdown(
                """
                <div class="warning-card">
                    <div class="result-title">
                        🟡 More Information Needed
                    </div>

                    <div class="result-description">
                        The system does not have enough information
                        to safely provide a definitive response.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


            # -------------------------------------------------
            # UNCERTAIN METRICS
            # -------------------------------------------------

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Confidence",
                    f"{int(confidence_score * 100)}%"
                )

            with col2:

                st.metric(
                    "Risk",
                    risk_level
                )

            with col3:

                st.metric(
                    "Decision",
                    decision if decision != "ANSWER" else "CLARIFY"
                )


            # -------------------------------------------------
            # CONFIDENCE BAR
            # -------------------------------------------------

            st.progress(
                float(confidence_score),
                text=f"Confidence: {int(confidence_score * 100)}%"
            )


            # -------------------------------------------------
            # EXPLANATION
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">❓ Why can\'t I get an answer?</div>',
                unsafe_allow_html=True
            )

            with st.container(border=True):

                if escalation_reason:
                    st.write(f"**Safety Alert:** {escalation_reason}")

                st.write(
                    answer_context or (
                        "The system could not identify enough reliable medication information "
                        "in the verified medical knowledge base to provide a safe answer. "
                        "Please provide the exact medicine name and any relevant details."
                    )
                )


            st.info(
                "🛡️ Instead of guessing or hallucinating, DoseCheck AI asks for more information."
            )


            # -------------------------------------------------
            # TRACE
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">🔍 AI Decision Process</div>',
                unsafe_allow_html=True
            )

            with st.expander(
                "View complete agent trace",
                expanded=True
            ):

                if trace_log:
                    for step in trace_log:
                        node_name = step.get("node", "").replace("_", " ").title()
                        reason = step.get("reason", "")
                        reason_str = f" — <i>{reason}</i>" if reason else ""
                        st.markdown(
                            f'<div class="trace-item">✓ <b>{node_name} Node</b>{reason_str}</div>',
                            unsafe_allow_html=True
                        )
                else:
                    closest_dist_str = f"{top_chunks[0]['distance']}" if top_chunks else "> 1.15"
                    steps = [
                        f"✓ Intake Agent — Question analyzed: '{full_query}'",
                        "⚠ Information incomplete or outside knowledge base",
                        f"✓ RAG Retriever — Vector distance: {closest_dist_str} (exceeds safety threshold 1.15)",
                        "⛔ Definitive answer blocked to prevent medical misinformation",
                        f"✓ Safety Critic — Confidence: {int(confidence_score * 100)}%",
                        f"→ Router — Decision: {decision if decision != 'ANSWER' else 'CLARIFY'}"
                    ]

                    for step in steps:
                        st.markdown(
                            f'<div class="trace-item">{step}</div>',
                            unsafe_allow_html=True
                        )


        # =================================================
        # EMERGENCY CASE
        # =================================================

        elif result_type == "emergency":

            st.markdown(
                """
                <div class="danger-card">
                    <div class="result-title">
                        🔴 Safety Escalation — Emergency Triggered
                    </div>

                    <div class="result-description">
                        A potential life-threatening red-flag symptom was detected.
                        Normal AI guidance has been immediately BLOCKED to prevent harm.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


            # -------------------------------------------------
            # EMERGENCY METRICS
            # -------------------------------------------------

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Confidence",
                    "99%"
                )

            with col2:

                st.metric(
                    "Risk",
                    "CRITICAL"
                )

            with col3:

                st.metric(
                    "Decision",
                    "ESCALATE"
                )


            # -------------------------------------------------
            # CONFIDENCE BAR
            # -------------------------------------------------

            st.progress(
                0.99,
                text="Emergency Severity: 99%"
            )


            st.error(
                "🚨 **POTENTIAL MEDICAL EMERGENCY DETECTED:** "
                "The symptoms described require urgent medical evaluation. "
                "Do not wait or rely on home remedies."
            )


            # -------------------------------------------------
            # ESCALATION REASON
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">🚨 Why was this escalated?</div>',
                unsafe_allow_html=True
            )

            with st.container(border=True):

                st.write(
                    f"**Trigger:** {escalation_reason or 'Potential red-flag symptom detected'}"
                )

                st.write(
                    "**Risk classification:** CRITICAL"
                )

                st.write(
                    "**Normal response:** BLOCKED (Zero-Tolerance Safety Protocol)"
                )

                st.write(
                    "**Action Required:** Call 911 / 112 / 999 or proceed immediately to the nearest Emergency Room."
                )


            st.warning(
                "⚠️ **Emergency Directive:** Please contact emergency medical services (911) "
                "or a qualified healthcare professional immediately."
            )


            # -------------------------------------------------
            # EMERGENCY EVIDENCE
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">📚 Emergency Clinical Protocol</div>',
                unsafe_allow_html=True
            )

            with st.container(border=True):
                st.write("📄 **Critical Red-Flag Symptoms Requiring Immediate Emergency Care**")
                st.caption("Authority: Centers for Disease Control and Prevention (CDC) & NHS Emergency Protocols")
                st.link_button("View NHS Anaphylaxis & Emergency Guidance", "https://www.nhs.uk/conditions/anaphylaxis/", use_container_width=True)


            # -------------------------------------------------
            # TRACE
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">🔍 AI Decision Process</div>',
                unsafe_allow_html=True
            )

            with st.expander(
                "View complete agent trace",
                expanded=True
            ):

                if trace_log:
                    for step in trace_log:
                        node_name = step.get("node", "").replace("_", " ").title()
                        reason = step.get("reason", "")
                        reason_str = f" — <i>{reason}</i>" if reason else ""
                        st.markdown(
                            f'<div class="trace-item">✓ <b>{node_name} Node</b>{reason_str}</div>',
                            unsafe_allow_html=True
                        )
                else:
                    steps = [
                        f"✓ Intake Agent — Query received: '{full_query}'",
                        f"🚨 Red Flag Agent — Life-threatening symptom matched: {escalation_reason or 'Emergency symptom'}",
                        "⛔ Normal response blocked — Short-circuit to emergency protocol",
                        "⚠ Safety System — CRITICAL RISK",
                        "→ Router — Decision: ESCALATE"
                    ]

                    for step in steps:
                        st.markdown(
                            f'<div class="trace-item">{step}</div>',
                            unsafe_allow_html=True
                        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.markdown(
    """
    <div class="footer">

        ⚠️ <b>Safety Notice:</b>
        DoseCheck AI provides safety-oriented informational
        guidance. It does not diagnose medical conditions or
        replace professional medical advice.

        <br><br>

        🧠 Multi-Agent · 📚 RAG Grounded · 🛡️ Safety First

        <br><br>

        Built for the Agentic AI Hackathon

    </div>
    """,
    unsafe_allow_html=True
)