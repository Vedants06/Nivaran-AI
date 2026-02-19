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
# Main RAG Function
# --------------------------------------------------
def run_rag_test():
    print("🚀 Initializing Nivaran RAG Test...")

    data_path = "./data/ndma_docs"

    # Validate data folder
    if not os.path.exists(data_path) or not os.listdir(data_path):
        print(f"❌ ERROR: '{data_path}' is missing or empty.")
        return

    try:
        # Load NDMA PDFs
        print(f"📂 Loading NDMA PDFs from {data_path}...")
        documents = SimpleDirectoryReader(
            data_path,
            recursive=True,
            required_exts=[".pdf"]
        ).load_data()

        print(f"✅ Loaded {len(documents)} document pages.")

        # Build vector index
        index = VectorStoreIndex.from_documents(documents)

        # Create query engine with strict prompt
        query_engine = index.as_query_engine(
            similarity_top_k=5,
            text_qa_template=PromptTemplate(
                SYSTEM_PROMPT +
                "\n\nContext:\n{context_str}\n\nQuestion: {query_str}\nAnswer:"
            )
        )

        print("\n🧠 Nivaran RAG is ready. Ask disaster-related questions!")
        print("Type 'exit' to quit.\n")

        # User interaction loop
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

            response = query_engine.query(question)

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

