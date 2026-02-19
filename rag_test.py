import os
import logging
from dotenv import load_dotenv

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    PromptTemplate
)
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# --------------------------------------------------
# Silence HTTP / Groq logs
# --------------------------------------------------
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.WARNING)

# --------------------------------------------------
# Load API Key
# --------------------------------------------------
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("❌ GROQ_API_KEY not found! Check your .env file.")

# --------------------------------------------------
# Configure LLM & Embeddings
# --------------------------------------------------
Settings.llm = Groq(
    model="llama-3.1-8b-instant",
    api_key=groq_api_key
)

Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)

# --------------------------------------------------
# Disaster Guard Keywords
# --------------------------------------------------
DISASTER_KEYWORDS = [
    "flood", "earthquake", "fire", "landslide",
    "cyclone", "disaster", "ndma",
    "evacuation", "emergency", "rescue",
    "safety", "hazard"
]

# --------------------------------------------------
# NDMA System Prompt (STRICT)
# --------------------------------------------------
SYSTEM_PROMPT = """
You are Nivaran AI, a disaster management assistant.

Rules:
- Answer ONLY using the provided NDMA documents.
- If the question is not related to disasters, emergency response,
  safety protocols, or NDMA guidelines, respond with:
  "❌ This question is outside the scope of disaster management and NDMA guidelines."
- Do NOT use general knowledge.
- Do NOT guess.
"""

# --------------------------------------------------
# Module-level cache so the index is only built ONCE
# even if get_protocol() is called multiple times.
# --------------------------------------------------
_query_engine = None


def _build_query_engine():
    """
    Loads NDMA PDFs, builds the vector index, and returns a query engine.
    Called automatically the first time get_protocol() is used.
    """
    global _query_engine

    if _query_engine is not None:
        return _query_engine          # Already built — reuse it

    data_path = "./data/ndma_docs"

    if not os.path.exists(data_path) or not os.listdir(data_path):
        raise FileNotFoundError(
            f"❌ NDMA docs folder '{data_path}' is missing or empty. "
            "Please add PDF files before running."
        )

    print("📂 Loading NDMA PDFs (first call — this takes ~30s)...")
    documents = SimpleDirectoryReader(
        data_path,
        recursive=True,
        required_exts=[".pdf"]
    ).load_data()
    print(f"✅ Loaded {len(documents)} document pages. Building index...")

    index = VectorStoreIndex.from_documents(documents)

    _query_engine = index.as_query_engine(
        similarity_top_k=5,
        text_qa_template=PromptTemplate(
            SYSTEM_PROMPT +
            "\n\nContext:\n{context_str}\n\nQuestion: {query_str}\nAnswer:"
        )
    )

    print("✅ RAG query engine ready.\n")
    return _query_engine


# --------------------------------------------------
# ✅ PUBLIC FUNCTION — called by Vedant's graph.py
# --------------------------------------------------
def get_protocol(disaster_type: str) -> str:
    """
    Given a disaster type (e.g. "flood", "landslide", "fire"),
    queries the NDMA vector index and returns the official
    safety protocol as a plain string.

    Usage in graph.py:
        from rag_test import get_protocol
        protocol = get_protocol("flood")

    Args:
        disaster_type: The hazard type from the Vision Agent output.
                       Expected values: "flood", "landslide", "fire",
                       "infrastructure", "cyclone", or "unknown".

    Returns:
        A string containing the NDMA protocol steps,
        or a safe fallback message if nothing is found.
    """
    if not disaster_type or disaster_type.lower() in ("none", "unknown", "error"):
        return "ℹ️ No disaster detected. No NDMA protocol required."

    disaster_type = disaster_type.lower().strip()

    # Build a clear, focused question for the RAG engine
    query = (
        f"What are the official NDMA safety steps and emergency response "
        f"protocol for a {disaster_type}? List all key actions."
    )

    try:
        engine = _build_query_engine()
        response = engine.query(query)
        protocol_text = str(response).strip()

        if not protocol_text:
            return (
                f"⚠️ No specific protocol found for '{disaster_type}'. "
                "Please consult your local NDMA authority."
            )

        return protocol_text

    except FileNotFoundError as e:
        # NDMA docs not set up — return a clear error for the dashboard
        return str(e)

    except Exception as e:
        return f"❌ RAG Error while fetching protocol for '{disaster_type}': {e}"


# --------------------------------------------------
# Interactive test loop (unchanged — for your own testing)
# --------------------------------------------------
def run_rag_test():
    print("🚀 Initializing Nivaran RAG Test...")

    try:
        engine = _build_query_engine()

        print("🧠 Nivaran RAG is ready. Ask disaster-related questions!")
        print("Type 'exit' to quit.\n")

        while True:
            question = input("❓ Your question: ").strip()

            if question.lower() in ["exit", "quit"]:
                print("👋 Exiting Nivaran RAG. Stay safe!")
                break

            # Keyword guard
            if not any(word in question.lower() for word in DISASTER_KEYWORDS):
                print(
                    "❌ This question is not related to disaster management "
                    "or NDMA guidelines.\n"
                )
                continue

            response = engine.query(question)

            print("\n📝 --- NDMA RESPONSE ---")
            print(response)
            print("------------------------\n")

    except Exception as e:
        print(f"❌ An error occurred: {e}")


# --------------------------------------------------
# Entry Point
# --------------------------------------------------
if __name__ == "__main__":
    run_rag_test()