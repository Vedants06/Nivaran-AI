# backend/api/server.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import sys, os, shutil
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.incident_store import (
    save_incident, get_all_incidents,
    get_incident_by_id, update_approval, get_stats
)
from pipeline.graph import app as nivaran_graph
from datetime import datetime

app = FastAPI(title="Nivaran API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def root():
    return {"message": "Nivaran API is running ✅"}

@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    location: str = Form("Unknown"),
    lat: float = Form(19.0760),
    lon: float = Form(72.8777)
):
    temp_path = f"data/temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    result = nivaran_graph.invoke({"image_path": temp_path})
    vision = result["vision_output"]

    incident_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    incident = {
        "id":              incident_id,
        "time":            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "location":        location,
        "lat":             lat,
        "lon":             lon,
        "type":            vision.get("type", "unknown").capitalize(),
        "severity":        vision.get("severity", "unknown").capitalize(),
        "confidence":      vision.get("confidence", 0.0),
        "detected":        "YES" if vision.get("hazard") else "NO",
        "protocol":        result["protocol"],
        "alert_en":        result.get("alert_en", ""),
        "alert_hi":        result.get("alert_hi", ""),
        "alert_mr":        result.get("alert_mr", ""),
        "tweet_public":    result.get("tweet_public", ""),
        "tweet_authority": result.get("tweet_authority", ""),
        "image_path":      temp_path,
        "approval_status": "PENDING"
    }

    save_incident(incident)
    return incident

@app.get("/api/incidents")
def incidents():
    return get_all_incidents()

@app.get("/api/incidents/{incident_id}")
def incident(incident_id: str):
    return get_incident_by_id(incident_id)

@app.post("/api/incidents/{incident_id}/approve")
def approve(incident_id: str, status: str, approved_by: str = "Officer"):
    update_approval(incident_id, status, approved_by)
    return {"message": f"Incident {incident_id} marked as {status}"}

@app.get("/api/stats")
def stats():
    return get_stats()