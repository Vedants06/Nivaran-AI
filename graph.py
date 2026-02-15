from typing import TypedDict
from langgraph.graph import StateGraph, END

# Define what data moves through your system
class AgentState(TypedDict):
    hazard_detected: bool
    disaster_type: str
    protocol: str

workflow = StateGraph(AgentState)

# Vedant's Task: Connect Om and Atharva's functions as nodes
def detection_node(state):
    # Call Om's function here
    return {"hazard_detected": True, "disaster_type": "flood"}

def protocol_node(state):
    # Call Atharva's function here
    return {"protocol": "Evacuate to Platform 1"}

workflow.add_node("detect", detection_node)
workflow.add_node("get_rules", protocol_node)

workflow.set_entry_point("detect")
workflow.add_edge("detect", "get_rules")
workflow.add_edge("get_rules", END)

app = workflow.compile()