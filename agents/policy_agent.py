import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

# Load documents
documents = SimpleDirectoryReader("data/ndma_docs").load_data()

# Create LLM and embedding
llm = Gemini(model="models/gemini-2.5-flash", api_key=API_KEY)
embed_model = GeminiEmbedding(model_name="models/embedding-001", api_key=API_KEY)

# Create index
index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)

query_engine = index.as_query_engine(llm=llm)


def get_safety_protocol(disaster_type: str):
    query = f"What are the official safety protocols for {disaster_type}?"
    response = query_engine.query(query)
    return str(response)

if __name__ == "__main__":
    result = get_safety_protocol("flood")
    print(result)
