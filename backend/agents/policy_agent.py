# backend/agents/policy_agent.py
import os
import logging
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, PromptTemplate, StorageContext
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pinecone import Pinecone, ServerlessSpec

# Load env
load_dotenv()

# Configure Models
Settings.llm = Groq(model="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

SYSTEM_PROMPT = """
You are Nivaran AI, a disaster management assistant.
Answer ONLY using the provided NDMA documents.
Be concise and actionable. Focus on immediate safety steps.
"""

DATA_PATH = "./data/ndma_docs"
_query_engine = None

def _load_engine():
    global _query_engine
    if _query_engine is not None:
        return _query_engine

    # 1. Initialize Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = "nivaran-ndma"

    # 2. Create index if it doesn't exist
    if index_name not in [idx.name for idx in pc.list_indexes()]:
        print("📌 Creating Pinecone index and uploading PDFs...")
        pc.create_index(
            name=index_name,
            dimension=384, # dimension for bge-small-en-v1.5
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        
        # Load local PDFs
        documents = SimpleDirectoryReader(DATA_PATH, recursive=True, required_exts=[".pdf"]).load_data()
        
        # Setup Vector Store & Storage Context
        vector_store = PineconeVectorStore(pinecone_index=pc.Index(index_name))
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # This uploads the vectors to Pinecone
        index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    else:
        # 3. Load existing index from cloud
        print("⚡ Loading knowledge base from Pinecone...")
        vector_store = PineconeVectorStore(pinecone_index=pc.Index(index_name))
        index = VectorStoreIndex.from_vector_store(vector_store)

    _query_engine = index.as_query_engine(
        similarity_top_k=5,
        text_qa_template=PromptTemplate(
            SYSTEM_PROMPT + "\n\nContext:\n{context_str}\n\nQuestion: {query_str}\nAnswer:"
        )
    )
    return _query_engine

def get_protocol(disaster_type: str) -> str:
    if not disaster_type or disaster_type.lower() in ["none", "unknown", "error"]:
        return "No disaster detected. No action required."
    try:
        engine = _load_engine()
        response = engine.query(f"What are the immediate safety steps for a {disaster_type}?")
        return str(response)
    except Exception as e:
        return f"⚠️ Protocol lookup failed: {e}"