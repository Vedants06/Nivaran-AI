import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "data/incidents.db"


def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create table with all columns including new multi-factor ones
    c.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id                  TEXT PRIMARY KEY,
            timestamp           TEXT,
            location            TEXT,
            lat                 REAL,
            lon                 REAL,
            type                TEXT,
            severity            TEXT,
            confidence          REAL,
            detected            TEXT,
            protocol            TEXT,
            alert_en            TEXT,
            alert_hi            TEXT,
            alert_mr            TEXT,
            tweet_public        TEXT,
            tweet_authority     TEXT,
            approval_status     TEXT DEFAULT 'PENDING',
            approved_by         TEXT DEFAULT '',
            media_kind          TEXT,
            media_name          TEXT,
            image_path          TEXT,
            composite_risk_score    REAL DEFAULT 0.0,
            risk_level              TEXT DEFAULT 'UNKNOWN',
            weather_data            TEXT DEFAULT '{}',
            geo_data                TEXT DEFAULT '{}'
        )
    ''')

    # ── Migration: add new columns to existing databases ──
    # This handles the case where incidents.db already exists
    # from before our changes. SQLite doesn't support ADD COLUMN IF EXISTS
    # so we try each one and ignore if it already exists.
    new_columns = [
        ("composite_risk_score", "REAL DEFAULT 0.0"),
        ("risk_level",           "TEXT DEFAULT 'UNKNOWN'"),
        ("weather_data",         "TEXT DEFAULT '{}'"),
        ("geo_data",             "TEXT DEFAULT '{}'"),
    ]

    for col_name, col_def in new_columns:
        try:
            c.execute(f"ALTER TABLE incidents ADD COLUMN {col_name} {col_def}")
            print(f"  ✅ Added column: {col_name}")
        except sqlite3.OperationalError:
            # Column already exists — this is fine, skip it
            pass

    conn.commit()
    conn.close()


def save_incident(incident: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── Extract multi-factor data ──────────────────────────
    # Handle both old-style incidents (no multi-factor)
    # and new-style incidents (with multi-factor)
    composite_score = incident.get("composite_score", 0.0)
    risk_level = incident.get("risk_level", "UNKNOWN")

    # Serialize factor breakdown as JSON for storage
    factor_breakdown = incident.get("factor_breakdown", {})
    weather_raw = {}
    geo_raw = {}

    if factor_breakdown:
        # Extract weather raw data
        weather_factor = factor_breakdown.get("weather", {})
        weather_raw = weather_factor.get("raw", {})

        # Extract geo raw data
        geo_factor = factor_breakdown.get("geological", {})
        geo_raw = {
            "soil_moisture": geo_factor.get("details", {}).get("soil_moisture", 0),
            "soil_status": geo_factor.get("details", {}).get("soil_status", ""),
            "seismic_events": geo_factor.get("details", {}).get("seismic_events", 0),
            "max_magnitude": geo_factor.get("details", {}).get("max_magnitude", 0),
        }

    c.execute('''
        INSERT OR REPLACE INTO incidents VALUES (
            :id, :timestamp, :location, :lat, :lon,
            :type, :severity, :confidence, :detected,
            :protocol, :alert_en, :alert_hi, :alert_mr,
            :tweet_public, :tweet_authority,
            :approval_status, :approved_by,
            :media_kind, :media_name, :image_path,
            :composite_risk_score, :risk_level,
            :weather_data, :geo_data
        )
    ''', {
        "id":                   incident.get("id", ""),
        "timestamp":            incident.get("time",
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "location":             incident.get("location", ""),
        "lat":                  incident.get("lat", 0.0),
        "lon":                  incident.get("lon", 0.0),
        "type":                 incident.get("type", ""),
        "severity":             incident.get("severity", ""),
        "confidence":           incident.get("confidence", 0.0),
        "detected":             incident.get("detected", ""),
        "protocol":             incident.get("protocol", ""),
        "alert_en":             incident.get("alert_en", ""),
        "alert_hi":             incident.get("alert_hi", ""),
        "alert_mr":             incident.get("alert_mr", ""),
        "tweet_public":         incident.get("tweet_public", ""),
        "tweet_authority":      incident.get("tweet_authority", ""),
        "approval_status":      incident.get("approval_status", "PENDING"),
        "approved_by":          incident.get("approved_by", ""),
        "media_kind":           incident.get("media_kind", ""),
        "media_name":           incident.get("media_name", ""),
        "image_path":           incident.get("image_path", ""),
        "composite_risk_score": float(composite_score),
        "risk_level":           str(risk_level),
        "weather_data":         json.dumps(weather_raw),
        "geo_data":             json.dumps(geo_raw),
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

    # Parse JSON fields back to dicts
    for row in rows:
        for json_field in ["weather_data", "geo_data"]:
            if isinstance(row.get(json_field), str):
                try:
                    row[json_field] = json.loads(row[json_field])
                except (json.JSONDecodeError, TypeError):
                    row[json_field] = {}

    return rows


def get_incident_by_id(incident_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {}

    result = dict(row)

    # Parse JSON fields
    for json_field in ["weather_data", "geo_data"]:
        if isinstance(result.get(json_field), str):
            try:
                result[json_field] = json.loads(result[json_field])
            except (json.JSONDecodeError, TypeError):
                result[json_field] = {}

    return result


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

    # New: average composite risk score
    c.execute("SELECT AVG(composite_risk_score) FROM incidents WHERE composite_risk_score > 0")
    avg_risk = c.fetchone()[0] or 0.0

    # New: count by risk level
    c.execute("SELECT risk_level, COUNT(*) FROM incidents GROUP BY risk_level")
    by_risk_level = dict(c.fetchall())

    # New: count of high composite risk incidents
    c.execute("SELECT COUNT(*) FROM incidents WHERE composite_risk_score >= 60")
    high_risk_count = c.fetchone()[0]

    conn.close()

    return {
        "total":            total,
        "by_type":          by_type,
        "by_severity":      by_severity,
        "avg_risk_score":   round(avg_risk, 1),
        "by_risk_level":    by_risk_level,
        "high_risk_count":  high_risk_count,
    }


def get_high_risk_incidents(threshold: float = 60.0) -> list:
    """
    Fetch only incidents with composite risk score above threshold.
    Useful for filtering the dashboard to show only real threats.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT * FROM incidents WHERE composite_risk_score >= ? ORDER BY composite_risk_score DESC",
        (threshold,)
    )
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows


def get_incidents_by_zone(zone_name: str) -> list:
    """
    Fetch all incidents for a specific location/zone.
    Useful for zone-specific risk tracking.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT * FROM incidents WHERE location LIKE ? ORDER BY timestamp DESC",
        (f"%{zone_name}%",)
    )
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows


# Initialize on import
init_db()


# ─────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("INCIDENT STORE — STANDALONE TEST")
    print("=" * 60)

    # Test saving an incident with multi-factor data
    test_incident = {
        "id": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "location": "Hindmata",
        "lat": 19.0145,
        "lon": 72.8510,
        "type": "Flood",
        "severity": "High",
        "confidence": 0.92,
        "detected": "YES",
        "protocol": "Evacuate low-lying areas immediately.",
        "alert_en": "⚠️ Severe flooding at Hindmata. Evacuate immediately.",
        "alert_hi": "⚠️ हिंदमाता में गंभीर बाढ़। तुरंत खाली करें।",
        "alert_mr": "⚠️ हिंदमाता येथे तीव्र पूर. त्वरित स्थलांतर करा.",
        "tweet_public": "🚨 Severe flood at Hindmata, Mumbai. #MumbaiRains #Nivaran",
        "tweet_authority": "@MumbaiPolice @NDMA_India 🚨 Flood at Hindmata. #NivaranAlert",
        "approval_status": "PENDING",
        "media_kind": "image",
        "media_name": "flood_test.jpg",
        "image_path": "test_images/flood.jpg",
        # Multi-factor fields
        "composite_score": 78.5,
        "risk_level": "HIGH",
        "factor_breakdown": {
            "weather": {
                "raw": {
                    "rainfall_mm": 55.0,
                    "humidity_pct": 94,
                    "pressure_hpa": 998,
                    "wind_speed_ms": 8.2,
                    "condition": "Rain"
                }
            },
            "geological": {
                "details": {
                    "soil_moisture": 0.43,
                    "soil_status": "NEAR_SATURATED",
                    "seismic_events": 1,
                    "max_magnitude": 2.3,
                }
            }
        }
    }

    print("\n📝 Saving test incident...")
    save_incident(test_incident)
    print(f"   ✅ Saved: {test_incident['id']}")

    print("\n📊 Database Stats:")
    stats = get_stats()
    print(f"   Total incidents:    {stats['total']}")
    print(f"   By type:            {stats['by_type']}")
    print(f"   By severity:        {stats['by_severity']}")
    print(f"   Avg risk score:     {stats['avg_risk_score']}/100")
    print(f"   High risk count:    {stats['high_risk_count']}")
    print(f"   By risk level:      {stats['by_risk_level']}")

    print("\n🔍 Fetching saved incident:")
    fetched = get_incident_by_id(test_incident["id"])
    print(f"   ID:                 {fetched.get('id')}")
    print(f"   Location:           {fetched.get('location')}")
    print(f"   Composite Score:    {fetched.get('composite_risk_score')}")
    print(f"   Risk Level:         {fetched.get('risk_level')}")
    print(f"   Weather Data:       {fetched.get('weather_data')}")
    print(f"   Geo Data:           {fetched.get('geo_data')}")

    print("\n🏙️ High Risk Incidents (score ≥ 60):")
    high_risk = get_high_risk_incidents(60)
    for inc in high_risk:
        print(f"   {inc['id']} | {inc['location']} | "
              f"Score: {inc['composite_risk_score']} | "
              f"Level: {inc['risk_level']}")

    print("\n✅ Incident store test complete.")