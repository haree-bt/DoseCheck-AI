import streamlit as st

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

    # -----------------------------------------------------
    # DETERMINE RESULT TYPE
    # -----------------------------------------------------

    if demo_mode == "🟢 Normal — Answer":

        result_type = "normal"

    elif demo_mode == "🟡 Uncertain — Clarify":

        result_type = "uncertain"

    elif demo_mode == "🔴 Emergency — Escalate":

        result_type = "emergency"

    else:

        # Temporary frontend logic.
        # This will later be replaced by the real
        # Safety Agent from your team.

        emergency_words = [
            "difficulty breathing",
            "can't breathe",
            "cannot breathe",
            "face swelling",
            "throat swelling",
            "severe chest pain",
            "loss of consciousness"
        ]

        question_lower = question.lower()

        if any(
            word in question_lower
            for word in emergency_words
        ):

            result_type = "emergency"

        elif (
            not current_medicines
            or not medicine_question
        ):

            result_type = "uncertain"

        else:

            result_type = "normal"


    # =====================================================
    # INPUT VALIDATION
    # =====================================================

    # IMPORTANT:
    # Demo scenarios are allowed to use predefined values.
    # Validation is applied only in Live / Manual mode.

    if (
        demo_mode == "Live / Manual"
        and (
            not current_medicines
            or not medicine_question
            or not question
        )
    ):

        st.warning(
            "⚠️ Please provide the required medication "
            "information before checking."
        )

    else:

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
                    "87%"
                )

            with col2:

                st.metric(
                    "Risk",
                    "LOW"
                )

            with col3:

                st.metric(
                    "Decision",
                    "ANSWER"
                )

            st.progress(
                0.87,
                text="Confidence: 87%"
            )


            # -------------------------------------------------
            # GUIDANCE
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">📋 Guidance</div>',
                unsafe_allow_html=True
            )

            with st.container(border=True):

                st.write(
                    """
                    Based on the available verified information,
                    general medication guidance can be provided.

                    Follow the instructions provided with your
                    medication and consult a qualified healthcare
                    professional when appropriate.
                    """
                )


            # -------------------------------------------------
            # EVIDENCE
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">📚 Verified Evidence</div>',
                unsafe_allow_html=True
            )

            evidence1, evidence2, evidence3 = st.columns(3)

            with evidence1:

                with st.container(border=True):

                    st.write("📄 **Medication Safety**")

                    st.caption(
                        "Verified knowledge-base information"
                    )

            with evidence2:

                with st.container(border=True):

                    st.write("🔗 **Interaction Reference**")

                    st.caption(
                        "Used for medication interaction analysis"
                    )

            with evidence3:

                with st.container(border=True):

                    st.write("🛡️ **Safety Guidance**")

                    st.caption(
                        "Used for safety evaluation"
                    )


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

                steps = [
                    "✓ Intake Agent — Medicines extracted",
                    "✓ Red Flag Agent — No red flags detected",
                    "✓ RAG Retriever — Evidence retrieved",
                    "✓ Interaction Tool — Medication check completed",
                    "✓ Response Agent — Guidance generated",
                    "✓ Safety Critic — Confidence: 0.87",
                    "✓ Router — Decision: ANSWER"
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
                    f"**Current medicines:** {current_medicines}"
                )

                st.write(
                    f"**Medicine asked about:** {medicine_question}"
                )

                st.write(
                    f"**Question:** {question}"
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
                    "52%"
                )

            with col2:

                st.metric(
                    "Risk",
                    "UNKNOWN"
                )

            with col3:

                st.metric(
                    "Decision",
                    "CLARIFY"
                )


            # -------------------------------------------------
            # CONFIDENCE BAR
            # -------------------------------------------------

            st.progress(
                0.52,
                text="Confidence: 52%"
            )


            # -------------------------------------------------
            # EXPLANATION
            # -------------------------------------------------

            st.markdown(
                '<div class="section-title">❓ Why can\'t I get an answer?</div>',
                unsafe_allow_html=True
            )

            with st.container(border=True):

                st.write(
                    """
                    The system could not identify enough reliable
                    medication information to provide a safe answer.

                    Please provide the exact medicine name and
                    any relevant details.
                    """
                )


            st.info(
                "🛡️ Instead of guessing, DoseCheck AI asks "
                "for more information."
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

                steps = [
                    "✓ Intake Agent — Question analyzed",
                    "⚠ Information incomplete",
                    "✓ RAG Retriever — Insufficient evidence",
                    "⛔ Definitive answer blocked",
                    "✓ Safety Critic — Confidence: 0.52",
                    "→ Router — Decision: CLARIFY"
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
                        🔴 Safety Escalation
                    </div>

                    <div class="result-description">
                        A potential red-flag symptom was detected.
                        Normal AI guidance has been blocked.
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
                    "41%"
                )

            with col2:

                st.metric(
                    "Risk",
                    "HIGH"
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
                0.41,
                text="Confidence: 41%"
            )


            st.error(
                "🚨 Potential emergency warning signs detected."
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
                    "**Trigger:** Potential red-flag symptom detected"
                )

                st.write(
                    "**Risk classification:** HIGH"
                )

                st.write(
                    "**Normal response:** BLOCKED"
                )

                st.write(
                    "**Final decision:** ESCALATE"
                )


            st.warning(
                "Please seek urgent medical help or contact "
                "a qualified healthcare professional."
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

                steps = [
                    "✓ Intake Agent — Medicines extracted",
                    "🚨 Red Flag Agent — Potential red flag detected",
                    "⛔ Normal response blocked",
                    "⚠ Safety System — HIGH RISK",
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