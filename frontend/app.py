import streamlit as st
from PIL import Image
from datetime import datetime
import folium
from streamlit_folium import st_folium
import tempfile
import os
import sys
import json
import requests

# Fix import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.pipeline.graph import app as nivaran_graph
from backend.database.incident_store import save_incident, get_all_incidents

# ---------------- Page config ----------------
st.set_page_config(
    page_title="Nivaran - Dashboard",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
    <style>
    html { overflow-y: scroll; }
    body, .main, .block-container { overflow-x: hidden !important; }
    iframe { border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Nivaran: Disaster Response Dashboard")
st.caption("Multi-factor flood detection, NDMA protocol retrieval, and multilingual alert generation.")

# ---------------- Session state ----------------
def ss_init(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

ss_init("result", None)
ss_init("approval_status", "PENDING")
ss_init("incidents", [])
ss_init("location_text", "")
ss_init("lat", 19.0760)
ss_init("lon", 72.8777)
ss_init("alert_en", "")
ss_init("alert_hi", "")
ss_init("alert_mr", "")
ss_init("tweet_public", "")
ss_init("tweet_authority", "")
ss_init("map_expanded", False)
ss_init("uploader_key", 1)
ss_init("uploaded_once", False)
ss_init("current_file", None)
ss_init("current_file_kind", None)
ss_init("map_center_lat", 19.0760)
ss_init("map_center_lon", 72.8777)
ss_init("last_search_name", "")
ss_init("last_search_lat", None)
ss_init("last_search_lon", None)
ss_init("last_search_address", "")
ss_init("demo_mode", True)

# Load persistent incidents from DB on first load
if not st.session_state.incidents:
    st.session_state.incidents = get_all_incidents()

# ---------------- Helpers ----------------
def severity_badge(severity: str) -> str:
    sev = (severity or "").strip().lower()
    if sev == "high":   return "🔴 HIGH"
    if sev == "medium": return "🟠 MEDIUM"
    if sev == "low":    return "🟢 LOW"
    return "—"

def risk_badge(risk_level: str) -> str:
    level = (risk_level or "").strip().upper()
    if level == "CRITICAL": return "🔴 CRITICAL"
    if level == "HIGH":     return "🟠 HIGH"
    if level == "MODERATE": return "🟡 MODERATE"
    if level == "LOW":      return "🟢 LOW"
    if level == "MINIMAL":  return "🔵 MINIMAL"
    return "⚪ UNKNOWN"

def risk_color(risk_level: str) -> str:
    level = (risk_level or "").strip().upper()
    if level == "CRITICAL": return "#E74C3C"
    if level == "HIGH":     return "#E67E22"
    if level == "MODERATE": return "#F1C40F"
    if level == "LOW":      return "#27AE60"
    if level == "MINIMAL":  return "#3498DB"
    return "#95A5A6"

def count_by_type(incidents, disaster_type):
    return sum(1 for i in incidents if i.get("type") == disaster_type)

def count_by_severity(incidents, severity):
    return sum(1 for i in incidents if str(i.get("severity", "")).lower() == severity.lower())

def get_marker_color(disaster_type):
    if disaster_type == "Flood":     return "blue"
    if disaster_type == "Landslide": return "darkred"
    if disaster_type == "Fire":      return "red"
    return "gray"

def _incidents_hashable(incidents_list):
    return tuple(tuple(sorted(
        (k, str(v)) for k, v in i.items()
    )) for i in incidents_list)

def _guess_kind_and_suffix(uploaded_file):
    name = (uploaded_file.name or "").lower()
    if name.endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
        return "video", os.path.splitext(name)[1] or ".mp4"
    return "image", os.path.splitext(name)[1] or ".jpg"

# ---------------- Geocoding ----------------
@st.cache_data(show_spinner=False)
def geocode_place(place_name: str):
    place_name = (place_name or "").strip()
    if not place_name:
        return None, None, ""
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": place_name, "format": "json", "limit": 1},
        headers={"User-Agent": "Nivaran-Dashboard/1.0"},
        timeout=12
    )
    r.raise_for_status()
    data = r.json()
    if not data:
        return None, None, ""
    return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", "")

# ---------------- Map builder ----------------
@st.cache_data(show_spinner=False)
def build_map_cached(incidents_hashable, center_lat, center_lon, zoom=11, searched_marker=None):
    incidents = [dict(t) for t in incidents_hashable]
    m = folium.Map(location=[float(center_lat), float(center_lon)], zoom_start=zoom)

    if searched_marker and searched_marker.get("lat") is not None:
        folium.Marker(
            location=[searched_marker["lat"], searched_marker["lon"]],
            popup=f"<b>{searched_marker.get('name','')}</b><br>{searched_marker.get('address','')}",
            tooltip="Searched Location",
            icon=folium.Icon(color="green", icon="info-sign"),
        ).add_to(m)

    for incident in incidents:
        if incident.get("lat") is None or incident.get("lon") is None:
            continue
        folium.Marker(
            location=[incident["lat"], incident["lon"]],
            popup=f"<b>{incident.get('id')}</b><br>{incident.get('type')} | {incident.get('severity')}<br>{incident.get('location')}",
            tooltip=incident.get("type"),
            icon=folium.Icon(color=get_marker_color(incident.get("type")))
        ).add_to(m)
    return m

# ---------------- Pipeline ----------------
def run_pipeline(uploaded_file, kind: str, location_text: str,
                 lat: float = 19.076, lon: float = 72.877,
                 demo_mode: bool = True) -> dict:
    temp_path = "temp_upload.jpg"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    zone_name = location_text if location_text else "Dadar"

    result = nivaran_graph.invoke({
        "image_path": temp_path,
        "zone_name": zone_name,
        "lat": lat,
        "lon": lon,
        "demo_mode": demo_mode
    })

    vision = result["vision_output"]
    risk = result.get("multi_factor_risk", {})

    return {
        "detected":            "YES" if vision.get("hazard") else "NO",
        "type":                vision.get("type", "unknown").capitalize(),
        "severity":            vision.get("severity", "unknown").capitalize(),
        "confidence":          vision.get("confidence", 0.0),
        "location":            location_text or "Unknown",
        "lat":                 lat,
        "lon":                 lon,
        "protocol":            result.get("protocol", ""),
        "alert_en":            result.get("alert_en", ""),
        "alert_hi":            result.get("alert_hi", ""),
        "alert_mr":            result.get("alert_mr", ""),
        "tweet_public":        result.get("tweet_public", ""),
        "tweet_authority":     result.get("tweet_authority", ""),
        "media_kind":          kind,
        "media_name":          getattr(uploaded_file, "name", "unknown"),
        "multi_factor_risk":   risk,
        "composite_score":     risk.get("composite_risk_score", 0),
        "risk_level":          risk.get("overall_risk_level", "UNKNOWN"),
        "factor_breakdown":    risk.get("factor_breakdown", {}),
        "risk_explanation":    risk.get("explanation", ""),
        "data_quality":        risk.get("data_quality", {}),
    }

# ---------------- KPI Row ----------------
incidents = st.session_state.incidents
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📌 Total Incidents",  len(incidents))
c2.metric("🌧️ Flood",           count_by_type(incidents, "Flood"))
c3.metric("⛰️ Landslide",        count_by_type(incidents, "Landslide"))
c4.metric("🔥 Fire",             count_by_type(incidents, "Fire"))
c5.metric("🔴 High Severity",    count_by_severity(incidents, "High"))

st.divider()

# ---------------- Sidebar ----------------
st.sidebar.header("📍 Incident Details")

st.session_state.location_text = st.sidebar.text_input(
    "Enter location name",
    value=st.session_state.location_text
)

colA, colB = st.sidebar.columns(2)
search_btn      = colA.button("🔎 Search Location", use_container_width=True)
clear_search_btn = colB.button("🧽 Clear", use_container_width=True)

if clear_search_btn:
    st.session_state.last_search_name    = ""
    st.session_state.last_search_lat     = None
    st.session_state.last_search_lon     = None
    st.session_state.last_search_address = ""
    st.session_state.map_center_lat      = st.session_state.lat
    st.session_state.map_center_lon      = st.session_state.lon

if search_btn:
    query = st.session_state.location_text.strip()
    if not query:
        st.sidebar.warning("Please type a location name first.")
    else:
        try:
            with st.sidebar.spinner("Searching..."):
                lat, lon, display_name = geocode_place(query)
            if lat is None:
                st.sidebar.error("Location not found.")
            else:
                st.session_state.lat = lat
                st.session_state.lon = lon
                st.session_state.map_center_lat      = lat
                st.session_state.map_center_lon      = lon
                st.session_state.last_search_name    = query
                st.session_state.last_search_lat     = lat
                st.session_state.last_search_lon     = lon
                st.session_state.last_search_address = display_name
                st.sidebar.success("Location found ✅")
        except Exception as e:
            st.sidebar.error(f"Geocoding failed: {e}")

st.sidebar.subheader("📌 Coordinates")
st.session_state.lat = st.sidebar.number_input("Latitude",  value=float(st.session_state.lat),  format="%.6f")
st.session_state.lon = st.sidebar.number_input("Longitude", value=float(st.session_state.lon), format="%.6f")
st.session_state.map_center_lat = float(st.session_state.lat)
st.session_state.map_center_lon = float(st.session_state.lon)

if st.session_state.last_search_lat:
    st.sidebar.caption(f"✅ {st.session_state.last_search_name}")
    st.sidebar.caption(st.session_state.last_search_address[:80])

st.sidebar.subheader("🌐 Preferred Alert Language")
preferred_lang = st.sidebar.radio("Select language", ["English", "Hindi", "Marathi"], index=0)

# ── Demo Mode Toggle (NEW) ──────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Data Source Mode")
st.session_state.demo_mode = st.sidebar.toggle(
    "🌧️ Monsoon Simulation Mode",
    value=st.session_state.demo_mode,
    help=(
        "ON = Simulated monsoon conditions (heavy rain, saturated soil). "
        "Use this for demos.\n\n"
        "OFF = Real-time API data from OpenWeatherMap and Open-Meteo. "
        "Shows actual current weather."
    )
)

if st.session_state.demo_mode:
    st.sidebar.info("🌧️ Using simulated monsoon data")
else:
    st.sidebar.success("🌐 Using LIVE weather and soil data")

# Sidebar map
st.sidebar.markdown("---")
with st.sidebar.expander("🗺️ Live Map View", expanded=True):
    searched_marker = None
    if st.session_state.last_search_lat:
        searched_marker = {
            "name": st.session_state.last_search_name,
            "lat":  st.session_state.last_search_lat,
            "lon":  st.session_state.last_search_lon,
            "address": st.session_state.last_search_address,
        }
    inc_hash  = _incidents_hashable(st.session_state.incidents)
    small_map = build_map_cached(
        inc_hash,
        st.session_state.map_center_lat,
        st.session_state.map_center_lon,
        zoom=13 if searched_marker else 11,
        searched_marker=searched_marker
    )
    st_folium(small_map, width=320, height=220, key="sidebar_map_static")

# ---------------- File uploader ----------------
uploaded_file = None
if not st.session_state.uploaded_once:
    uploaded_file = st.file_uploader(
        "Upload a CCTV/Drone/Public image OR video",
        type=["jpg", "jpeg", "png", "mp4", "mov", "mkv", "avi", "webm"],
        key=f"uploader_{st.session_state.uploader_key}",
    )
    if uploaded_file is not None:
        kind, _ = _guess_kind_and_suffix(uploaded_file)
        st.session_state.uploaded_once    = True
        st.session_state.current_file     = uploaded_file
        st.session_state.current_file_kind = kind
        st.rerun()
else:
    uploaded_file = st.session_state.current_file

left, right = st.columns([1, 1])

# ---------------- LEFT: Media preview ----------------
with left:
    st.subheader("📎 Uploaded Media")
    if uploaded_file is None:
        st.info("No media uploaded yet.")
    else:
        kind = st.session_state.current_file_kind or _guess_kind_and_suffix(uploaded_file)[0]
        if kind == "video":
            st.video(uploaded_file)
        else:
            st.image(Image.open(uploaded_file), caption="Image received ✅", use_container_width=True)

        if st.button("📤 Analyze different image/video", use_container_width=True):
            st.session_state.result            = None
            st.session_state.approval_status   = "PENDING"
            st.session_state.uploaded_once     = False
            st.session_state.current_file      = None
            st.session_state.current_file_kind = None
            st.session_state.uploader_key     += 1
            st.rerun()

# ---------------- RIGHT: AI Output ----------------
with right:
    st.subheader("🤖 AI Output")

    b1, b2 = st.columns(2)
    analyze_btn = b1.button("🚀 Analyze")
    reset_btn   = b2.button("🧹 Reset")

    if reset_btn:
        st.session_state.result          = None
        st.session_state.approval_status = "PENDING"
        st.success("Cleared ✅")

    if analyze_btn and uploaded_file is None:
        st.warning("Please upload an image or video first.")

    if analyze_btn and uploaded_file is not None:
        st.session_state.approval_status = "PENDING"
        with st.spinner("AI Agents are analyzing (Vision + Weather + Soil + Seismic)..."):
            kind   = st.session_state.current_file_kind or _guess_kind_and_suffix(uploaded_file)[0]
            result = run_pipeline(
                uploaded_file,
                kind,
                st.session_state.location_text,
                lat=float(st.session_state.lat),
                lon=float(st.session_state.lon),
                demo_mode=st.session_state.demo_mode
            )
            st.session_state.result          = result
            st.session_state.alert_en        = result.get("alert_en", "")
            st.session_state.alert_hi        = result.get("alert_hi", "")
            st.session_state.alert_mr        = result.get("alert_mr", "")
            st.session_state.tweet_public    = result.get("tweet_public", "")
            st.session_state.tweet_authority = result.get("tweet_authority", "")

            incident = {
                "id":        f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "time":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "location":  result.get("location", "Unknown"),
                "lat":       float(st.session_state.lat),
                "lon":       float(st.session_state.lon),
                **result
            }

            save_incident(incident)
            st.session_state.incidents = get_all_incidents()

    result = st.session_state.result

    tab_analysis, tab_all = st.tabs(["🔍 Current Analysis", "📋 All Incidents"])

    with tab_analysis:
        if result is None:
            st.info("Upload an image and click Analyze to begin.")
        else:
            # ── Detection Metrics ────────────────────
            st.markdown("### 📷 Visual Detection")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Detected", result.get("detected", "—"))
            c2.metric("Type", result.get("type", "—"))
            c3.metric("Severity", severity_badge(result.get("severity", "—")))
            c4.metric("Confidence", f"{float(result.get('confidence', 0))*100:.0f}%")

            st.write(f"**📍 Location:** {result.get('location', 'Unknown')}")
            st.write(f"**🧭 Coordinates:** {result.get('lat', '—')}, {result.get('lon', '—')}")

            # ══════════════════════════════════════════
            # MULTI-FACTOR RISK BREAKDOWN (NEW SECTION)
            # ══════════════════════════════════════════
            st.markdown("---")
            st.markdown("### 🧠 Multi-Factor Risk Assessment")

            composite = result.get("composite_score", 0)
            r_level = result.get("risk_level", "UNKNOWN")
            factors = result.get("factor_breakdown", {})
            data_quality = result.get("data_quality", {})

            # ── Big composite score display ──────────
            score_col1, score_col2, score_col3 = st.columns([1, 1, 1])

            with score_col1:
                st.metric(
                    "Composite Flood Risk",
                    f"{composite:.1f}/100",
                    delta=None
                )

            with score_col2:
                st.metric(
                    "Risk Level",
                    risk_badge(r_level)
                )

            with score_col3:
                demo_label = "🌧️ Simulated" if data_quality.get("demo_mode") else "🌐 Live Data"
                sources_ok = data_quality.get("successful", 0)
                total_sources = data_quality.get("total_factors", 0)
                st.metric(
                    "Data Sources",
                    f"{sources_ok}/{total_sources} Active",
                    delta=demo_label
                )

            # ── Progress bar for composite score ─────
            st.progress(
                min(1.0, composite / 100),
                text=f"Composite Risk: {composite:.1f}% — {r_level}"
            )

            # ── Individual factor bars ───────────────
            if factors:
                st.markdown("#### Factor Breakdown")

                # Define display config for each factor
                factor_config = {
                    "visual": {
                        "icon": "📷",
                        "label": "Visual Detection",
                        "help": "AI camera analysis (Gemini 2.5 Flash)"
                    },
                    "weather": {
                        "icon": "🌧️",
                        "label": "Weather Conditions",
                        "help": "Rainfall, humidity, pressure, wind"
                    },
                    "geological": {
                        "icon": "🌍",
                        "label": "Ground Conditions",
                        "help": "Soil moisture and seismic activity"
                    },
                    "historical": {
                        "icon": "📜",
                        "label": "Historical Risk",
                        "help": "BMC flood records for this zone"
                    },
                    "forecast": {
                        "icon": "📅",
                        "label": "Rain Forecast",
                        "help": "Incoming rainfall prediction"
                    },
                }

                for factor_key, config in factor_config.items():
                    factor_data = factors.get(factor_key, {})
                    score = factor_data.get("score", 0)
                    weight = factor_data.get("weight", 0)
                    source = factor_data.get("source", "Unknown")
                    description = factor_data.get("description", "")
                    has_error = "error" in factor_data

                    # Factor row
                    f_col1, f_col2, f_col3 = st.columns([2, 3, 1])

                    with f_col1:
                        st.markdown(
                            f"**{config['icon']} {config['label']}**"
                        )
                        st.caption(f"Weight: {weight:.0%} | Source: {source}")

                    with f_col2:
                        if has_error:
                            st.warning(f"⚠️ {factor_data.get('error', 'Unavailable')}")
                        else:
                            st.progress(
                                min(1.0, score / 100),
                                text=f"{score:.0f}/100"
                            )

                    with f_col3:
                        contribution = score * weight
                        st.markdown(f"**+{contribution:.1f}**")

                    # Show description in a subtle way
                    if description and not has_error:
                        st.caption(f"   ↳ {description}")

                # ── Weather details expander ─────────
                weather_factor = factors.get("weather", {})
                weather_raw = weather_factor.get("raw", {})

                if weather_raw:
                    with st.expander("🌧️ Detailed Weather Data"):
                        w1, w2, w3, w4 = st.columns(4)
                        w1.metric(
                            "💧 Rainfall",
                            f"{weather_raw.get('rainfall_mm', 0)} mm/hr"
                        )
                        w2.metric(
                            "💦 Humidity",
                            f"{weather_raw.get('humidity_pct', 0)}%"
                        )
                        w3.metric(
                            "🌡️ Pressure",
                            f"{weather_raw.get('pressure_hpa', 0)} hPa"
                        )
                        w4.metric(
                            "💨 Wind",
                            f"{weather_raw.get('wind_speed_ms', 0)} m/s"
                        )
                        st.caption(
                            f"Condition: {weather_raw.get('condition', 'N/A')}"
                        )

                # ── Geo details expander ─────────────
                geo_factor = factors.get("geological", {})
                geo_details = geo_factor.get("details", {})

                if geo_details:
                    with st.expander("🌍 Detailed Ground Data"):
                        g1, g2, g3 = st.columns(3)
                        g1.metric(
                            "💧 Soil Moisture",
                            f"{geo_details.get('soil_moisture', 0):.3f}"
                        )
                        g2.metric(
                            "Soil Status",
                            geo_details.get("soil_status", "N/A")
                        )
                        g3.metric(
                            "🔴 Seismic Events",
                            f"{geo_details.get('seismic_events', 0)} "
                            f"(Max M{geo_details.get('max_magnitude', 0)})"
                        )

            # ── Risk explanation expander ────────────
            explanation = result.get("risk_explanation", "")
            if explanation:
                with st.expander("📊 Full Risk Explanation"):
                    st.code(explanation, language=None)

            # ══════════════════════════════════════════
            # END OF MULTI-FACTOR SECTION
            # ══════════════════════════════════════════

            st.markdown("---")

            # ── Approval Status ──────────────────────
            status = st.session_state.approval_status
            if status == "PENDING":   st.warning("🟡 Approval Status: PENDING")
            elif status == "APPROVED": st.success("🟢 Approval Status: APPROVED")
            else:                      st.error("🔴 Approval Status: REJECTED")

            # ── NDMA Protocol ────────────────────────
            st.markdown("### 📘 NDMA Protocol")
            protocol_text = result.get("protocol", "—")
            if protocol_text and protocol_text != "—":
                st.success(protocol_text)
            else:
                st.info("No protocol retrieved (risk below threshold or no hazard detected).")

            # ── Alert (Selected Language) ────────────
            st.markdown("### 🌐 Alert (Selected Language)")
            if preferred_lang == "English":
                chosen_alert = st.text_area(
                    "Alert (English)",
                    value=st.session_state.alert_en,
                    height=120, key="en_current"
                )
            elif preferred_lang == "Hindi":
                chosen_alert = st.text_area(
                    "Alert (Hindi)",
                    value=st.session_state.alert_hi,
                    height=120, key="hi_current"
                )
            else:
                chosen_alert = st.text_area(
                    "Alert (Marathi)",
                    value=st.session_state.alert_mr,
                    height=120, key="mr_current"
                )

            # ── Human-in-the-Loop Approval ───────────
            st.markdown("### ✅ Human-in-the-Loop Approval")
            a1, a2 = st.columns(2)
            if a1.button("✅ Approve", key="appr_current"):
                st.session_state.approval_status = "APPROVED"
                st.rerun()
            if a2.button("❌ Reject",  key="rej_current"):
                st.session_state.approval_status = "REJECTED"
                st.rerun()

            # ── Tweet Drafts ─────────────────────────
            st.markdown("### 🐦 Tweet Drafts")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**👥 Public Tweet**")
                pub = st.text_area(
                    "Public",
                    value=st.session_state.tweet_public,
                    height=140, key="pub_current"
                )
                st.caption(f"{len(pub)}/280")
                if len(pub) <= 280:
                    st.success("✅ Ready to post")
                else:
                    st.error("Too long! Shorten it.")

            with col2:
                st.markdown("**🚨 Authority Tweet**")
                auth = st.text_area(
                    "Authority",
                    value=st.session_state.tweet_authority,
                    height=140, key="auth_current"
                )
                st.caption(f"{len(auth)}/280")
                if len(auth) <= 280:
                    st.success("✅ Ready to post")
                else:
                    st.error("Too long! Shorten it.")

            # ── PDF Export ───────────────────────────
            st.markdown("### 📄 Export Report")
            if st.button("📥 Generate PDF Report", key="pdf_current"):
                with st.spinner("Generating PDF..."):
                    try:
                        from backend.utils.report_generator import generate_report
                        out_path = generate_report(result)
                        if out_path and os.path.exists(out_path):
                            with open(out_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download Report",
                                    data=f,
                                    file_name=os.path.basename(out_path),
                                    mime="application/pdf",
                                    key="dl_current"
                                )
                        else:
                            st.error("PDF generation failed.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── All Incidents Tab ────────────────────────
    with tab_all:
        st.subheader("📋 Incident Log")
        if not st.session_state.incidents:
            st.info("No incidents yet.")
        else:
            options = [
                f"{i['id']} | {i.get('time') or i.get('timestamp','')} | "
                f"{i.get('location','Unknown')} | {i.get('type','')} | "
                f"{i.get('severity','')} | Risk: {i.get('composite_risk_score', 0):.0f}"
                for i in st.session_state.incidents
            ]
            selected    = st.selectbox("Select an incident:", options)
            selected_id = selected.split("|")[0].strip()
            chosen      = next(
                (i for i in st.session_state.incidents if i["id"] == selected_id),
                None
            )

            if chosen:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Type", chosen.get("type", "—"))
                c2.metric("Severity", severity_badge(chosen.get("severity", "—")))
                c3.metric("Confidence", f"{float(chosen.get('confidence', 0))*100:.0f}%")
                c4.metric("Risk Score", f"{float(chosen.get('composite_risk_score', 0)):.0f}/100")

                st.write(f"**📍 Location:** {chosen.get('location', 'Unknown')}")
                st.write(f"**🧭 Coordinates:** {chosen.get('lat', '—')}, {chosen.get('lon', '—')}")
                st.write(f"**🕒 Time:** {chosen.get('time') or chosen.get('timestamp', '—')}")
                st.write(f"**🎯 Risk Level:** {risk_badge(chosen.get('risk_level', 'UNKNOWN'))}")

                # Show weather and geo data if available
                weather_data = chosen.get("weather_data", {})
                geo_data = chosen.get("geo_data", {})

                if weather_data and isinstance(weather_data, dict) and weather_data:
                    with st.expander("🌧️ Weather Data at Time of Incident"):
                        wd1, wd2, wd3, wd4 = st.columns(4)
                        wd1.metric("💧 Rainfall", f"{weather_data.get('rainfall_mm', 0)} mm/hr")
                        wd2.metric("💦 Humidity", f"{weather_data.get('humidity_pct', 0)}%")
                        wd3.metric("🌡️ Pressure", f"{weather_data.get('pressure_hpa', 0)} hPa")
                        wd4.metric("💨 Wind", f"{weather_data.get('wind_speed_ms', 0)} m/s")

                if geo_data and isinstance(geo_data, dict) and geo_data:
                    with st.expander("🌍 Ground Conditions at Time of Incident"):
                        gd1, gd2, gd3 = st.columns(3)
                        gd1.metric("💧 Soil Moisture", f"{geo_data.get('soil_moisture', 0):.3f}")
                        gd2.metric("Status", geo_data.get('soil_status', 'N/A'))
                        gd3.metric("🔴 Seismic", f"{geo_data.get('seismic_events', 0)} events")

                status = chosen.get("approval_status", "PENDING")
                if status == "PENDING":   st.warning(f"🟡 Status: PENDING")
                elif status == "APPROVED": st.success(f"🟢 Status: APPROVED")
                else:                      st.error(f"🔴 Status: REJECTED")

                if chosen.get("protocol"):
                    with st.expander("📘 NDMA Protocol"):
                        st.info(chosen["protocol"])

                if chosen.get("alert_en"):
                    with st.expander("🌐 Alerts"):
                        st.write(f"**EN:** {chosen.get('alert_en', '')}")
                        st.write(f"**HI:** {chosen.get('alert_hi', '')}")
                        st.write(f"**MR:** {chosen.get('alert_mr', '')}")