import os
import sys
import logging
from typing import TypedDict
from langgraph.graph import StateGraph, END
from groq import Groq as GroqClient
from dotenv import load_dotenv

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from backend.agents.vision_agent import analyze_image
from backend.agents.policy_agent import get_protocol

logging.getLogger("google.ai").setLevel(logging.WARNING)
load_dotenv()

groq_client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))

class AgentState(TypedDict):
    image_path:      str
    vision_output:   dict
    protocol:        str
    alert_en:        str
    alert_hi:        str
    alert_mr:        str
    tweet_public:    str
    tweet_authority: str

def detection_node(state: AgentState):
    print(f"\n🔍 Running Vision Agent on: {state['image_path']}")
    result = analyze_image(state["image_path"])
    return {"vision_output": result}

def protocol_node(state: AgentState):
    vision = state["vision_output"]
    if vision.get("hazard"):
        disaster_type = vision.get("type", "unknown")
        print(f"📚 Querying NDMA knowledge base for: {disaster_type}")
        protocol = get_protocol(disaster_type)
    else:
        protocol = "No disaster detected. No action required."
    return {"protocol": protocol}

def alert_node(state: AgentState):
    vision = state["vision_output"]

    if not vision.get("hazard"):
        return {
            "alert_en": "", "alert_hi": "", "alert_mr": "",
            "tweet_public": "", "tweet_authority": ""
        }

    disaster_type = vision.get("type", "unknown")
    severity      = vision.get("severity", "unknown")
    protocol      = state["protocol"]

    print(f"🌐 Generating multilingual alerts for: {disaster_type} ({severity})")

    prompt = f"""You are a disaster alert officer for Mumbai city.
A {severity} severity {disaster_type} has been detected at a Mumbai railway station.

NDMA Protocol summary:
{protocol[:400]}

Generate ALL of the following. Follow the format exactly:

EN: <Public alert in English, max 180 chars>
HI: <Public alert in Hindi, max 180 chars>
MR: <Public alert in Marathi, max 180 chars>
PUBLIC_TWEET: <Tweet for general public, max 220 chars, include #MumbaiRains #Nivaran>
AUTHORITY_TWEET: <Tweet tagging @RailwayMumbai @MumbaiPolice @NDMA_India, max 220 chars, include #NivaranAlert>

Only output these 5 lines. Nothing else."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600
        )
        text = response.choices[0].message.content.strip()
        print(f"\n📢 Raw Alert Output:\n{text}")

        output = {
            "alert_en": "", "alert_hi": "", "alert_mr": "",
            "tweet_public": "", "tweet_authority": ""
        }
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("EN:"):
                output["alert_en"] = line[3:].strip()
            elif line.startswith("HI:"):
                output["alert_hi"] = line[3:].strip()
            elif line.startswith("MR:"):
                output["alert_mr"] = line[3:].strip()
            elif line.startswith("PUBLIC_TWEET:"):
                output["tweet_public"] = line[13:].strip()
            elif line.startswith("AUTHORITY_TWEET:"):
                output["tweet_authority"] = line[16:].strip()

        return output

    except Exception as e:
        print(f"❌ Alert generation failed: {e}")
        return {
            "alert_en":        f"⚠️ {disaster_type.capitalize()} alert. Follow NDMA guidelines.",
            "alert_hi":        f"⚠️ {disaster_type} चेतावनी। NDMA दिशानिर्देशों का पालन करें।",
            "alert_mr":        f"⚠️ {disaster_type} इशारा। NDMA मार्गदर्शक तत्त्वांचे पालन करा।",
            "tweet_public":    f"⚠️ {disaster_type.capitalize()} detected in Mumbai. Stay safe. #MumbaiRains #Nivaran",
            "tweet_authority": f"@RailwayMumbai @MumbaiPolice 🚨 {disaster_type.capitalize()} HIGH severity. Immediate action needed. #NivaranAlert"
        }

# Build graph
workflow = StateGraph(AgentState)
workflow.add_node("detect",     detection_node)
workflow.add_node("get_rules",  protocol_node)
workflow.add_node("draft_alert", alert_node)

workflow.set_entry_point("detect")
workflow.add_edge("detect",      "get_rules")
workflow.add_edge("get_rules",   "draft_alert")
workflow.add_edge("draft_alert", END)

app = workflow.compile()

if __name__ == "__main__":
    test_folder = os.path.join(root_path, "test_images")
    if not os.path.exists(test_folder):
        print(f"❌ Folder not found: {test_folder}")
        sys.exit()

    for filename in os.listdir(test_folder):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            img_path = os.path.join(test_folder, filename)
            result   = app.invoke({"image_path": img_path})
            print(f"\n{'='*50}")
            print(f"Hazard:   {result['vision_output'].get('type')}")
            print(f"Severity: {result['vision_output'].get('severity')}")
            print(f"Alert EN: {result.get('alert_en','')}")
            print(f"Tweet:    {result.get('tweet_public','')}")
            print(f"{'='*50}")