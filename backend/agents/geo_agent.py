import requests
import math
from datetime import datetime, timedelta
from typing import Optional


# Mumbai's known landslide-prone elevated areas
LANDSLIDE_PRONE_ZONES = {
    "Malabar Hill":     {"lat": 18.9553, "lon": 72.7946, "slope_risk": 70},
    "Powai Hills":      {"lat": 19.1176, "lon": 72.9060, "slope_risk": 65},
    "Vikhroli Hills":   {"lat": 19.1099, "lon": 72.9301, "slope_risk": 60},
    "Chembur Hills":    {"lat": 19.0522, "lon": 72.8989, "slope_risk": 55},
    "Ghatkopar Hills":  {"lat": 19.0860, "lon": 72.9080, "slope_risk": 50},
    "Borivali NP":      {"lat": 19.2147, "lon": 72.8713, "slope_risk": 45},
}

# Mumbai's chronically flood-prone areas with historical base risk
FLOOD_PRONE_ZONES = {
    "Hindmata":         90,
    "Sion":             85,
    "King Circle":      80,
    "Andheri Subway":   85,
    "Milan Subway":     80,
    "Dadar":            75,
    "Kurla":            70,
    "Chembur":          65,
    "Malad":            60,
    "Borivali":         55,
    "Bandra":           50,
    "Colaba":           45,
    "Thane":            50,
}


class GeoAgent:
    """
    Fetches geological and environmental data relevant to
    flood and landslide risk assessment for Mumbai.
    
    Data Sources (ALL FREE, no API keys needed):
    1. Open-Meteo API — soil moisture, soil temperature
    2. USGS Earthquake API — recent seismic activity
    3. Static terrain data — Mumbai's known risk zones
    
    Also supports DEMO MODE for presentations.
    """

    SOIL_URL = "https://api.open-meteo.com/v1/forecast"
    SEISMIC_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode

    # ─────────────────────────────────────────────
    # SIMULATED DATA (Demo Mode)
    # ─────────────────────────────────────────────

    def _get_demo_soil(self) -> dict:
        """Simulated saturated soil conditions during heavy monsoon."""
        return {
            "soil_moisture_surface": 0.43,
            "soil_moisture_deep": 0.38,
            "soil_temperature_c": 25.2,
            "source": "DEMO_MODE_SIMULATED",
            "timestamp": datetime.now().isoformat()
        }

    def _get_demo_seismic(self) -> dict:
        """Simulated minor seismic activity."""
        return {
            "earthquakes": [
                {
                    "magnitude": 2.3,
                    "place": "45km NE of Mumbai, India",
                    "depth_km": 10.5,
                    "time": (datetime.now() - timedelta(days=2)).isoformat(),
                }
            ],
            "count": 1,
            "max_magnitude": 2.3,
            "source": "DEMO_MODE_SIMULATED"
        }

    # ─────────────────────────────────────────────
    # SOIL MOISTURE (Open-Meteo API)
    # ─────────────────────────────────────────────

    def get_soil_conditions(self, lat: float = 19.076,
                            lon: float = 72.877) -> dict:
        """
        Get soil moisture and temperature from Open-Meteo.
        
        Why this matters for floods:
        - Saturated soil (moisture > 0.40) cannot absorb more water
        - All rainfall runs off as surface water → waterlogging
        - This is literally why areas like Hindmata flood
        
        Why this matters for landslides:
        - Saturated soil on slopes becomes unstable
        - Heavy soil + rain + gravity = landslide
        
        Soil moisture scale:
        - 0.00 - 0.15: Dry soil
        - 0.15 - 0.25: Normal moisture
        - 0.25 - 0.35: Wet soil
        - 0.35 - 0.45: Saturated (flood/landslide risk)
        - 0.45+: Fully saturated (danger zone)
        
        FREE API — No key needed.
        """
        if self.demo_mode:
            return self._get_demo_soil()

        try:
            response = requests.get(
                self.SOIL_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": (
                        "soil_moisture_0_to_1cm,"
                        "soil_moisture_1_to_3cm,"
                        "soil_moisture_3_to_9cm,"
                        "soil_temperature_0cm"
                    ),
                    "timezone": "Asia/Kolkata",
                    "forecast_days": 1
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})

            # Get latest available values
            surface_moisture_list = hourly.get("soil_moisture_0_to_1cm", [])
            deep_moisture_list = hourly.get("soil_moisture_3_to_9cm", [])
            temp_list = hourly.get("soil_temperature_0cm", [])

            # Filter out None values and get last valid reading
            surface = self._last_valid(surface_moisture_list, 0.2)
            deep = self._last_valid(deep_moisture_list, 0.15)
            temp = self._last_valid(temp_list, 25.0)

            return {
                "soil_moisture_surface": round(surface, 4),
                "soil_moisture_deep": round(deep, 4),
                "soil_temperature_c": round(temp, 1),
                "source": "Open-Meteo",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"⚠️ Soil data fetch failed: {e}")
            return {
                "soil_moisture_surface": 0.2,
                "soil_moisture_deep": 0.15,
                "soil_temperature_c": 25.0,
                "source": "FALLBACK_DEFAULT",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _last_valid(self, data_list: list, default: float) -> float:
        """Get last non-None value from a list."""
        for value in reversed(data_list):
            if value is not None:
                return value
        return default

    # ─────────────────────────────────────────────
    # SEISMIC ACTIVITY (USGS API)
    # ─────────────────────────────────────────────

    def get_seismic_activity(self, lat: float = 19.076,
                              lon: float = 72.877,
                              radius_km: int = 300,
                              days: int = 7) -> dict:
        """
        Check recent earthquake activity near Mumbai.
        
        Why this matters:
        - Seismic events destabilize slopes and structures
        - Even small tremors (2.0-3.0) can trigger landslides
          in already-saturated soil
        - Larger quakes (4.0+) have independent danger
        
        FREE API — No key needed.
        USGS provides global earthquake data in real-time.
        """
        if self.demo_mode:
            return self._get_demo_seismic()

        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            response = requests.get(
                self.SEISMIC_URL,
                params={
                    "format": "geojson",
                    "starttime": start_time.strftime("%Y-%m-%d"),
                    "endtime": end_time.strftime("%Y-%m-%d"),
                    "latitude": lat,
                    "longitude": lon,
                    "maxradiuskm": radius_km,
                    "minmagnitude": 2.0,
                    "orderby": "time"
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            earthquakes = []
            for feature in data.get("features", []):
                props = feature["properties"]
                coords = feature["geometry"]["coordinates"]
                earthquakes.append({
                    "magnitude": props["mag"],
                    "place": props["place"],
                    "depth_km": coords[2],
                    "time": datetime.fromtimestamp(
                        props["time"] / 1000
                    ).isoformat(),
                })

            max_mag = max(
                [eq["magnitude"] for eq in earthquakes], default=0
            )

            return {
                "earthquakes": earthquakes[:10],  # Keep top 10
                "count": len(earthquakes),
                "max_magnitude": max_mag,
                "source": "USGS",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"⚠️ Seismic data fetch failed: {e}")
            return {
                "earthquakes": [],
                "count": 0,
                "max_magnitude": 0,
                "source": "FALLBACK_DEFAULT",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    # ─────────────────────────────────────────────
    # RISK SCORING
    # ─────────────────────────────────────────────

    def compute_soil_risk(self, lat: float = 19.076,
                          lon: float = 72.877) -> dict:
        """
        Compute soil saturation risk score (0-100).
        
        Higher moisture = higher flood/landslide risk.
        """
        soil = self.get_soil_conditions(lat, lon)
        moisture = soil["soil_moisture_surface"]

        if moisture > 0.45:
            score = 100
            status = "FULLY_SATURATED"
        elif moisture > 0.40:
            score = 85
            status = "NEAR_SATURATED"
        elif moisture > 0.35:
            score = 65
            status = "WET"
        elif moisture > 0.25:
            score = 40
            status = "MOIST"
        elif moisture > 0.15:
            score = 20
            status = "NORMAL"
        else:
            score = 5
            status = "DRY"

        return {
            "score": round(score, 2),
            "status": status,
            "moisture_value": moisture,
            "raw_data": soil
        }

    def compute_seismic_risk(self, lat: float = 19.076,
                              lon: float = 72.877) -> dict:
        """
        Compute seismic risk score (0-100).
        
        Based on recent earthquake count and max magnitude.
        """
        seismic = self.get_seismic_activity(lat, lon)
        max_mag = seismic["max_magnitude"]
        count = seismic["count"]

        if max_mag >= 5.0:
            score = 100
        elif max_mag >= 4.0:
            score = 70
        elif max_mag >= 3.0:
            score = 40
        elif count > 5:
            score = 30  # Earthquake swarm
        elif count > 0:
            score = max(10, count * 8)
        else:
            score = 0

        return {
            "score": round(score, 2),
            "max_magnitude": max_mag,
            "event_count": count,
            "raw_data": seismic
        }

    def get_historical_flood_risk(self, zone_name: str) -> dict:
        """
        Get historical flood risk for a Mumbai zone.
        
        Based on BMC records of chronically flooded areas.
        Returns a base risk score (0-100) based on how frequently
        the area has flooded in the past.
        """
        # Try exact match first
        score = FLOOD_PRONE_ZONES.get(zone_name, None)

        # If no exact match, try partial match
        if score is None:
            zone_lower = zone_name.lower()
            for known_zone, known_score in FLOOD_PRONE_ZONES.items():
                if known_zone.lower() in zone_lower or zone_lower in known_zone.lower():
                    score = known_score
                    break

        # Default for unknown areas
        if score is None:
            score = 30

        return {
            "score": score,
            "zone": zone_name,
            "known_flood_zone": score >= 60,
            "source": "BMC Historical Records"
        }

    def get_nearest_slope_risk(self, lat: float, lon: float) -> dict:
        """
        Check if coordinates are near a known landslide-prone slope.
        
        Returns slope risk based on proximity to known elevated areas.
        """
        min_dist = float('inf')
        slope_risk = 10  # Default for flat terrain
        nearest_zone = "Flat Terrain (Low-lying)"

        for zone_name, zone_data in LANDSLIDE_PRONE_ZONES.items():
            dist = math.sqrt(
                (lat - zone_data["lat"]) ** 2 +
                (lon - zone_data["lon"]) ** 2
            )
            if dist < min_dist:
                min_dist = dist
                # Within ~5km radius
                if dist < 0.05:
                    slope_risk = zone_data["slope_risk"]
                    nearest_zone = zone_name
                elif dist < 0.1:
                    slope_risk = zone_data["slope_risk"] * 0.5
                    nearest_zone = f"Near {zone_name}"

        return {
            "score": round(slope_risk, 2),
            "nearest_zone": nearest_zone,
            "distance_deg": round(min_dist, 4),
            "source": "Mumbai Geological Survey Data"
        }

    def compute_full_geo_risk(self, zone_name: str,
                               lat: float = 19.076,
                               lon: float = 72.877) -> dict:
        """
        Complete geological risk assessment combining all factors.
        
        Returns:
        - soil_risk: How saturated is the ground
        - seismic_risk: Any recent earthquake activity
        - historical_risk: Is this area known to flood
        - slope_risk: Is this near hilly terrain
        - composite geo score
        """
        soil = self.compute_soil_risk(lat, lon)
        seismic = self.compute_seismic_risk(lat, lon)
        historical = self.get_historical_flood_risk(zone_name)
        slope = self.get_nearest_slope_risk(lat, lon)

        # For flood risk: soil + historical are primary
        # For landslide risk: soil + slope + seismic are primary
        # We compute a general geo score here
        # The risk_engine.py will apply disaster-specific weights

        composite = (
            soil["score"] * 0.35 +
            historical["score"] * 0.30 +
            seismic["score"] * 0.15 +
            slope["score"] * 0.20
        )

        if composite >= 75:
            risk_level = "CRITICAL"
        elif composite >= 50:
            risk_level = "HIGH"
        elif composite >= 25:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        return {
            "zone": zone_name,
            "composite_score": round(composite, 2),
            "risk_level": risk_level,
            "factors": {
                "soil_saturation": soil,
                "seismic_activity": seismic,
                "historical_flood": historical,
                "terrain_slope": slope,
            },
            "timestamp": datetime.now().isoformat()
        }


# ─────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────
if __name__ == "__main__":

    # Toggle this for testing
    USE_DEMO = True

    agent = GeoAgent(demo_mode=USE_DEMO)

    print("=" * 60)
    print("GEO AGENT — STANDALONE TEST")
    print(f"Mode: {'DEMO (simulated)' if USE_DEMO else 'LIVE (real APIs)'}")
    print("=" * 60)

    # Test soil conditions
    print("\n🌍 Soil Conditions (Dadar area):")
    print("-" * 40)
    soil = agent.get_soil_conditions(19.0178, 72.8478)
    print(f"  Surface Moisture: {soil['soil_moisture_surface']}")
    print(f"  Deep Moisture:    {soil['soil_moisture_deep']}")
    print(f"  Temperature:      {soil['soil_temperature_c']}°C")
    print(f"  Source:           {soil['source']}")

    # Test seismic activity
    print("\n🔴 Seismic Activity (300km radius):")
    print("-" * 40)
    seismic = agent.get_seismic_activity()
    print(f"  Events (7 days):  {seismic['count']}")
    print(f"  Max Magnitude:    {seismic['max_magnitude']}")
    if seismic["earthquakes"]:
        for eq in seismic["earthquakes"][:3]:
            print(f"    • M{eq['magnitude']} — {eq['place']}")

    # Test historical flood risk
    print("\n📜 Historical Flood Risk:")
    print("-" * 40)
    for zone in ["Hindmata", "Sion", "Dadar", "Andheri Subway", "Colaba"]:
        hist = agent.get_historical_flood_risk(zone)
        bar = "█" * int(hist["score"] / 5) + "░" * (20 - int(hist["score"] / 5))
        known = "⚠️ KNOWN" if hist["known_flood_zone"] else "  OK"
        print(f"  {zone:18s} {bar} {hist['score']:3d}/100 {known}")

    # Test full geo risk
    print("\n🧮 Full Geo Risk Assessment (Dadar):")
    print("-" * 40)
    geo = agent.compute_full_geo_risk("Dadar", 19.0178, 72.8478)
    print(f"  Composite Score:  {geo['composite_score']}/100")
    print(f"  Risk Level:       {geo['risk_level']}")
    print()
    print("  Factor Breakdown:")
    for name, factor in geo["factors"].items():
        score = factor["score"]
        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        print(f"    {name:20s} {bar} {score}/100")

    # Test slope risk for different locations
    print("\n⛰️ Slope Risk by Location:")
    print("-" * 40)
    test_locations = [
        ("Malabar Hill", 18.955, 72.795),
        ("Powai", 19.118, 72.906),
        ("Dadar (flat)", 19.018, 72.848),
        ("Andheri (flat)", 19.114, 72.870),
    ]
    for name, lat, lon in test_locations:
        slope = agent.get_nearest_slope_risk(lat, lon)
        print(f"  {name:20s} Score: {slope['score']:5.1f}  "
              f"Near: {slope['nearest_zone']}")