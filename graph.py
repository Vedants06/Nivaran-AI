import os
import logging
from typing import TypedDict
from langgraph.graph import StateGraph, END
from groq import Groq as GroqClient
from dotenv import load_dotenv

from agents.vision_agent import analyze_image
from agents.policy_agent import get_protocol

logging.getLogger("google.ai").setLevel(logging.WARNING)
load_dotenv()

groq_client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))

# ------------------------------
# Define State
# ------------------------------
class AgentState(TypedDict):
    image_path: str
    vision_output: dict
    protocol: str
    alert_en: str
    alert_hi: str
    alert_mr: str


workflow = StateGraph(AgentState)


# ------------------------------
# Node 1: Vision
# ------------------------------
def detection_node(state: AgentState):
    print(f"\n🔍 Running Vision Agent on: {state['image_path']}")
    result = analyze_image(state["image_path"])
    return {"vision_output": result}


# ------------------------------
# Node 2: NDMA Protocol
# ------------------------------
def protocol_node(state: AgentState):
    vision = state["vision_output"]

    if vision.get("hazard"):
        disaster_type = vision.get("type", "unknown")
        print(f"\n📚 Querying NDMA knowledge base for: {disaster_type}")
        protocol = get_protocol(disaster_type)
    else:
        protocol = "No disaster detected. No action required."

    return {"protocol": protocol}


# ------------------------------
# Node 3: Multilingual Alerts
# ------------------------------
def alert_node(state: AgentState):
    vision = state["vision_output"]

    # Skip alert generation if no hazard
    if not vision.get("hazard"):
        return {"alert_en": "", "alert_hi": "", "alert_mr": ""}

    disaster_type = vision.get("type", "unknown")
    severity = vision.get("severity", "unknown")
    protocol = state["protocol"]

    print(f"\n🌐 Generating multilingual alerts for: {disaster_type} ({severity})")

    prompt = f"""You are a disaster alert officer for Mumbai city.
A {severity} severity {disaster_type} has been detected.

NDMA Protocol summary:
{protocol[:400]}

Write 3 short public safety alerts (max 200 characters each).
Be specific, actionable, and urgent.

Format strictly as:
EN: <alert in English>
HI: <alert in Hindi>
MR: <alert in Marathi>

Only output these 3 lines. Nothing else."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        )

        text = response.choices[0].message.content.strip()
        print(f"\n📢 Raw Alert Output:\n{text}")

        alerts = {"alert_en": "", "alert_hi": "", "alert_mr": ""}
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("EN:"):
                alerts["alert_en"] = line[3:].strip()
            elif line.startswith("HI:"):
                alerts["alert_hi"] = line[3:].strip()
            elif line.startswith("MR:"):
                alerts["alert_mr"] = line[3:].strip()

        return alerts

    except Exception as e:
        print(f"❌ Alert generation failed: {e}")
        return {
            "alert_en": f"⚠️ {disaster_type.capitalize()} alert. Follow NDMA guidelines.",
            "alert_hi": f"⚠️ {disaster_type} चेतावनी। NDMA दिशानिर्देशों का पालन करें।",
            "alert_mr": f"⚠️ {disaster_type} इशारा। NDMA मार्गदर्शक तत्त्वांचे पालन करा।"
        }


# ------------------------------
# Build Graph
# ------------------------------
workflow.add_node("detect", detection_node)
workflow.add_node("get_rules", protocol_node)
workflow.add_node("draft_alert", alert_node)

workflow.set_entry_point("detect")
workflow.add_edge("detect", "get_rules")
workflow.add_edge("get_rules", "draft_alert")
workflow.add_edge("draft_alert", END)

app = workflow.compile()


# ------------------------------
# MAIN
# ------------------------------
if __name__ == "__main__":
    folder_path = "test_images"

    if not os.path.exists(folder_path):
        print("Folder not found:", folder_path)
        exit()

    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            full_path = os.path.join(folder_path, filename)

            result = app.invoke({"image_path": full_path})

            print("\n" + "="*50)
            print("FINAL OUTPUT:")
            print(f"  Hazard:   {result['vision_output'].get('type')}")
            print(f"  Severity: {result['vision_output'].get('severity')}")
            print(f"  Protocol:\n{result['protocol']}")
            print(f"\n  Alert (EN): {result['alert_en']}")
            print(f"  Alert (HI): {result['alert_hi']}")
            print(f"  Alert (MR): {result['alert_mr']}")
            print("="*50)