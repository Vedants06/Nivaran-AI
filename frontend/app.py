import streamlit as st
from PIL import Image
from datetime import datetime
import folium
from streamlit_folium import st_folium
import tempfile
import os
import sys
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
st.caption("Real-time disaster detection, NDMA protocol retrieval, and multilingual alert generation.")

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
    return tuple(tuple(sorted(i.items())) for i in incidents_list)

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
def run_pipeline(uploaded_file, kind: str, location_text: str) -> dict:
    temp_path = "temp_upload.jpg"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    result = nivaran_graph.invoke({"image_path": temp_path})
    vision = result["vision_output"]

    return {
        "detected":        "YES" if vision.get("hazard") else "NO",
        "type":            vision.get("type", "unknown").capitalize(),
        "severity":        vision.get("severity", "unknown").capitalize(),
        "confidence":      vision.get("confidence", 0.0),
        "location":        location_text or "Unknown",
        "protocol":        result["protocol"],
        "alert_en":        result.get("alert_en", ""),
        "alert_hi":        result.get("alert_hi", ""),
        "alert_mr":        result.get("alert_mr", ""),
        "tweet_public":    result.get("tweet_public", ""),
        "tweet_authority": result.get("tweet_authority", ""),
        "media_kind":      kind,
        "media_name":      getattr(uploaded_file, "name", "unknown"),
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
        with st.spinner("AI Agents are thinking..."):
            kind   = st.session_state.current_file_kind or _guess_kind_and_suffix(uploaded_file)[0]
            result = run_pipeline(uploaded_file, kind, st.session_state.location_text)
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

            # Save to SQLite
            save_incident(incident)
            st.session_state.incidents = get_all_incidents()

    result = st.session_state.result

    tab_flood, tab_landslide, tab_fire, tab_all = st.tabs(
        ["🌧️ Flood", "⛰️ Landslide", "🔥 Fire", "📋 All Incidents"]
    )

    def render_incident_view(incident: dict):
        c1, c2, c3 = st.columns(3)
        c1.metric("Detected",  incident.get("detected", "—"))
        c2.metric("Type",      incident.get("type", "—"))
        c3.metric("Severity",  severity_badge(incident.get("severity", "—")))

        st.write(f"**📍 Location:** {incident.get('location', 'Unknown')}")
        st.write(f"**🧭 Coordinates:** {incident.get('lat', '—')}, {incident.get('lon', '—')}")
        st.write(f"**🕒 Time:** {incident.get('time') or incident.get('timestamp', '—')}")
        st.write(f"**📎 Media:** {incident.get('media_kind', '—')} | {incident.get('media_name', '—')}")

        status = st.session_state.approval_status
        if status == "PENDING":   st.warning("🟡 Approval Status: PENDING")
        elif status == "APPROVED": st.success("🟢 Approval Status: APPROVED")
        else:                      st.error("🔴 Approval Status: REJECTED")

        st.markdown("### 📘 NDMA Protocol")
        st.success(incident.get("protocol", "—"))

        st.markdown("### 🌐 Alert (Selected Language)")
        if preferred_lang == "English":
            chosen_alert = st.text_area("Alert (English)", value=st.session_state.alert_en, height=120, key=f"en_{incident.get('id','cur')}")
        elif preferred_lang == "Hindi":
            chosen_alert = st.text_area("Alert (Hindi)",   value=st.session_state.alert_hi, height=120, key=f"hi_{incident.get('id','cur')}")
        else:
            chosen_alert = st.text_area("Alert (Marathi)", value=st.session_state.alert_mr, height=120, key=f"mr_{incident.get('id','cur')}")

        st.markdown("### ✅ Human-in-the-Loop Approval")
        a1, a2 = st.columns(2)
        if a1.button("✅ Approve", key=f"appr_{incident.get('id','cur')}"):
            st.session_state.approval_status = "APPROVED"
        if a2.button("❌ Reject",  key=f"rej_{incident.get('id','cur')}"):
            st.session_state.approval_status = "REJECTED"

        st.markdown("### 🐦 Tweet Drafts")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**👥 Public Tweet**")
            pub = st.text_area("Public", value=st.session_state.tweet_public, height=140, key=f"pub_{incident.get('id','cur')}")
            st.caption(f"{len(pub)}/280")
            if len(pub) <= 280:
                st.success("✅ Ready to post")
            else:
                st.error("Too long! Shorten it.")

        with col2:
            st.markdown("**🚨 Authority Tweet**")
            auth = st.text_area("Authority", value=st.session_state.tweet_authority, height=140, key=f"auth_{incident.get('id','cur')}")
            st.caption(f"{len(auth)}/280")
            if len(auth) <= 280:
                st.success("✅ Ready to post")
            else:
                st.error("Too long! Shorten it.")

        # PDF Export
        st.markdown("### 📄 Export Report")
        if st.button("📥 Generate PDF Report", key=f"pdf_{incident.get('id','cur')}"):
            with st.spinner("Generating PDF..."):
                try:
                    from backend.utils.report_generator import generate_report
                    out_path = generate_report(incident)
                    if out_path and os.path.exists(out_path):
                        with open(out_path, "rb") as f:
                            st.download_button(
                                label="⬇️ Download Report",
                                data=f,
                                file_name=os.path.basename(out_path),
                                mime="application/pdf",
                                key=f"dl_{incident.get('id','cur')}"
                            )
                    else:
                        st.error("PDF generation failed.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab_flood:
        st.subheader("🌧️ Flood")
        if result is None:
            st.info("Waiting for AI...")
        elif result.get("type") != "Flood":
            st.warning("No flood detected in current analysis.")
        else:
            render_incident_view({"id": "CURRENT", "time": "NOW", "lat": st.session_state.lat, "lon": st.session_state.lon, **result})

    with tab_landslide:
        st.subheader("⛰️ Landslide")
        if result is None:
            st.info("Waiting for AI...")
        elif result.get("type") != "Landslide":
            st.warning("No landslide detected in current analysis.")
        else:
            render_incident_view({"id": "CURRENT", "time": "NOW", "lat": st.session_state.lat, "lon": st.session_state.lon, **result})

    with tab_fire:
        st.subheader("🔥 Fire")
        if result is None:
            st.info("Waiting for AI...")
        elif result.get("type") != "Fire":
            st.warning("No fire detected in current analysis.")
        else:
            render_incident_view({"id": "CURRENT", "time": "NOW", "lat": st.session_state.lat, "lon": st.session_state.lon, **result})

    with tab_all:
        st.subheader("📋 Incident Log")
        if not st.session_state.incidents:
            st.info("No incidents yet.")
        else:
            options = [
                f"{i['id']} | {i.get('time') or i.get('timestamp','')} | {i.get('location','Unknown')} | {i.get('type','')} | {i.get('severity','')}"
                for i in st.session_state.incidents
            ]
            selected    = st.selectbox("Select an incident:", options)
            selected_id = selected.split("|")[0].strip()
            chosen      = next((i for i in st.session_state.incidents if i["id"] == selected_id), None)
            if chosen:
                render_incident_view(chosen)