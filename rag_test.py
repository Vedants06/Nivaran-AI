import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from google import genai

# 1. Load the .env file
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ API Key is missing from .env!")
    exit()

# 2. Configure Settings using the 2026 Model IDs
# 2. Configure Settings using STABLE Model IDs
print("🔧 Configuring Nivaran Brain (Gemini 1.5 Flash Stable)...")

# Using 1.5-flash-latest ensures it finds the most current stable version
# Try the preferred model, but handle 404s by listing available models
preferred_model = "models/gemini-2.5-flash-latest"
llm_set = False
try:
    Settings.llm = GoogleGenAI(
        model=preferred_model,
        api_key=api_key,
    )
    llm_set = True
except Exception as e:
    print(f"⚠️ Failed to initialize model '{preferred_model}': {e}")
    try:
        client = genai.Client(api_key=api_key)
        print("Available models (first 50):")
        models = [getattr(m, "name", None) or getattr(m, "model", None) or str(m) for m in client.models.list()[:50]]
        for name in models:
            print(" -", name)

        # Try to auto-select a reasonable fallback from available models
        preferred_patterns = [
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-flash",
            "gemini-pro-latest",
            "gemini-2.5-pro",
        ]
        auto_choice = None
        for pat in preferred_patterns:
            for name in models:
                if pat in name:
                    auto_choice = name
                    break
            if auto_choice:
                break
        if auto_choice:
            print(f"Auto-selected model: {auto_choice}")
            try:
                Settings.llm = GoogleGenAI(model=auto_choice, api_key=api_key)
                llm_set = True
            except Exception as sel_err:
                print(f"Auto-selected model failed to initialize: {sel_err}")
    except Exception as list_err:
        print("Failed to list models:", list_err)

    print(f"llm_set after auto-selection attempts: {llm_set}")
    if not llm_set:
        fallback = os.getenv("GENAI_MODEL_FALLBACK")
        if fallback:
            print(f"Using fallback model from GENAI_MODEL_FALLBACK: {fallback}")
            Settings.llm = GoogleGenAI(model=fallback, api_key=api_key)
            llm_set = True
        else:
            print("Please set the environment variable GENAI_MODEL_FALLBACK to a valid model name and retry.")
            raise

# text-embedding-004 sometimes fails in v1beta; 
# 'models/embedding-001' is the absolute reliable fallback for LlamaIndex
Settings.embed_model = GoogleGenAIEmbedding(
    model_name="models/gemini-embedding-001", 
    api_key=api_key
)
def run_rag_test():
    print("\n--- Initializing Nivaran Librarian ---")
    
    # 3. Path to your NDMA documents
    # Ensure this folder exists and has at least one PDF!
    input_dir = "./data/ndma_docs"
    
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        print(f"📁 Created directory {input_dir}. Please drop your NDMA PDFs there!")
        return

    # 4. Load the documents
    print(f"📚 Loading documents from: {input_dir}...")
    reader = SimpleDirectoryReader(input_dir)
    documents = reader.load_data()
    
    if not documents:
        print("⚠️ No documents found! Add a PDF to data/ndma_docs/ and run again.")
        return

    # 5. Create the Vector Index
    # This turns PDF text into searchable mathematical vectors
    print("🧠 Indexing documents... (Building Vector Space)")
    index = VectorStoreIndex.from_documents(documents)
    
    # 6. Create the Query Engine
    query_engine = index.as_query_engine()
    
    # 7. Run the test query
    question = "What are the safety steps for a landslide?"
    print(f"\n🔍 Querying Knowledge Base: {question}")
    
    # The engine searches the PDF and generates an answer
    response = query_engine.query(question)
    
    # 8. Final Output
    print("\n--- ✅ Official NDMA Response ---")
    print(response)

if __name__ == "__main__":
    run_rag_test()