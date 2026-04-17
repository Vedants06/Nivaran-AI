import os
import sys
import logging
import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from groq import Groq as GroqClient
from dotenv import load_dotenv

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from backend.agents.vision_agent import analyze_image
from backend.agents.policy_agent import get_protocol
from backend.pipeline.risk_engine import MultiFactorRiskEngine

logging.getLogger("google.ai").setLevel(logging.WARNING)
load_dotenv()

groq_client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))


# ─────────────────────────────────────────────
# STATE DEFINITION
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    # Input
    image_path: str
    zone_name: str
    lat: float
    lon: float
    demo_mode: bool

    # Vision output
    vision_output: dict

    # Multi-factor risk (NEW)
    multi_factor_risk: Optional[dict]

    # Protocol
    protocol: str

    # Alerts
    alert_en: str
    alert_hi: str
    alert_mr: str
    tweet_public: str
    tweet_authority: str

    # Risk level for conditional branching
    risk_level: str


# ─────────────────────────────────────────────
# NODE 1: DETECTION
# ─────────────────────────────────────────────

def detection_node(state: AgentState):
    print(f"\n🔍 Running Vision Agent on: {state['image_path']}")
    result = analyze_image(state["image_path"])
    return {"vision_output": result}


# ─────────────────────────────────────────────
# NODE 2: MULTI-FACTOR RISK FUSION (NEW)
# ─────────────────────────────────────────────

def risk_fusion_node(state: AgentState):
    """
    Takes vision output and combines with real-time
    weather, geological, and historical data to produce
    a composite flood risk score.
    
    This is the node that addresses the judges' criticism.
    """
    vision = state.get("vision_output", {})

    # Extract location from state (with defaults)
    zone_name = state.get("zone_name", "Dadar")
    lat = state.get("lat", 19.0178)
    lon = state.get("lon", 72.8478)
    demo_mode = state.get("demo_mode", False)

    # Convert vision confidence to 0-100 score
    visual_score = 0
    if vision.get("hazard", False):
        visual_score = vision.get("confidence", 0.5) * 100

    print(f"\n🧠 Running Multi-Factor Risk Fusion")
    print(f"   Zone: {zone_name} ({lat}, {lon})")
    print(f"   Visual Score: {visual_score}/100")
    print(f"   Demo Mode: {demo_mode}")

    try:
        engine = MultiFactorRiskEngine(demo_mode=demo_mode)

        risk = engine.compute_risk(
            zone_name=zone_name,
            lat=lat,
            lon=lon,
            visual_score=visual_score,
            visual_confidence=vision.get("confidence", 0),
            disaster_type="flood"
        )

        print(f"   Composite Score: {risk['composite_risk_score']}/100")
        print(f"   Risk Level: {risk['overall_risk_level']}")

        return {
            "multi_factor_risk": risk,
            "risk_level": risk["overall_risk_level"]
        }

    except Exception as e:
        print(f"   ⚠️ Risk engine error: {e}")
        # If risk engine fails, assume moderate risk
        # so the pipeline still continues (safe default)
        return {
            "multi_factor_risk": {
                "composite_risk_score": 50,
                "overall_risk_level": "MODERATE",
                "error": str(e),
                "factor_breakdown": {}
            },
            "risk_level": "MODERATE"
        }


# ─────────────────────────────────────────────
# CONDITIONAL EDGE: SHOULD WE ALERT?
# ─────────────────────────────────────────────

def should_alert(state: AgentState) -> str:
    """
    Decision: Should we proceed to alert generation?
    
    Now based on COMPOSITE risk score, not just visual detection.
    - HIGH or CRITICAL → generate alert
    - MODERATE with visual detection → generate alert  
    - LOW or MINIMAL → no alert needed
    
    This prevents false alarms when weather data doesn't
    corroborate what the camera saw.
    """
    vision = state.get("vision_output", {})
    risk_level = state.get("risk_level", "MINIMAL")
    risk = state.get("multi_factor_risk", {})
    composite = risk.get("composite_risk_score", 0)

    has_visual = vision.get("hazard", False)

    print(f"\n📊 Decision Check:")
    print(f"   Visual hazard: {has_visual}")
    print(f"   Composite score: {composite}/100")
    print(f"   Risk level: {risk_level}")

    # Alert if composite risk is concerning
    if composite >= 60 or risk_level in ["HIGH", "CRITICAL"]:
        print("   → Proceeding to alert generation")
        return "generate_alert"

    # Also alert if visual detected something AND score is moderate
    if has_visual and composite >= 35:
        print("   → Proceeding to alert (visual + moderate risk)")
        return "generate_alert"

    print("   → Risk below threshold, skipping alert")
    return "no_alert"


# ─────────────────────────────────────────────
# NODE 3: PROTOCOL RETRIEVAL
# ─────────────────────────────────────────────

def protocol_node(state: AgentState):
    vision = state["vision_output"]
    if vision.get("hazard"):
        disaster_type = vision.get("type", "unknown")
        print(f"📚 Querying NDMA knowledge base for: {disaster_type}")
        protocol = get_protocol(disaster_type)
    else:
        protocol = "No disaster detected. No action required."
    return {"protocol": protocol}


# ─────────────────────────────────────────────
# NODE 4: ALERT GENERATION (UPDATED WITH MULTI-FACTOR CONTEXT)
# ─────────────────────────────────────────────

def alert_node(state: AgentState):
    vision = state["vision_output"]

    if not vision.get("hazard"):
        return {
            "alert_en": "", "alert_hi": "", "alert_mr": "",
            "tweet_public": "", "tweet_authority": ""
        }

    disaster_type = vision.get("type", "unknown")
    severity = vision.get("severity", "unknown")
    protocol = state["protocol"]
    zone_name = state.get("zone_name", "Mumbai")

    # ── Build multi-factor context for the LLM ──
    risk = state.get("multi_factor_risk", {})
    factors = risk.get("factor_breakdown", {})

    # Weather context
    weather_desc = factors.get("weather", {}).get("description", "N/A")
    weather_raw = factors.get("weather", {}).get("raw", {})

    # Geo context
    geo_desc = factors.get("geological", {}).get("description", "N/A")

    # Historical context
    hist_desc = factors.get("historical", {}).get("description", "N/A")

    # Forecast context
    forecast_desc = factors.get("forecast", {}).get("description", "N/A")

    # Composite score
    composite_score = risk.get("composite_risk_score", 0)
    risk_level = risk.get("overall_risk_level", "UNKNOWN")

    print(f"\n🌐 Generating multilingual alerts for: {disaster_type} ({severity})")
    print(f"   With multi-factor context (composite: {composite_score}/100)")

    # ── Enhanced prompt with environmental data ──
    prompt = f"""You are a disaster alert officer for Mumbai city.
A {severity} severity {disaster_type} has been detected at {zone_name}, Mumbai.

MULTI-FACTOR RISK ASSESSMENT:
- Composite Risk Score: {composite_score}/100 ({risk_level})
- Weather: {weather_desc}
- Rainfall: {weather_raw.get('rainfall_mm', 'N/A')} mm/hr
- Ground Conditions: {geo_desc}
- Historical Pattern: {hist_desc}
- Forecast: {forecast_desc}

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
            "alert_en": f"⚠️ {disaster_type.capitalize()} alert at {zone_name}. Follow NDMA guidelines.",
            "alert_hi": f"⚠️ {zone_name} में {disaster_type} चेतावनी। NDMA दिशानिर्देशों का पालन करें।",
            "alert_mr": f"⚠️ {zone_name} मध्ये {disaster_type} इशारा। NDMA मार्गदर्शक तत्त्वांचे पालन करा।",
            "tweet_public": f"⚠️ {disaster_type.capitalize()} detected at {zone_name}, Mumbai. Stay safe. #MumbaiRains #Nivaran",
            "tweet_authority": f"@RailwayMumbai @MumbaiPolice 🚨 {disaster_type.capitalize()} at {zone_name}. Immediate action needed. #NivaranAlert"
        }


# ─────────────────────────────────────────────
# NODE 5: NO ALERT (LOW RISK PATH)
# ─────────────────────────────────────────────

def no_alert_node(state: AgentState):
    """When composite risk is too low for an alert."""
    risk = state.get("multi_factor_risk", {})
    composite = risk.get("composite_risk_score", 0)
    zone_name = state.get("zone_name", "Mumbai")

    print(f"\n✅ No alert needed for {zone_name}. Composite: {composite}/100")

    return {
        "alert_en": "",
        "alert_hi": "",
        "alert_mr": "",
        "tweet_public": "",
        "tweet_authority": "",
        "protocol": "Composite risk below threshold. No NDMA protocol needed."
    }


# ─────────────────────────────────────────────
# BUILD THE GRAPH
# ─────────────────────────────────────────────

workflow = StateGraph(AgentState)

# Add all nodes
workflow.add_node("detect", detection_node)
workflow.add_node("risk_fusion", risk_fusion_node)
workflow.add_node("get_rules", protocol_node)
workflow.add_node("draft_alert", alert_node)
workflow.add_node("no_alert", no_alert_node)

# Set entry point
workflow.set_entry_point("detect")

# Flow: detect → risk_fusion (ALWAYS)
workflow.add_edge("detect", "risk_fusion")

# Conditional: risk_fusion → alert or no_alert
workflow.add_conditional_edges(
    "risk_fusion",
    should_alert,
    {
        "generate_alert": "get_rules",
        "no_alert": "no_alert"
    }
)

# Alert path: get_rules → draft_alert → END
workflow.add_edge("get_rules", "draft_alert")
workflow.add_edge("draft_alert", END)

# No alert path: no_alert → END
workflow.add_edge("no_alert", END)

# Compile
app = workflow.compile()


# ─────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import os

    test_folder = os.path.join(root_path, "test_images")
    if not os.path.exists(test_folder):
        print(f"❌ Folder not found: {test_folder}")
        sys.exit()

    print("=" * 60)
    print("GRAPH PIPELINE TEST — WITH MULTI-FACTOR RISK ENGINE")
    print("=" * 60)

    for filename in sorted(os.listdir(test_folder)):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            img_path = os.path.join(test_folder, filename)

            print(f"\n{'=' * 60}")
            print(f"Testing: {filename}")
            print(f"{'=' * 60}")

            result = app.invoke({
                "image_path": img_path,
                "zone_name": "Hindmata",
                "lat": 19.0145,
                "lon": 72.8510,
                "demo_mode": True
            })

            vision = result["vision_output"]
            risk = result.get("multi_factor_risk", {})
            composite = risk.get("composite_risk_score", 0)
            risk_level = result.get("risk_level", "UNKNOWN")

            print(f"\n{'─' * 40}")
            print(f"FINAL RESULTS:")
            print(f"{'─' * 40}")
            print(f"  Hazard:           {vision.get('type', 'N/A')}")
            print(f"  Severity:         {vision.get('severity', 'N/A')}")
            print(f"  Visual Confidence: {vision.get('confidence', 0):.2f}")
            print(f"  Composite Score:  {composite}/100")
            print(f"  Risk Level:       {risk_level}")
            print(f"  Alert EN:         {result.get('alert_en', '')[:80]}...")
            print(f"  Tweet:            {result.get('tweet_public', '')[:80]}...")
            print(f"{'─' * 40}")