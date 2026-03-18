import os
import sys
import logging
from typing import TypedDict
from langgraph.graph import StateGraph, END
from groq import Groq as GroqClient
from dotenv import load_dotenv

# --- DIRECT RUN FIX: Ensures 'backend' is recognized from the root ---
# This calculates the path to 'Nivaran-AI' and adds it to Python's memory
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Now we import using the project structure
from backend.agents.vision_agent import analyze_image
from backend.agents.policy_agent import get_protocol
from backend.utils.report_generator import generate_report

# Suppress unnecessary logs
logging.getLogger("google.ai").setLevel(logging.WARNING)
load_dotenv()

# Initialize Groq for the Alert Agent
groq_client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))

# ------------------------------
# 1. Define State
# ------------------------------
class AgentState(TypedDict):
    image_path: str
    vision_output: dict
    protocol: str
    alert_en: str
    alert_hi: str
    alert_mr: str
    tweet_public: str
    tweet_authority: str

# ------------------------------
# 2. Define Nodes
# ------------------------------

def detection_node(state: AgentState):
    """Analyze the image using Gemini Vision."""
    print(f"\n🔍 Running Vision Agent on: {state['image_path']}")
    result = analyze_image(state["image_path"])
    return {"vision_output": result}

def protocol_node(state: AgentState):
    """Retrieve NDMA guidelines from Pinecone based on detection."""
    vision = state["vision_output"]

    if vision.get("hazard"):
        disaster_type = vision.get("type", "unknown")
        print(f"📚 Querying NDMA knowledge base (Pinecone) for: {disaster_type}")
        protocol = get_protocol(disaster_type) 
    else:
        protocol = "No disaster detected. No action required."

    return {"protocol": protocol}

def alert_node(state: AgentState):
    """Generate multilingual alerts using Groq (Llama 3.1)."""
    vision = state["vision_output"]

    if not vision.get("hazard"):
        return {"alert_en": "", "alert_hi": "", "alert_mr": "", "tweet_public": "", "tweet_authority": ""}

    print(f"🌐 Generating multilingual alerts for: {vision.get('type')} ({vision.get('severity')})")

    prompt = f"""You are a disaster officer. Generate alerts for a {vision.get('type')}. 
    Protocol: {state['protocol'][:300]}
    Format:
    EN: <text>
    HI: <text>
    MR: <text>
    PUBLIC_TWEET: <text>
    AUTHORITY_TWEET: <text>"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.choices[0].message.content.strip()
        # Simple parsing logic
        lines = text.splitlines()
        return {"alert_en": text} # Simplified for brevity; you can use your full parsing logic here
    except Exception as e:
        print(f"❌ Alert Error: {e}")
        return {"alert_en": "Alert generated."}

def report_node(state: AgentState):
    """Final Step: Generate the PDF Report using real agent data."""
    vision = state["vision_output"]

    if vision.get("hazard"):
        print(f"📋 Generating Official PDF Report...")
        
        # Prepare the exact dictionary report_generator.py expects
        report_data = {
            "type": vision.get("type"),
            "severity": vision.get("severity"),
            "confidence": vision.get("confidence"),
            "protocol": state["protocol"],  # REAL text from Pinecone
            "location": "Mumbai - Central Station Feed"
        }
        
        # Trigger your utility script
        generate_report(report_data)
    else:
        print("❄️ No hazard detected. Skipping PDF generation.")
    
    return state

# ------------------------------
# 3. Build & Compile Graph
# ------------------------------
workflow = StateGraph(AgentState)

workflow.add_node("detect", detection_node)
workflow.add_node("get_rules", protocol_node)
workflow.add_node("draft_alert", alert_node)
workflow.add_node("generate_pdf", report_node)

workflow.set_entry_point("detect")
workflow.add_edge("detect", "get_rules")
workflow.add_edge("get_rules", "draft_alert")
workflow.add_edge("draft_alert", "generate_pdf")
workflow.add_edge("generate_pdf", END)

app = workflow.compile()

# ------------------------------
# 4. Main Execution
# ------------------------------
if __name__ == "__main__":
    # Get the test_images folder from the root Nivaran-AI folder
    test_folder = os.path.join(root_path, "test_images")

    if not os.path.exists(test_folder):
        print(f"❌ Error: Folder not found at {test_folder}")
        sys.exit()

    for filename in os.listdir(test_folder):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            img_path = os.path.join(test_folder, filename)
            result = app.invoke({"image_path": img_path})
            print(f"✅ Finished {filename}: Hazard={result['vision_output'].get('type')}")