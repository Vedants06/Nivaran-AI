# agents/policy_agent.py
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
# Silence noisy logs
# --------------------------------------------------
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.WARNING)

# --------------------------------------------------
# Load env & configure models ONCE at module level
# --------------------------------------------------
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("❌ GROQ_API_KEY not found! Check your .env file.")

Settings.llm = Groq(
    model="llama-3.1-8b-instant",
    api_key=groq_api_key
)
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)

# --------------------------------------------------
# System Prompt
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
- Be concise and actionable. Focus on immediate safety steps.
"""

DATA_PATH = "./data/ndma_docs"

# --------------------------------------------------
# Build index ONCE when module loads (not on every call)
# --------------------------------------------------
_query_engine = None

def _load_engine():
    """Lazy-load the RAG engine once and cache it."""
    global _query_engine

    if _query_engine is not None:
        return _query_engine

    if not os.path.exists(DATA_PATH) or not os.listdir(DATA_PATH):
        raise FileNotFoundError(
            f"❌ NDMA docs folder '{DATA_PATH}' is missing or empty. "
            "Add NDMA PDFs before running."
        )

    print("📂 Loading NDMA PDFs (first call only)...")
    documents = SimpleDirectoryReader(
        DATA_PATH,
        recursive=True,
        required_exts=[".pdf"]
    ).load_data()

    print(f"✅ Indexed {len(documents)} pages.")

    index = VectorStoreIndex.from_documents(documents)

    _query_engine = index.as_query_engine(
        similarity_top_k=5,
        text_qa_template=PromptTemplate(
            SYSTEM_PROMPT +
            "\n\nContext:\n{context_str}\n\nQuestion: {query_str}\nAnswer:"
        )
    )

    return _query_engine


# --------------------------------------------------
# 🔑 THE CALLABLE FUNCTION Vedant's graph.py imports
# --------------------------------------------------
def get_protocol(disaster_type: str) -> str:
    """
    Given a disaster type (e.g. 'flood', 'landslide', 'fire'),
    query the NDMA knowledge base and return safety protocol text.

    Returns a plain string — ready to drop into AgentState["protocol"].
    """
    if not disaster_type or disaster_type.lower() in ["none", "unknown", "error"]:
        return "No disaster detected. No action required."

    query = f"What are the immediate safety steps and emergency protocol for a {disaster_type}?"

    try:
        engine = _load_engine()
        response = engine.query(query)
        return str(response)

    except FileNotFoundError as e:
        print(str(e))
        return f"⚠️ Protocol lookup failed: NDMA docs not found. Manual response required for {disaster_type}."

    except Exception as e:
        print(f"❌ RAG error: {e}")
        return f"⚠️ Protocol lookup failed due to an error. Manual response required for {disaster_type}."