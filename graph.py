import os
from typing import TypedDict
from langgraph.graph import StateGraph, END

# Import your Vision Agent
from agents.vision_agent import analyze_image


# ------------------------------
# Define State
# ------------------------------
class AgentState(TypedDict):
    image_path: str
    vision_output: dict
    protocol: str


workflow = StateGraph(AgentState)


# ------------------------------
# Vision Node
# ------------------------------
def detection_node(state: AgentState):
    print(f"\nRunning Vision Agent on: {state['image_path']}")

    result = analyze_image(state["image_path"])

    return {
        "vision_output": result
    }


# ------------------------------
# Protocol Node
# ------------------------------
def protocol_node(state: AgentState):
    vision = state["vision_output"]

    if vision.get("hazard"):
        disaster_type = vision.get("type", "unknown")
        severity = vision.get("severity", "unknown")

        protocol_message = (
            f"Emergency protocol activated for {disaster_type} "
            f"(Severity: {severity})."
        )
    else:
        protocol_message = "No disaster detected. No action required."

    return {
        "protocol": protocol_message
    }


# ------------------------------
# Build Graph
# ------------------------------
workflow.add_node("detect", detection_node)
workflow.add_node("get_rules", protocol_node)

workflow.set_entry_point("detect")

workflow.add_edge("detect", "get_rules")
workflow.add_edge("get_rules", END)

app = workflow.compile()


# ------------------------------
# MAIN (MULTIPLE IMAGE SUPPORT)
# ------------------------------
if __name__ == "__main__":

    folder_path = "test_images"

    if not os.path.exists(folder_path):
        print("Folder not found:", folder_path)
        exit()

    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):

            full_path = os.path.join(folder_path, filename)

            input_state = {
                "image_path": full_path
            }

            result = app.invoke(input_state)

            print("\nFINAL OUTPUT:")
            print(result)
