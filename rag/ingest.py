"""
rag/ingest.py
Document Ingestion, Cleaning, Chunking, and Embedding into ChromaDB.
"""

import os
import re
from pathlib import Path
import chromadb

# Paths configuration
BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "documents"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
COLLECTION_NAME = "medication_guidelines"


def parse_metadata_and_body(file_path: Path):
    """
    Reads a document and extracts YAML-style header metadata and body text.
    Handles Windows UTF-8 BOM, CRLF, and LF line endings.
    """
    text = file_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    metadata = {
        "source": "Unknown",
        "title": file_path.stem.replace("_", " ").title(),
        "url": "",
        "category": file_path.parent.name
    }
    
    # Check for frontmatter delimited by ---
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if frontmatter_match:
        header_raw = frontmatter_match.group(1)
        body = frontmatter_match.group(2)
        for line in header_raw.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                metadata[key.strip()] = val.strip()
    else:
        body = text

    # Text cleaning: normalize multiple spaces/newlines
    cleaned_body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return metadata, cleaned_body


def chunk_text(text: str, chunk_size: int = 450, overlap: int = 80) -> list[str]:
    """
    Splits text into overlapping chunks using paragraph and sentence boundaries.
    
    Why overlap?
    Prevents critical medical facts from being split across chunk boundaries.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{paragraph}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
                # Keep the last portion for overlap
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = f"{overlap_text}\n\n{paragraph}".strip()
            else:
                # In case a single paragraph is longer than chunk_size
                chunks.append(paragraph)

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def ingest_documents():
    """
    Main ingestion pipeline:
    1. Reads authoritative documents from rag/documents/
    2. Cleans and chunks the text
    3. Generates embeddings and stores in ChromaDB at rag/vectorstore/
    """
    print("=" * 60)
    print("DoseCheck-AI: Starting Medical Knowledge Ingestion...")
    print(f"Loading documents from: {DOCS_DIR}")
    print("=" * 60)

    # Initialize persistent ChromaDB client
    os.makedirs(VECTORSTORE_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    
    # Get or create collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Authoritative medical safety & dosage guidelines"}
    )

    doc_files = list(DOCS_DIR.rglob("*.txt"))
    if not doc_files:
        print("No .txt documents found in documents directory!")
        return

    all_ids = []
    all_documents = []
    all_metadatas = []

    total_chunks = 0

    for doc_path in doc_files:
        metadata, body = parse_metadata_and_body(doc_path)
        chunks = chunk_text(body, chunk_size=450, overlap=80)
        
        print(f"\nProcessing: [{metadata.get('category')}] {metadata.get('title')}")
        print(f"   Source: {metadata.get('source')}")
        print(f"   URL: {metadata.get('url')}")
        print(f"   Created {len(chunks)} chunks.")

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{doc_path.stem}_chunk_{idx}"
            chunk_meta = {
                "source": metadata.get("source", "Unknown"),
                "title": metadata.get("title", doc_path.stem),
                "url": metadata.get("url", ""),
                "category": metadata.get("category", "general"),
                "chunk_id": chunk_id
            }
            all_ids.append(chunk_id)
            all_documents.append(chunk)
            all_metadatas.append(chunk_meta)
            total_chunks += 1

    # Upsert into ChromaDB (adds or updates existing chunks)
    print(f"\nWriting {total_chunks} chunks to ChromaDB vectorstore...")
    collection.upsert(
        ids=all_ids,
        documents=all_documents,
        metadatas=all_metadatas
    )

    print("\n" + "=" * 60)
    print(f"SUCCESS: Ingested {len(doc_files)} documents ({total_chunks} total chunks).")
    print(f"ChromaDB local database saved at: {VECTORSTORE_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    ingest_documents()
