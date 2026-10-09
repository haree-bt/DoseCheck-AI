"""
rag/retriever.py
Authoritative Medical Knowledge Retrieval with Confidence and Safety Routing.
"""

from pathlib import Path
import sys
import chromadb

# Ensure root directory is importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from safety_guardrail import (
    detect_red_flags,
    detect_toxic_dosage,
    detect_vulnerable_populations
)

# Paths configuration
BASE_DIR = Path(__file__).resolve().parent
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
COLLECTION_NAME = "medication_guidelines"


def check_for_red_flags(query: str) -> list[str]:
    """
    Scans the user query for life-threatening red flags and toxic overdoses.
    """
    flags = detect_red_flags(query)
    toxic = detect_toxic_dosage(query)
    if toxic:
        flags.append(f"toxic_dosage: {toxic['reason']}")
    return flags


def retrieve_relevant_documents(
    query: str,
    top_k: int = 3,
    distance_threshold: float = 1.15
) -> dict:
    """
    Main retrieval function for DoseCheck-AI.
    
    Args:
        query: The user's medication question.
        top_k: Number of relevant chunks to retrieve.
        distance_threshold: Cutoff distance in ChromaDB. 
                            Distances above this indicate poor match.
                            
    Returns:
        Structured dictionary with grounding context, sources, confidence, and decision.
    """
    # 1. First: Check for life-threatening Red Flags in the query
    detected_red_flags = check_for_red_flags(query)
    if detected_red_flags:
        return {
            "query": query,
            "decision": "ESCALATE",
            "risk_level": "CRITICAL",
            "confidence_score": 0.99,
            "needs_escalation": True,
            "escalation_reason": f"Potential medical emergency detected: {', '.join(detected_red_flags)}",
            "answer_context": (
                "EMERGENCY RED FLAG DETECTED: The query mentions symptoms consistent with an "
                "acute medical emergency or severe adverse drug reaction. Do not provide home "
                "remedies or delay care. Advise immediate emergency medical attention (call 911 / emergency services)."
            ),
            "sources": [
                {
                    "title": "Critical Red-Flag Symptoms Requiring Immediate Emergency Care",
                    "source": "Centers for Disease Control and Prevention (CDC) & NHS Emergency Protocols",
                    "url": "https://www.nhs.uk/conditions/anaphylaxis/"
                }
            ],
            "top_chunks": [],
            "disclaimer": "Hackathon safety filter. Not medically validated."
        }

    # 1B. Check for Special Vulnerable Populations (Pediatric, Pregnancy)
    vulnerable_pops = detect_vulnerable_populations(query)
    high_risk_pops = [p for p in vulnerable_pops if p.get("severity") == "high"]
    if high_risk_pops:
        pop_msg = " | ".join(p["message"] for p in high_risk_pops)
        return {
            "query": query,
            "decision": "FLAG",
            "risk_level": "HIGH",
            "confidence_score": 0.25,
            "needs_escalation": True,
            "escalation_reason": f"Special population safety restriction: {pop_msg}",
            "answer_context": (
                f"SPECIAL POPULATION SAFETY RESTRICTION: {pop_msg} "
                "Standard adult dosage guidelines cannot be provided safely. Please consult a qualified "
                "pediatrician, obstetrician, or pharmacist directly."
            ),
            "sources": [],
            "top_chunks": [],
            "disclaimer": "Hackathon safety protocol. Pediatric and pregnancy cases require licensed clinician review."
        }

    # 2. Connect to ChromaDB
    if not VECTORSTORE_DIR.exists():
        return {
            "query": query,
            "decision": "FLAG",
            "risk_level": "HIGH",
            "confidence_score": 0.0,
            "needs_escalation": True,
            "escalation_reason": "Vector database not initialized. Please run rag/ingest.py first.",
            "answer_context": "No medical knowledge base found.",
            "sources": [],
            "top_chunks": [],
            "disclaimer": "Hackathon prototype score."
        }

    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    collection = client.get_collection(name=COLLECTION_NAME)

    # 3. Perform Similarity Search
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not documents:
        return {
            "query": query,
            "decision": "FLAG",
            "risk_level": "HIGH",
            "confidence_score": 0.1,
            "needs_escalation": True,
            "escalation_reason": "No matching medical evidence found in knowledge base.",
            "answer_context": "Insufficient evidence to answer safely.",
            "sources": [],
            "top_chunks": [],
            "disclaimer": "Hackathon prototype score."
        }

    closest_distance = distances[0]
    
    # 4. Filter and structure the retrieved chunks
    retrieved_chunks = []
    sources = []
    seen_sources = set()

    for doc, meta, dist in zip(documents, metadatas, distances):
        chunk_data = {
            "chunk_id": meta.get("chunk_id", ""),
            "text": doc,
            "distance": round(dist, 4),
            "title": meta.get("title", ""),
            "source": meta.get("source", ""),
            "url": meta.get("url", ""),
            "category": meta.get("category", "")
        }
        retrieved_chunks.append(chunk_data)

        source_key = (meta.get("title"), meta.get("source"))
        if source_key not in seen_sources:
            seen_sources.add(source_key)
            sources.append({
                "title": meta.get("title", ""),
                "source": meta.get("source", ""),
                "url": meta.get("url", "")
            })

    # 5. Evaluate Confidence and Decision Routing
    # ChromaDB distance: lower distance = higher similarity
    # Good matches are typically <= 1.05
    if closest_distance <= distance_threshold:
        # Grounded confident answer
        confidence = round(max(0.2, min(0.98, 1.0 - (closest_distance * 0.45))), 2)
        decision = "ANSWER"
        risk_level = "LOW"
        needs_escalation = False
        escalation_reason = None
        
        # Format the context text for downstream LLM/Response Agent
        context_blocks = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            context_blocks.append(
                f"[Chunk {i}] ({chunk['title']} | Source: {chunk['source']})\n{chunk['text']}"
            )
        answer_context = "\n\n".join(context_blocks)
    else:
        # Unrelated query or outside knowledge base: DO NOT FABRICATE
        confidence = round(max(0.05, 0.5 - (closest_distance * 0.2)), 2)
        decision = "FLAG"
        risk_level = "MODERATE_TO_HIGH"
        needs_escalation = True
        escalation_reason = f"Low retrieval relevance (distance {closest_distance:.2f} exceeds safety threshold {distance_threshold})."
        answer_context = (
            "INSUFFICIENT EVIDENCE: The knowledge base does not contain authoritative evidence "
            "directly covering this specific query. Do not guess or fabricate medical advice. "
            "Recommend consulting a qualified physician or pharmacist."
        )

    return {
        "query": query,
        "decision": decision,
        "risk_level": risk_level,
        "confidence_score": confidence,
        "needs_escalation": needs_escalation,
        "escalation_reason": escalation_reason,
        "answer_context": answer_context,
        "sources": sources,
        "top_chunks": retrieved_chunks,
        "disclaimer": "Hackathon safety and confidence score. Not medically validated."
    }


if __name__ == "__main__":
    import json
    # Quick standalone test
    test_q = "What is the maximum daily dose of acetaminophen?"
    print(f"Testing retrieval for query: '{test_q}'\n")
    res = retrieve_relevant_documents(test_q)
    print(f"Decision: {res['decision']}")
    print(f"Confidence: {res['confidence_score']}")
    print(f"Risk Level: {res['risk_level']}")
    print(f"Sources: {[s['title'] for s in res['sources']]}")
