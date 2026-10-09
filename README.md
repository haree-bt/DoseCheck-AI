# DoseCheck-AI 💊🛡️
> **Safety-First Multi-Agent AI System for Medication Guidance**  
> Powered by Grounded Medical RAG, Tool Verification, Confidence Scoring, and Risk-Based Escalation.

---

## 1. Problem Statement
General-purpose AI chatbots pose significant risks when answering medical questions. They can hallucinate dosages, fail to warn about fatal drug interactions, and attempt to "diagnose" patients instead of recognizing life-threatening emergencies. In healthcare, **knowing when NOT to answer is just as critical as answering.**

## 2. Solution: DoseCheck-AI
**DoseCheck-AI** is an Agentic AI system designed with a strict safety-first directive:
- **Authoritative Fact Grounding**: Every answer is grounded in verified medical guidelines (US FDA, NIH MedlinePlus, CDC, and UK NHS).
- **Zero Fabrication (Anti-Hallucination)**: If information is uncertain or outside the knowledge base, the system refuses to guess and flags for human clinician review.
- **Critical Red-Flag Escalation**: Emergency symptoms (anaphylaxis, chest pain, overdose) trigger an immediate safety override directing users to 911 / emergency services.
- **Transparent Citations**: Downstream agents and users receive direct source titles, authorities, and official URLs.

---

## 3. Overall System Architecture

```
                      [ User Query ]
                            │
                            ▼
                    [ Intake Agent ]
                            │
                            ▼
              [ Red Flag / Safety Check ] ──(Emergency Detected)──┐
                            │                                     │
                            ▼                                     │
                 [ RAG Retrieval Agent ]                          │
                            │                                     │
                            ▼                                     │
              [ Medication / Tool Checker ]                       │
                            │                                     │
                            ▼                                     │
                   [ Response Agent ]                             │
                            │                                     │
                            ▼                                     │
                    [ Safety Critic ]                             │
                            │                                     │
                            ▼                                     │
                 [ Confidence / Router ]                          │
                            │                                     │
              ┌─────────────┴─────────────┐                       │
              ▼                           ▼                       ▼
      [ High Confidence ]        [ Low Confidence /       [ CRITICAL RISK ]
      [  Safe Grounded  ]        [  Safety Concern ]              │
              │                           │                       │
              ▼                           ▼                       ▼
      ✅ Safe User Answer          ⚠️ Flag & Escalate      🚨 Immediate 911
      (with Citations)           (Clinician Advice)       (Emergency Override)
```

---

## 4. RAG Pipeline Architecture (Member 2 — RAG Engineer)

The RAG engine is built to be fast, reliable, and runnable on standard CPUs without massive cloud dependencies:

```
Authoritative Medical Documents (FDA, NIH, CDC, NHS)
                     │
                     ▼
  Document Parsing & Metadata Extraction (YAML Frontmatter)
                     │
                     ▼
  Text Normalization & Paragraph-Aware Overlapping Chunking (~450 chars, 80 overlap)
                     │
                     ▼
  Local Dense Embeddings (all-MiniLM-L6-v2 via ONNX runtime)
                     │
                     ▼
  ChromaDB Vector Database (rag/vectorstore/)
                     │
                     ▼
  Cosine Similarity Search & Distance Filtering
                     │
                     ▼
  Grounding Context + Confidence Scoring + Safety Routing (ANSWER / FLAG / ESCALATE)
```

---

## 5. Team Integration Interface

The RAG module exposes a clean, decoupled Python interface for teammate agents:

```python
from rag.retriever import retrieve_relevant_documents

# Call retriever
result = retrieve_relevant_documents("What is the maximum daily dose of acetaminophen?")
```

### Standardized Output Contract:
```json
{
  "query": "What is the maximum daily dose of acetaminophen?",
  "decision": "ANSWER",
  "risk_level": "LOW",
  "confidence_score": 0.8,
  "needs_escalation": false,
  "escalation_reason": null,
  "answer_context": "[Chunk 1] (Acetaminophen Safety... | Source: FDA)\n...",
  "sources": [
    {
      "title": "Acetaminophen Safety, Dosage Limits, and Toxicity Warnings",
      "source": "US Food and Drug Administration (FDA) & NIH MedlinePlus",
      "url": "https://www.fda.gov/drugs/safe-daily-intake-acetaminophen"
    }
  ],
  "disclaimer": "Hackathon safety and confidence score. Not medically validated."
}
```

---

## 6. Project Structure

```text
DoseCheck-AI/
│
├── README.md                 # Project documentation and architecture guide
├── requirements.txt          # Core dependencies (chromadb, langgraph, streamlit, fastmcp)
├── .gitignore                # Protects venv/ and vectorstore/ from git tracking
│
├── app.py                    # Streamlit web application & clinical dashboard (Member 4)
├── graph.py                  # LangGraph multi-agent orchestration workflow (Member 1)
├── state.py                  # Agent state schema with trace logs and metadata (Member 1)
├── safety_guardrail.py       # Red-flag detector, toxic dose & population guardrails (Member 4)
│
├── medication_tool.py        # Clinical drug catalog, brand aliases & entity lookup (Member 3)
├── interaction_tool.py       # Drug interaction engine & class-level risk rules (Member 3)
├── escalation_tool.py        # Clinician review & audit case generation (Member 3)
├── server.py                 # FastMCP server exposing tools via MCP protocol (Member 3)
│
├── rag/                      # Grounded RAG Engine (Member 2)
│   ├── __init__.py           # Package marker
│   ├── ingest.py             # Word-aligned chunker and ChromaDB indexer
│   ├── retriever.py          # Similarity search, confidence scoring & safety router
│   ├── documents/            # Authoritative medical knowledge base (FDA, NHS, CDC, AAP)
│   │   ├── dosage/           # Missed dose guidance
│   │   ├── medication_safety/# Acetaminophen, Ibuprofen, Anticoagulants, Cardiovascular, Pediatrics, Pregnancy
│   │   └── red_flags/        # Emergency anaphylaxis, stroke & hemorrhage protocols
│   └── vectorstore/          # Local persistent ChromaDB storage (auto-generated)
│
└── evaluation/               # Verification & Automated Testing Suite
    ├── test_cases.json       # Gold RAG grounding & rejection benchmark cases
    ├── agent_test_cases.json # Multi-agent workflow test cases (overdose, pediatrics, pregnancy, interactions)
    └── evaluate.py           # Comprehensive automated evaluation runner (100% test accuracy)
```

---

## 7. Installation and Setup

### Prerequisites
- Windows 10/11
- Python 3.11, 3.12, 3.13, or 3.14

### 1. Clone the Repository
```powershell
git clone https://github.com/haree-bt/DoseCheck-AI.git .
```

### 2. Set Up Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 8. How to Run

### Step 1: Ingest Medical Knowledge into ChromaDB
```powershell
python rag/ingest.py
```

### Step 2: Run the Automated Evaluation Suite
```powershell
python evaluation/evaluate.py
```

### Step 3: Launch the Clinical Streamlit Web App
```powershell
streamlit run app.py
```

---

## 9. Evaluation Results
The system is evaluated against **13 automated test cases** across two verification batteries:

### Part 1: RAG Grounding & Rejection (5 Cases)
1. **Dosage Limits**: `PASS` (Answered with FDA citations)
2. **Missed Doses**: `PASS` (Answered with NHS double-dose warnings)
3. **Drug Interactions**: `PASS` (Answered with NSAID / blood thinner warning)
4. **Out-of-Domain**: `PASS` (Safely blocked fabrication, flagged for clinician review)
5. **Emergency Red Flag**: `PASS` (Critical risk detected, escalated to 911)

### Part 2: Multi-Agent Safety Workflow (8 Cases)
1. **Grounded Safe Guidance**: `PASS` (Paracetamol adult dosage answered safely)
2. **Missed Dose Protocol**: `PASS` (Never double up missed pills)
3. **Acute Overdose / Toxic Ingestion**: `PASS` (10,000 mg paracetamol triggers emergency override)
4. **Pediatric Contraindication**: `PASS` (Adult guidelines blocked for 2-year-old child; pediatrician referral)
5. **Pregnancy Black-Box Warnings**: `PASS` (Third-trimester NSAID ductus arteriosus risk flagged)
6. **Dangerous Drug Interaction**: `PASS` (Ibuprofen + Anticoagulant bleeding hazard detected and blocked)
7. **Emergency Chest Pain**: `PASS` (Immediate 911 escalation)
8. **Emergency Internal Bleeding**: `PASS` (GI hemorrhage red flag escalated to 911)

**Overall Score**: **13/13 Passed (100.0% Accuracy)**.

---

## 10. Team Members
- **Member 1**: Agents & Orchestration
- **Member 2**: RAG Engineer (Document Ingestion, Embeddings, ChromaDB, Retriever & Safety Routing)
- **Member 3**: Tools / MCP Integration
- **Member 4**: Safety Guardrails & Frontend / UI
