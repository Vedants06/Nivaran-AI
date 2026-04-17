import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

from backend.agents.weather_agent import WeatherAgent
from backend.agents.geo_agent import GeoAgent

load_dotenv()


class MultiFactorRiskEngine:
    """
    Fuses data from ALL sources to produce a composite,
    multi-factor flood risk assessment.
    
    This directly addresses the criticism:
    "You can't predict disasters from images alone."
    
    Now we combine:
    1. Visual detection (from existing vision_agent / Gemini)
    2. Weather data (rainfall, wind, pressure, humidity)
    3. Geological data (soil moisture, seismic activity)
    4. Historical flood patterns (BMC records)
    
    Each factor has a weight. No single factor can trigger
    a high-risk alert alone. Multiple sources must corroborate.
    
    FLOOD-SPECIFIC WEIGHTS:
    - Visual:     25%  (camera sees water/flooding)
    - Weather:    35%  (rainfall is primary flood driver)
    - Geological: 15%  (soil saturation, can ground absorb water?)
    - Historical: 15%  (does this area flood regularly?)
    - Forecast:   10%  (is more rain coming?)
    """

    # Weight profile for flood risk assessment
    FLOOD_WEIGHTS = {
        "visual":     0.25,
        "weather":    0.35,
        "geological": 0.15,
        "historical": 0.15,
        "forecast":   0.10,
    }

    def __init__(self, demo_mode: bool = False):
        """
        Parameters:
        -----------
        demo_mode: bool
            If True, all agents return simulated monsoon data.
            If False, agents call real APIs.
        """
        api_key = os.getenv("OPENWEATHER_API_KEY", "")

        # If no API key, force demo mode
        if not api_key:
            demo_mode = True

        self.demo_mode = demo_mode
        self.weather_agent = WeatherAgent(
            api_key=api_key,
            demo_mode=demo_mode
        )
        self.geo_agent = GeoAgent(demo_mode=demo_mode)

    def compute_risk(
        self,
        zone_name: str,
        lat: float = 19.076,
        lon: float = 72.877,
        visual_score: float = 0.0,
        visual_confidence: float = 0.0,
        disaster_type: str = "flood"
    ) -> dict:
        """
        Master risk computation combining ALL data sources.
        
        Parameters:
        -----------
        zone_name: str
            Mumbai zone/area name (e.g., "Dadar", "Hindmata")
        lat, lon: float
            GPS coordinates
        visual_score: float (0-100)
            Score from vision agent. Typically confidence * 100.
        visual_confidence: float (0-1)
            Raw confidence from Gemini
        disaster_type: str
            Currently "flood" (expandable to landslide, fire later)
        
        Returns:
        --------
        dict with:
            - composite_risk_score (0-100)
            - overall_risk_level (CRITICAL/HIGH/MODERATE/LOW/MINIMAL)
            - recommended_action
            - factor_breakdown (detailed scores per factor)
            - explanation (human-readable text)
            - data_quality (how many sources succeeded)
        """
        factors = {}
        errors = []
        weights = self.FLOOD_WEIGHTS

        # ─── Factor 1: Visual Detection ──────────
        factors["visual"] = {
            "score": round(visual_score, 2),
            "confidence": round(visual_confidence, 2),
            "weight": weights["visual"],
            "source": "Google Gemini 2.5 Flash",
            "description": self._describe_visual(visual_score)
        }

        # ─── Factor 2: Weather Conditions ────────
        try:
            weather_risk = self.weather_agent.compute_weather_risk(zone_name)
            factors["weather"] = {
                "score": weather_risk["composite_score"],
                "weight": weights["weather"],
                "source": weather_risk["raw_data"].get("source", "OpenWeatherMap"),
                "details": weather_risk["factors"],
                "raw": {
                    "rainfall_mm": weather_risk["raw_data"]["rainfall_1h_mm"],
                    "humidity_pct": weather_risk["raw_data"]["humidity_pct"],
                    "pressure_hpa": weather_risk["raw_data"]["pressure_hpa"],
                    "wind_speed_ms": weather_risk["raw_data"]["wind_speed_ms"],
                    "condition": weather_risk["raw_data"]["condition"],
                },
                "description": self._describe_weather(weather_risk)
            }
        except Exception as e:
            factors["weather"] = {
                "score": 0,
                "weight": weights["weather"],
                "source": "ERROR",
                "error": str(e),
                "description": f"Weather data unavailable: {e}"
            }
            errors.append(f"Weather: {e}")

        # ─── Factor 3: Geological Conditions ─────
        try:
            geo_risk = self.geo_agent.compute_full_geo_risk(zone_name, lat, lon)
            soil_data = geo_risk["factors"]["soil_saturation"]
            seismic_data = geo_risk["factors"]["seismic_activity"]

            factors["geological"] = {
                "score": geo_risk["composite_score"],
                "weight": weights["geological"],
                "source": "Open-Meteo + USGS",
                "details": {
                    "soil_moisture": soil_data["moisture_value"],
                    "soil_status": soil_data["status"],
                    "soil_score": soil_data["score"],
                    "seismic_events": seismic_data["event_count"],
                    "max_magnitude": seismic_data["max_magnitude"],
                    "seismic_score": seismic_data["score"],
                },
                "description": self._describe_geo(geo_risk)
            }
        except Exception as e:
            factors["geological"] = {
                "score": 0,
                "weight": weights["geological"],
                "source": "ERROR",
                "error": str(e),
                "description": f"Geological data unavailable: {e}"
            }
            errors.append(f"Geological: {e}")

        # ─── Factor 4: Historical Risk ───────────
        try:
            historical = self.geo_agent.get_historical_flood_risk(zone_name)
            factors["historical"] = {
                "score": historical["score"],
                "weight": weights["historical"],
                "source": "BMC Historical Flood Records",
                "known_flood_zone": historical["known_flood_zone"],
                "description": self._describe_historical(historical, zone_name)
            }
        except Exception as e:
            factors["historical"] = {
                "score": 30,  # Default moderate risk
                "weight": weights["historical"],
                "source": "DEFAULT",
                "error": str(e),
                "description": "Historical data unavailable, using default."
            }
            errors.append(f"Historical: {e}")

        # ─── Factor 5: Forecast (Incoming Rain) ──
        try:
            forecast_alert = self.weather_agent.get_incoming_rain_alert(zone_name)
            
            if forecast_alert["alert_triggered"]:
                hours = forecast_alert["hours_until_heavy_rain"]
                peak = forecast_alert["peak_rainfall_mm"]

                if hours <= 3:
                    forecast_score = 90
                elif hours <= 6:
                    forecast_score = 70
                elif hours <= 12:
                    forecast_score = 50
                else:
                    forecast_score = 30
            else:
                peak_rain = forecast_alert.get("peak_rainfall_mm", 0)
                forecast_score = min(25, peak_rain)

            factors["forecast"] = {
                "score": round(forecast_score, 2),
                "weight": weights["forecast"],
                "source": factors["weather"].get("source", "OpenWeatherMap"),
                "alert_triggered": forecast_alert["alert_triggered"],
                "details": forecast_alert,
                "description": self._describe_forecast(forecast_alert)
            }
        except Exception as e:
            factors["forecast"] = {
                "score": 0,
                "weight": weights["forecast"],
                "source": "ERROR",
                "error": str(e),
                "description": f"Forecast unavailable: {e}"
            }
            errors.append(f"Forecast: {e}")

        # ─── Compute Weighted Composite ──────────
        composite_score = 0
        weight_sum = 0

        for factor_name, weight in weights.items():
            factor_data = factors.get(factor_name, {})
            score = factor_data.get("score", 0)

            # Only count factors that didn't error
            if "error" not in factor_data:
                composite_score += score * weight
                weight_sum += weight
            else:
                # Still add with reduced confidence
                composite_score += score * weight * 0.5
                weight_sum += weight * 0.5

        # Normalize if some factors had errors
        if weight_sum > 0 and weight_sum < 0.95:
            composite_score = composite_score / weight_sum

        composite_score = round(min(100, max(0, composite_score)), 2)

        # ─── Determine Risk Level ────────────────
        if composite_score >= 80:
            risk_level = "CRITICAL"
            action = "IMMEDIATE_EVACUATION"
            color = "red"
            emoji = "🔴"
        elif composite_score >= 60:
            risk_level = "HIGH"
            action = "ALERT_AND_PREPARE"
            color = "orange"
            emoji = "🟠"
        elif composite_score >= 40:
            risk_level = "MODERATE"
            action = "MONITOR_CLOSELY"
            color = "yellow"
            emoji = "🟡"
        elif composite_score >= 20:
            risk_level = "LOW"
            action = "ROUTINE_MONITORING"
            color = "green"
            emoji = "🟢"
        else:
            risk_level = "MINIMAL"
            action = "NO_ACTION_NEEDED"
            color = "blue"
            emoji = "🔵"

        # ─── Generate Explanation ────────────────
        explanation = self._build_explanation(
            factors, weights, composite_score,
            risk_level, zone_name
        )

        return {
            "zone": zone_name,
            "disaster_type": disaster_type,
            "composite_risk_score": composite_score,
            "overall_risk_level": risk_level,
            "recommended_action": action,
            "display_color": color,
            "emoji": emoji,
            "factor_breakdown": factors,
            "weights_used": weights,
            "explanation": explanation,
            "data_quality": {
                "total_factors": len(weights),
                "successful": len(weights) - len(errors),
                "errored": len(errors),
                "errors": errors,
                "demo_mode": self.demo_mode
            },
            "timestamp": datetime.now().isoformat()
        }

    # ─────────────────────────────────────────────
    # DESCRIPTION GENERATORS
    # ─────────────────────────────────────────────

    def _describe_visual(self, score: float) -> str:
        if score >= 80:
            return "Camera clearly shows flooding/water accumulation."
        elif score >= 50:
            return "Camera shows possible water/flooding indicators."
        elif score >= 20:
            return "Camera shows minor water presence."
        elif score > 0:
            return "Camera shows minimal visual indicators."
        else:
            return "No flood indicators detected visually."

    def _describe_weather(self, weather_risk: dict) -> str:
        rainfall = weather_risk["raw_data"]["rainfall_1h_mm"]
        humidity = weather_risk["raw_data"]["humidity_pct"]
        condition = weather_risk["raw_data"]["condition"]

        if rainfall > 65:
            return f"EXTREMELY HEAVY rain: {rainfall}mm/hr. {condition}. Humidity {humidity}%."
        elif rainfall > 35:
            return f"HEAVY rain: {rainfall}mm/hr. {condition}. Humidity {humidity}%."
        elif rainfall > 15:
            return f"Moderate rain: {rainfall}mm/hr. {condition}. Humidity {humidity}%."
        elif rainfall > 0:
            return f"Light rain: {rainfall}mm/hr. {condition}. Humidity {humidity}%."
        else:
            return f"No rainfall currently. {condition}. Humidity {humidity}%."

    def _describe_geo(self, geo_risk: dict) -> str:
        soil = geo_risk["factors"]["soil_saturation"]
        seismic = geo_risk["factors"]["seismic_activity"]

        soil_desc = f"Soil {soil['status'].lower()} (moisture: {soil['moisture_value']:.2f})."
        
        if seismic["event_count"] > 0:
            seismic_desc = (
                f" {seismic['event_count']} seismic events detected "
                f"(max M{seismic['max_magnitude']})."
            )
        else:
            seismic_desc = " No seismic activity."

        return soil_desc + seismic_desc

    def _describe_historical(self, historical: dict, zone_name: str) -> str:
        if historical["known_flood_zone"]:
            return f"{zone_name} is a KNOWN flood-prone area (BMC records). Base risk: {historical['score']}/100."
        else:
            return f"{zone_name} has moderate historical flood risk. Base risk: {historical['score']}/100."

    def _describe_forecast(self, forecast_alert: dict) -> str:
        if forecast_alert["alert_triggered"]:
            hours = forecast_alert["hours_until_heavy_rain"]
            peak = forecast_alert["peak_rainfall_mm"]
            return f"⚠️ Heavy rain ({peak}mm) expected in {hours} hours!"
        else:
            peak = forecast_alert.get("peak_rainfall_mm", 0)
            return f"No heavy rain expected in next 24 hours. Max forecast: {peak}mm."

    def _build_explanation(self, factors: dict, weights: dict,
                            composite: float, risk_level: str,
                            zone_name: str) -> str:
        """Generate complete human-readable explanation."""
        lines = []
        lines.append(f"MULTI-FACTOR FLOOD RISK ASSESSMENT — {zone_name}")
        lines.append("=" * 50)
        lines.append("")

        # Sort factors by contribution (weight * score) descending
        sorted_factors = sorted(
            weights.items(),
            key=lambda x: factors.get(x[0], {}).get("score", 0) * x[1],
            reverse=True
        )

        for factor_name, weight in sorted_factors:
            factor_data = factors.get(factor_name, {})
            score = factor_data.get("score", 0)
            contribution = score * weight
            source = factor_data.get("source", "Unknown")
            description = factor_data.get("description", "")

            bar_filled = int(score / 5)
            bar_empty = 20 - bar_filled
            bar = "█" * bar_filled + "░" * bar_empty

            lines.append(
                f"  {factor_name.upper():12s} {bar} {score:5.1f}/100 "
                f"(×{weight:.0%} = {contribution:5.1f})"
            )
            lines.append(f"               Source: {source}")
            lines.append(f"               {description}")
            lines.append("")

        lines.append("-" * 50)
        lines.append(f"  COMPOSITE SCORE: {composite:.1f}/100")
        lines.append(f"  RISK LEVEL:      {risk_level}")
        lines.append("-" * 50)

        # Add interpretation
        lines.append("")
        if composite >= 60:
            lines.append(
                f"⚠️ Multiple independent data sources confirm elevated "
                f"flood risk in {zone_name}. This is NOT based on a single "
                f"factor — {sum(1 for f in factors.values() if f.get('score', 0) > 40)} "
                f"out of {len(factors)} factors show concerning levels."
            )
        elif composite >= 40:
            lines.append(
                f"📊 Some risk indicators are elevated for {zone_name}, "
                f"but not all factors corroborate. Continued monitoring recommended."
            )
        else:
            lines.append(
                f"✅ Risk indicators for {zone_name} are within normal range. "
                f"No immediate flood threat detected across any data source."
            )

        return "\n".join(lines)


# ─────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────
if __name__ == "__main__":

    print("=" * 60)
    print("MULTI-FACTOR RISK ENGINE — STANDALONE TEST")
    print("=" * 60)

    engine = MultiFactorRiskEngine(demo_mode=True)

    # ── Test 1: Flood image detected at Hindmata ────────
    print("\n" + "=" * 60)
    print("TEST 1: Flood detected at Hindmata (HIGH RISK area)")
    print("=" * 60)

    result = engine.compute_risk(
        zone_name="Hindmata",
        lat=19.0145,
        lon=72.8510,
        visual_score=85.0,
        visual_confidence=0.85,
        disaster_type="flood"
    )

    print(f"\n{result['emoji']} Composite Score: {result['composite_risk_score']}/100")
    print(f"   Risk Level:      {result['overall_risk_level']}")
    print(f"   Action:          {result['recommended_action']}")
    print(f"   Demo Mode:       {result['data_quality']['demo_mode']}")
    print(f"   Factors OK:      {result['data_quality']['successful']}/{result['data_quality']['total_factors']}")

    print("\n" + result["explanation"])

    # ── Test 2: No hazard detected at Colaba ────────────
    print("\n" + "=" * 60)
    print("TEST 2: No hazard detected at Colaba (LOWER RISK)")
    print("=" * 60)

    result2 = engine.compute_risk(
        zone_name="Colaba",
        lat=18.9067,
        lon=72.8147,
        visual_score=0.0,
        visual_confidence=0.0,
        disaster_type="flood"
    )

    print(f"\n{result2['emoji']} Composite Score: {result2['composite_risk_score']}/100")
    print(f"   Risk Level:      {result2['overall_risk_level']}")
    print(f"   Action:          {result2['recommended_action']}")

    print("\n" + result2["explanation"])

    # ── Test 3: Medium confidence at Dadar ──────────────
    print("\n" + "=" * 60)
    print("TEST 3: Medium confidence detection at Dadar")
    print("=" * 60)

    result3 = engine.compute_risk(
        zone_name="Dadar",
        lat=19.0178,
        lon=72.8478,
        visual_score=55.0,
        visual_confidence=0.55,
        disaster_type="flood"
    )

    print(f"\n{result3['emoji']} Composite Score: {result3['composite_risk_score']}/100")
    print(f"   Risk Level:      {result3['overall_risk_level']}")
    print(f"   Action:          {result3['recommended_action']}")

    print("\nFactor Scores Summary:")
    print("-" * 40)
    for name, data in result3["factor_breakdown"].items():
        score = data.get("score", 0)
        weight = data.get("weight", 0)
        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        print(f"  {name:12s} {bar} {score:5.1f}/100 (weight: {weight:.0%})")