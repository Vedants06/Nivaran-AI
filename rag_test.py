import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google import GooglePaLMEmbedding

# 1. Load the .env file FIRST
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Check if key is loaded correctly
if api_key:
    print(f"✅ API Key loaded successfully! (Starts with: {api_key[:5]}...)")
else:
    print("❌ API Key is still missing from .env!")
    exit() # Stop if there is no key

# 2. Configure Settings AFTER loading the key
# LLM Configuration
Settings.llm = GoogleGenAI(model="gemini-1.5-flash", api_key=api_key)

# Embedding Configuration
Settings.embed_model = GooglePaLMEmbedding(model_name="models/embedding-001", api_key=api_key)

def run_rag_test():
    print("\n--- Initializing Nivaran Librarian ---")
    
    # 3. Path to your NDMA documents
    input_dir = "./data/ndma_docs"
    
    if not os.path.exists(input_dir):
        print(f"Error: The directory {input_dir} does not exist.")
        return

    # 4. Load the documents
    print(f"Loading documents from: {input_dir}...")
    reader = SimpleDirectoryReader(input_dir)
    documents = reader.load_data()
    
    if not documents:
        print("No documents found! Put your NDMA PDFs in data/ndma_docs/")
        return

    # 5. Create the Vector Index
    print("Indexing documents... (This might take a moment)")
    index = VectorStoreIndex.from_documents(documents)
    
    # 6. Create the Query Engine
    query_engine = index.as_query_engine()
    
    # 7. Run the test query
    question = "What are the safety steps for a landslide?"
    print(f"\nQuerying: {question}")
    
    response = query_engine.query(question)
    
    # 8. Final Output
    print("\n--- Official NDMA Response ---")
    print(response)

if __name__ == "__main__":
    run_rag_test()