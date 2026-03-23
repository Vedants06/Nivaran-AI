# backend/database/incident_store.py
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "data/incidents.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id          TEXT PRIMARY KEY,
            timestamp   TEXT,
            location    TEXT,
            lat         REAL,
            lon         REAL,
            type        TEXT,
            severity    TEXT,
            confidence  REAL,
            detected    TEXT,
            protocol    TEXT,
            alert_en    TEXT,
            alert_hi    TEXT,
            alert_mr    TEXT,
            tweet_public      TEXT,
            tweet_authority   TEXT,
            approval_status   TEXT DEFAULT 'PENDING',
            approved_by       TEXT DEFAULT '',
            media_kind        TEXT,
            media_name        TEXT,
            image_path        TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_incident(incident: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO incidents VALUES (
            :id, :timestamp, :location, :lat, :lon,
            :type, :severity, :confidence, :detected,
            :protocol, :alert_en, :alert_hi, :alert_mr,
            :tweet_public, :tweet_authority,
            :approval_status, :approved_by,
            :media_kind, :media_name, :image_path
        )
    ''', {
        "id":               incident.get("id", ""),
        "timestamp":        incident.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "location":         incident.get("location", ""),
        "lat":              incident.get("lat", 0.0),
        "lon":              incident.get("lon", 0.0),
        "type":             incident.get("type", ""),
        "severity":         incident.get("severity", ""),
        "confidence":       incident.get("confidence", 0.0),
        "detected":         incident.get("detected", ""),
        "protocol":         incident.get("protocol", ""),
        "alert_en":         incident.get("alert_en", ""),
        "alert_hi":         incident.get("alert_hi", ""),
        "alert_mr":         incident.get("alert_mr", ""),
        "tweet_public":     incident.get("tweet_public", ""),
        "tweet_authority":  incident.get("tweet_authority", ""),
        "approval_status":  incident.get("approval_status", "PENDING"),
        "approved_by":      incident.get("approved_by", ""),
        "media_kind":       incident.get("media_kind", ""),
        "media_name":       incident.get("media_name", ""),
        "image_path":       incident.get("image_path", "")
    })
    conn.commit()
    conn.close()

def get_all_incidents() -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM incidents ORDER BY timestamp DESC")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

def get_incident_by_id(incident_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else {}

def update_approval(incident_id: str, status: str, approved_by: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE incidents SET approval_status=?, approved_by=? WHERE id=?",
        (status, approved_by, incident_id)
    )
    conn.commit()
    conn.close()

def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM incidents")
    total = c.fetchone()[0]
    c.execute("SELECT type, COUNT(*) FROM incidents GROUP BY type")
    by_type = dict(c.fetchall())
    c.execute("SELECT severity, COUNT(*) FROM incidents GROUP BY severity")
    by_severity = dict(c.fetchall())
    conn.close()
    return {
        "total": total,
        "by_type": by_type,
        "by_severity": by_severity
    }

# Initialize on import
init_db()