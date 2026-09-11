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
├── requirements.txt          # Minimal, reliable dependencies (chromadb)
├── .gitignore                # Protects venv/ and vectorstore/ from git tracking
│
├── rag/                      # RAG Engine (Member 2 Responsibility)
│   ├── __init__.py           # Package marker
│   ├── ingest.py             # Document loading, chunking, and ChromaDB indexing
│   ├── retriever.py          # Similarity search, confidence scoring & safety router
│   ├── documents/            # Authoritative medical knowledge base
│   │   ├── dosage/           # Missed dose guidance (NHS & NIH)
│   │   ├── medication_safety/# Acetaminophen & Ibuprofen safety guidelines (FDA & NIH)
│   │   └── red_flags/        # Emergency anaphylaxis / critical symptoms (CDC & NHS)
│   └── vectorstore/          # Local ChromaDB persistent storage (auto-generated)
│
└── evaluation/               # Evaluation & Safety Verification
    ├── test_cases.json       # 5 Gold test cases covering all 3 safety scenarios
    └── evaluate.py           # Automated evaluation runner (100% test accuracy)
```

---

## 7. Installation and Setup

### Prerequisites
- Windows 10/11
- Python 3.11, 3.12, 3.13, or 3.14

### 1. Clone the Repository
```powershell
git clone <REPO_URL> .
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

### Step 2: Test Retrieval & Confidence Scoring
```powershell
python rag/retriever.py
```

### Step 3: Run the Automated Evaluation Suite
```powershell
python evaluation/evaluate.py
```

---

## 9. Evaluation Results
The system is evaluated against 5 gold test cases covering:
1. **Dosage Limits**: `PASS` (Answered with FDA citations)
2. **Missed Doses**: `PASS` (Answered with NHS double-dose warnings)
3. **Drug Interactions**: `PASS` (Answered with NSAID / blood thinner warning)
4. **Out-of-Domain**: `PASS` (Safely blocked fabrication, flagged for clinician review)
5. **Emergency Red Flag**: `PASS` (Critical risk detected, escalated to 911)

**Result**: 5/5 Passed (100.0% Accuracy).

---

## 10. Team Members
- **Member 1**: Agents & Orchestration
- **Member 2**: RAG Engineer (Document Ingestion, Embeddings, ChromaDB, Retriever & Safety Routing)
- **Member 3**: Tools / MCP Integration
- **Member 4**: Safety Guardrails & Frontend / UI
