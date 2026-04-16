import requests
from datetime import datetime
from typing import Optional

# Mumbai zone coordinates for hyperlocal monitoring
MUMBAI_ZONES = {
    "Andheri":  {"lat": 19.1136, "lon": 72.8697},
    "Bandra":   {"lat": 19.0544, "lon": 72.8402},
    "Dadar":    {"lat": 19.0178, "lon": 72.8478},
    "Kurla":    {"lat": 19.0726, "lon": 72.8794},
    "Borivali": {"lat": 19.2308, "lon": 72.8567},
    "Colaba":   {"lat": 18.9067, "lon": 72.8147},
    "Sion":     {"lat": 19.0404, "lon": 72.8620},
    "Chembur":  {"lat": 19.0522, "lon": 72.8989},
    "Malad":    {"lat": 19.1872, "lon": 72.8484},
    "Thane":    {"lat": 19.2183, "lon": 72.9781},
}


class WeatherAgent:
    """
    Fetches real-time weather data for Mumbai zones and computes
    a weather-based flood risk score.
    
    API: OpenWeatherMap (free tier: 1000 calls/day)
    No credit card required. Sign up at: https://openweathermap.org/api
    
    Also supports DEMO MODE for presentations — returns simulated
    monsoon conditions so the pipeline can be demonstrated any time.
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self, api_key: Optional[str] = None, demo_mode: bool = False):
        """
        Parameters:
        -----------
        api_key: str - OpenWeatherMap API key (or None for demo mode)
        demo_mode: bool - If True, returns simulated monsoon data
        """
        self.api_key = api_key
        self.demo_mode = demo_mode or (api_key is None)

    # ─────────────────────────────────────────────
    # SIMULATED DATA (Demo Mode)
    # ─────────────────────────────────────────────

    def _get_demo_weather(self, zone_name: str) -> dict:
        """
        Returns simulated Mumbai monsoon weather for demo presentations.
        This simulates the kind of conditions that cause real floods.
        """
        return {
            "zone": zone_name,
            "temperature": 26.5,
            "humidity": 94,
            "pressure": 998,
            "wind_speed": 8.2,
            "wind_deg": 225,
            "rainfall_1h": 55.0,
            "rainfall_3h": 120.0,
            "weather_condition": "Rain",
            "weather_description": "heavy intensity rain",
            "visibility": 800,
            "clouds": 100,
            "timestamp": datetime.now().isoformat(),
            "source": "DEMO_MODE_SIMULATED"
        }

    def _get_demo_forecast(self, zone_name: str) -> list:
        """Returns 24-hour simulated forecast."""
        from datetime import timedelta

        base_time = datetime.now()
        forecast = []

        # Simulate 3-hour intervals for 24 hours
        rainfall_pattern = [45, 60, 75, 90, 85, 70, 55, 40, 35, 30, 25, 20, 18, 15, 12, 10, 8, 6, 5, 4, 3, 2, 2, 1]

        for i in range(8):
            forecast.append({
                "datetime": (base_time + timedelta(hours=i * 3)).strftime("%Y-%m-%d %H:%M:%S"),
                "temp": 26 + (i % 3) * 0.5,
                "humidity": min(98, 90 + i * 0.8),
                "rainfall_3h": rainfall_pattern[i],
                "wind_speed": 7 + (i % 4) * 1.5,
                "condition": "Rain"
            })

        return forecast

    # ─────────────────────────────────────────────
    # LIVE API CALLS (Real Mode)
    # ─────────────────────────────────────────────

    def _call_api(self, endpoint: str, params: dict) -> dict:
        """Generic API caller with error handling."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise ValueError(
                    "Invalid OpenWeatherMap API key. "
                    "Get a free key at https://openweathermap.org/api"
                )
            raise ValueError(f"Weather API error: {e}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Network error calling weather API: {e}")

    def get_current_weather(self, zone_name: str) -> dict:
        """
        Fetch current weather for a specific Mumbai zone.
        
        Returns dict with:
        - zone, temperature, humidity, pressure
        - wind_speed (m/s), wind_deg
        - rainfall_1h (mm), rainfall_3h (mm)
        - weather_condition, weather_description
        - visibility (m), clouds (%)
        - timestamp, source
        """
        if self.demo_mode:
            return self._get_demo_weather(zone_name)

        coords = MUMBAI_ZONES.get(zone_name, MUMBAI_ZONES["Dadar"])

        params = {
            "lat": coords["lat"],
            "lon": coords["lon"],
            "appid": self.api_key,
            "units": "metric"
        }

        data = self._call_api("weather", params)

        return {
            "zone": zone_name,
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": data["wind"].get("speed", 0),
            "wind_deg": data["wind"].get("deg", 0),
            "rainfall_1h": data.get("rain", {}).get("1h", 0),
            "rainfall_3h": data.get("rain", {}).get("3h", 0),
            "weather_condition": data["weather"][0]["main"],
            "weather_description": data["weather"][0]["description"],
            "visibility": data.get("visibility", 10000),
            "clouds": data["clouds"]["all"],
            "timestamp": datetime.utcnow().isoformat(),
            "source": "OpenWeatherMap"
        }

    def get_forecast(self, zone_name: str, hours: int = 24) -> list:
        """
        Get hourly weather forecast.
        API returns data in 3-hour intervals.
        
        Returns list of dicts with:
        - datetime, temp, humidity
        - rainfall_3h, wind_speed, condition
        """
        if self.demo_mode:
            return self._get_demo_forecast(zone_name)

        coords = MUMBAI_ZONES.get(zone_name, MUMBAI_ZONES["Dadar"])

        # API returns 3-hour intervals, so divide hours by 3
        count = max(1, hours // 3)

        params = {
            "lat": coords["lat"],
            "lon": coords["lon"],
            "appid": self.api_key,
            "units": "metric",
            "cnt": count
        }

        data = self._call_api("forecast", params)

        forecasts = []
        for item in data.get("list", []):
            forecasts.append({
                "datetime": item["dt_txt"],
                "temp": item["main"]["temp"],
                "humidity": item["main"]["humidity"],
                "rainfall_3h": item.get("rain", {}).get("3h", 0),
                "wind_speed": item["wind"]["speed"],
                "condition": item["weather"][0]["main"]
            })

        return forecasts

    # ─────────────────────────────────────────────
    # RISK SCORING
    # ─────────────────────────────────────────────

    def compute_weather_risk(self, zone_name: str) -> dict:
        """
        Compute a composite weather risk score (0-100) for flood potential.
        
        Factors and weights:
        - Rainfall intensity: 40% (primary driver for Mumbai floods)
        - Humidity: 15%
        - Wind speed: 20% (cyclone indicator)
        - Atmospheric pressure: 15% (storm system indicator)
        - Visibility: 10% (heavy rain indicator)
        
        IMD Rainfall Classification (India):
        - Light rain: 2.5-7.5 mm/hr
        - Moderate rain: 7.5-35 mm/hr  
        - Heavy rain: 35-65 mm/hr
        - Very heavy rain: 65-115 mm/hr
        - Extremely heavy: >115 mm/hr
        """
        weather = self.get_current_weather(zone_name)

        # ── Rainfall risk (40%) ──────────────────
        # Mumbai floods start at heavy rainfall (>35mm/hr)
        rainfall = weather["rainfall_1h"]

        if rainfall > 65:
            rain_risk = 100
        elif rainfall > 35:
            rain_risk = 80
        elif rainfall > 15:
            rain_risk = 50
        elif rainfall > 7:
            rain_risk = 30
        elif rainfall > 2:
            rain_risk = 15
        else:
            rain_risk = max(0, rainfall * 5)

        # ── Humidity risk (15%) ──────────────────
        # >90% humidity + rain = waterlogging near certain
        humidity = weather["humidity"]
        humidity_risk = max(0, min(100, (humidity - 60) * 2.5))

        # ── Wind risk (20%) ──────────────────────
        # m/s to km/h: multiply by 3.6
        wind_kmh = weather["wind_speed"] * 3.6

        if wind_kmh > 60:
            wind_risk = 100
        elif wind_kmh > 40:
            wind_risk = 60
        elif wind_kmh > 25:
            wind_risk = 35
        else:
            wind_risk = max(0, wind_kmh * 1.2)

        # ── Pressure risk (15%) ─────────────────
        # <1000 hPa indicates storm system approaching
        pressure = weather["pressure"]

        if pressure < 980:
            pressure_risk = 100
        elif pressure < 990:
            pressure_risk = 80
        elif pressure < 1000:
            pressure_risk = 50
        elif pressure < 1010:
            pressure_risk = 25
        else:
            pressure_risk = 0

        # ── Visibility risk (10%) ────────────────
        visibility = weather["visibility"]

        if visibility < 200:
            visibility_risk = 100
        elif visibility < 500:
            visibility_risk = 70
        elif visibility < 1000:
            visibility_risk = 40
        elif visibility < 3000:
            visibility_risk = 20
        else:
            visibility_risk = 0

        # ── Weighted composite ───────────────────
        composite_score = (
            rain_risk * 0.40 +
            humidity_risk * 0.15 +
            wind_risk * 0.20 +
            pressure_risk * 0.15 +
            visibility_risk * 0.10
        )

        # ── Risk level ──────────────────────────
        if composite_score >= 75:
            risk_level = "CRITICAL"
            action = "IMMEDIATE_EVACUATION"
        elif composite_score >= 50:
            risk_level = "HIGH"
            action = "ALERT_AND_PREPARE"
        elif composite_score >= 25:
            risk_level = "MODERATE"
            action = "MONITOR_CLOSELY"
        else:
            risk_level = "LOW"
            action = "ROUTINE_MONITORING"

        return {
            "zone": zone_name,
            "composite_score": round(composite_score, 2),
            "risk_level": risk_level,
            "recommended_action": action,
            "factors": {
                "rainfall_risk":        round(rain_risk, 2),
                "humidity_risk":        round(humidity_risk, 2),
                "wind_risk":            round(wind_risk, 2),
                "pressure_risk":        round(pressure_risk, 2),
                "visibility_risk":      round(visibility_risk, 2),
            },
            "raw_data": {
                "temperature_c":       weather["temperature"],
                "humidity_pct":        weather["humidity"],
                "pressure_hpa":        weather["pressure"],
                "wind_speed_ms":       weather["wind_speed"],
                "rainfall_1h_mm":      weather["rainfall_1h"],
                "rainfall_3h_mm":      weather["rainfall_3h"],
                "condition":           weather["weather_condition"],
                "visibility_m":         weather["visibility"],
                "source":             weather.get("source", "Unknown")
            },
            "timestamp": weather["timestamp"]
        }

    def scan_all_zones(self) -> list:
        """
        Scan all 10 Mumbai zones and return risk data sorted by score.
        Useful for the dashboard to show "Most At-Risk Zones" ranking.
        """
        results = []
        for zone in MUMBAI_ZONES:
            try:
                risk = self.compute_weather_risk(zone)
                results.append(risk)
            except Exception as e:
                results.append({
                    "zone": zone,
                    "composite_score": -1,
                    "risk_level": "ERROR",
                    "error": str(e)
                })

        # Sort by score descending (highest risk first)
        results.sort(key=lambda x: x.get("composite_score", -1), reverse=True)
        return results

    def get_incoming_rain_alert(self, zone_name: str) -> dict:
        """
        Check the forecast and issue an alert if heavy rain is coming.
        
        Returns:
        - alert_triggered: bool
        - hours_until_heavy_rain: int or None
        - peak_rainfall_mm: float
        """
        forecast = self.get_forecast(zone_name, hours=24)

        for i, entry in enumerate(forecast):
            if entry["rainfall_3h"] >= 35:  # Heavy rain threshold
                return {
                    "alert_triggered": True,
                    "hours_until_heavy_rain": i * 3,
                    "peak_rainfall_mm": entry["rainfall_3h"],
                    "at_datetime": entry["datetime"]
                }

        return {
            "alert_triggered": False,
            "hours_until_heavy_rain": None,
            "peak_rainfall_mm": max(f["rainfall_3h"] for f in forecast) if forecast else 0,
        }


# ─────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("OPENWEATHER_API_KEY", "")

    # Toggle this to test with simulated data
    USE_DEMO = True  # Set to False if you have a real API key

    agent = WeatherAgent(api_key=api_key, demo_mode=USE_DEMO)

    print("=" * 60)
    print("WEATHER AGENT — STANDALONE TEST")
    print(f"Mode: {'DEMO (simulated monsoon)' if USE_DEMO else 'LIVE (real API)'}")
    print("=" * 60)

    # Test single zone
    print("\n📍 Single Zone Test: Dadar")
    print("-" * 40)
    result = agent.compute_weather_risk("Dadar")
    print(f"Zone:             {result['zone']}")
    print(f"Composite Score:  {result['composite_score']}/100")
    print(f"Risk Level:      {result['risk_level']}")
    print(f"Action:          {result['recommended_action']}")
    print()
    print("Factor Breakdown:")
    for factor, score in result["factors"].items():
        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        print(f"  {factor:20s} {bar} {score}/100")

    print()
    print("Raw Weather Data:")
    for key, value in result["raw_data"].items():
        print(f"  {key:20s} {value}")

    # Test incoming rain alert
    print("\n📅 Incoming Rain Alert Check:")
    print("-" * 40)
    alert = agent.get_incoming_rain_alert("Dadar")
    print(f"Alert Triggered:      {alert['alert_triggered']}")
    if alert["alert_triggered"]:
        print(f"Hours Until Heavy Rain: {alert['hours_until_heavy_rain']}")
        print(f"Peak Rainfall:         {alert['peak_rainfall_mm']} mm")
        print(f"At:                   {alert['at_datetime']}")

    # Scan all zones
    print("\n🏙️ All Mumbai Zones Scan:")
    print("-" * 40)
    all_zones = agent.scan_all_zones()
    print(f"{'Zone':12s} {'Score':>6s} {'Level':12s} {'Action'}")
    print("-" * 40)
    for z in all_zones:
        score = z.get("composite_score", -1)
        level = z.get("risk_level", "ERROR")
        action = z.get("recommended_action", "-")
        print(f"{z['zone']:12s} {score:>6.1f}  {level:12s} {action}")

    # Forecast
    print("\n📅 24-Hour Forecast (Dadar):")
    print("-" * 40)
    forecast = agent.get_forecast("Dadar", hours=24)
    for f in forecast:
        rainfall = f.get("rainfall_3h", 0)
        bar = "🌧️" * min(int(rainfall / 5), 10)
        print(f"  {f['datetime']:20s} {f['temp']:5.1f}°C  "
              f"💧 {rainfall:5.1f}mm  {bar}")