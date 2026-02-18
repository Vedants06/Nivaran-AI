import os
import logging
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.WARNING)

# 1. Load API Key
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("❌ GROQ_API_KEY not found! Check your .env file.")

# 2. Configure LLM + Embeddings
Settings.llm = Groq(
    model="llama-3.1-8b-instant",
    api_key=groq_api_key
)
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)

def run_rag_test():
    print("🚀 Initializing Nivaran RAG Test...")

    # 3. Data path
    data_path = "./data/ndma_docs"

    # ✅ Path validation FIRST
    if not os.path.exists(data_path) or not os.listdir(data_path):
        print(f"❌ ERROR: The folder '{data_path}' is missing or empty.")
        return

    try:
        # 4. Load PDFs
        print(f"📂 Loading NDMA PDFs from {data_path}...")
        documents = SimpleDirectoryReader(
            data_path,
            recursive=True,
            required_exts=[".pdf"]
        ).load_data()

        print(f"✅ Loaded {len(documents)} document pages.")

        # 5. Build Vector Index
        index = VectorStoreIndex.from_documents(documents)

        # 6. Create Query Engine
        query_engine = index.as_query_engine()

        # 7. User Question Loop
        print("\n🧠 Nivaran RAG is ready. Ask your questions!")
        print("Type 'exit' to quit.\n")

        while True:
            question = input("❓ Your question: ").strip()

            if question.lower() in ["exit", "quit"]:
                print("👋 Exiting Nivaran RAG. Stay safe!")
                break

            response = query_engine.query(question)

            print("\n📝 --- NDMA RESPONSE ---")
            print(response)
            print("------------------------\n")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    run_rag_test()
