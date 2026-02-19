import streamlit as st
from PIL import Image
import time
from datetime import datetime
import folium
from streamlit_folium import st_folium
from graph import app as nivaran_graph


# ---------------- Page config ----------------
st.set_page_config(
    page_title="Nivaran - UI Mockup",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Nivaran: Disaster Response Dashboard")
st.caption("UI Mockup: Upload image + map marker + incident log + language selector (no backend yet).")


# ---------------- Session state (MUST be before usage) ----------------
if "result" not in st.session_state:
    st.session_state.result = None
if "approval_status" not in st.session_state:
    st.session_state.approval_status = "PENDING"
if "incidents" not in st.session_state:
    st.session_state.incidents = []
if "location_text" not in st.session_state:
    st.session_state.location_text = ""
if "lat" not in st.session_state:
    st.session_state.lat = 19.0760   # Mumbai default
if "lon" not in st.session_state:
    st.session_state.lon = 72.8777   # Mumbai default
if "alert_en" not in st.session_state:
    st.session_state.alert_en = ""
if "alert_hi" not in st.session_state:
    st.session_state.alert_hi = ""
if "alert_mr" not in st.session_state:
    st.session_state.alert_mr = ""


# ---------------- Helpers ----------------
def severity_badge(severity: str) -> str:
    sev = (severity or "").strip().lower()
    if sev == "high":
        return "🔴 HIGH"
    if sev == "medium":
        return "🟠 MEDIUM"
    if sev == "low":
        return "🟢 LOW"
    return "—"


def count_by_type(incidents, disaster_type: str) -> int:
    return sum(1 for i in incidents if (i.get("type") == disaster_type))


def count_by_severity(incidents, severity: str) -> int:
    return sum(1 for i in incidents if (str(i.get("severity", "")).lower() == severity.lower()))


def get_marker_color(disaster_type: str) -> str:
    if disaster_type == "Flood":
        return "blue"
    elif disaster_type == "Landslide":
        return "darkred"
    elif disaster_type == "Fire":
        return "red"
    return "gray"


# ---------------- Mock pipeline (Vedant will replace later) ----------------

def run_pipeline(uploaded_file, location_text: str) -> dict:
    temp_path = "temp_upload.jpg"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    result = nivaran_graph.invoke({"image_path": temp_path})

    vision = result["vision_output"]
    return {
        "detected": "YES" if vision.get("hazard") else "NO",
        "type": vision.get("type", "unknown").capitalize(),
        "severity": vision.get("severity", "unknown").capitalize(),
        "location": location_text or "Unknown",
        "protocol": result["protocol"],
        "alert_en": result.get("alert_en", ""),
        "alert_hi": result.get("alert_hi", ""),
        "alert_mr": result.get("alert_mr", ""),
    }


# ---------------- KPI Row ----------------
incidents = st.session_state.incidents
total_incidents = len(incidents)
flood_count = count_by_type(incidents, "Flood")
landslide_count = count_by_type(incidents, "Landslide")
fire_count = count_by_type(incidents, "Fire")
high_count = count_by_severity(incidents, "High")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📌 Total Incidents", total_incidents)
c2.metric("🌧️ Flood", flood_count)
c3.metric("⛰️ Landslide", landslide_count)
c4.metric("🔥 Fire", fire_count)
c5.metric("🔴 High Severity", high_count)

st.divider()


# ---------------- Sidebar ----------------
st.sidebar.header("📍 Incident Details")

st.session_state.location_text = st.sidebar.text_input(
    "Enter location name (example: Kurla Station / Andheri Subway)",
    value=st.session_state.location_text
)

st.sidebar.subheader("📌 Coordinates (for marker)")
st.session_state.lat = st.sidebar.number_input(
    "Latitude",
    value=float(st.session_state.lat),
    format="%.6f"
)
st.session_state.lon = st.sidebar.number_input(
    "Longitude",
    value=float(st.session_state.lon),
    format="%.6f"
)

st.sidebar.subheader("🌐 Preferred Alert Language")
preferred_lang = st.sidebar.radio(
    "Select language",
    ["English", "Hindi", "Marathi"],
    index=0
)

st.sidebar.caption("Tip: For now, enter lat/lon manually. Later we can auto-convert location → coordinates.")


# ---------------- Main uploader ----------------
uploaded_file = st.file_uploader(
    "Upload a CCTV/Drone/Public image (jpg/png)",
    type=["jpg", "jpeg", "png"]
)

left, right = st.columns([1, 1])


# ---------------- LEFT: Map + image ----------------
with left:
    st.subheader("🗺️ Live Map View")

    # Base map centered at Mumbai
    m = folium.Map(location=[19.0760, 72.8777], zoom_start=11)

    # Add markers for ALL incidents
    for incident in st.session_state.incidents:
        if incident.get("lat") is None or incident.get("lon") is None:
            continue

        popup_text = f"""
        <b>ID:</b> {incident.get('id')}<br>
        <b>Type:</b> {incident.get('type')}<br>
        <b>Severity:</b> {incident.get('severity')}<br>
        <b>Location:</b> {incident.get('location')}<br>
        <b>Time:</b> {incident.get('time')}
        """

        folium.Marker(
            location=[incident.get("lat"), incident.get("lon")],
            popup=popup_text,
            tooltip=incident.get("type"),
            icon=folium.Icon(color=get_marker_color(incident.get("type")))
        ).add_to(m)

    st_folium(m, width=700, height=420)

    st.subheader("📷 Uploaded Image")
    if uploaded_file is None:
        st.info("No image uploaded yet.")
    else:
        img = Image.open(uploaded_file)
        st.image(img, caption="Image received ✅", use_container_width=True)


# ---------------- RIGHT: Output + actions ----------------
with right:
    st.subheader("🤖 AI Output")

    b1, b2 = st.columns([1, 1])
    analyze_btn = b1.button("🚀 Analyze Image")
    reset_btn = b2.button("🧹 Reset (clear current)")

    if reset_btn:
        st.session_state.result = None
        st.session_state.approval_status = "PENDING"
        st.success("Cleared current result ✅")

    if analyze_btn and uploaded_file is None:
        st.warning("Please upload an image first.")

    if analyze_btn and uploaded_file is not None:
        st.session_state.approval_status = "PENDING"
        with st.spinner("AI Agents are thinking..."):
            result = run_pipeline(uploaded_file, st.session_state.location_text)
            st.session_state.result = result

            st.session_state.alert_en = result.get("alert_en", "")
            st.session_state.alert_hi = result.get("alert_hi", "")
            st.session_state.alert_mr = result.get("alert_mr", "")

            incident = {
                "id": f"INC-{len(st.session_state.incidents)+1:03d}",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "location": result.get("location", "Unknown"),
                "lat": st.session_state.lat,
                "lon": st.session_state.lon,
                **result
            }
            st.session_state.incidents.insert(0, incident)

    result = st.session_state.result

    tab_flood, tab_landslide, tab_fire, tab_all = st.tabs(
        ["🌧️ Flood", "⛰️ Landslide", "🔥 Fire", "📋 All Incidents"]
    )

    def render_incident_view(incident: dict):
        c1, c2, c3 = st.columns(3)
        c1.metric("Detected", incident.get("detected", "—"))
        c2.metric("Type", incident.get("type", "—"))
        c3.metric("Severity", severity_badge(incident.get("severity", "—")))

        st.write(f"**📍 Location:** {incident.get('location', 'Unknown')}")
        st.write(f"**🧭 Coordinates:** {incident.get('lat', '—')}, {incident.get('lon', '—')}")
        st.write(f"**🕒 Time:** {incident.get('time', '—')}")

        status = st.session_state.approval_status
        if status == "PENDING":
            st.warning("🟡 Approval Status: PENDING")
        elif status == "APPROVED":
            st.success("🟢 Approval Status: APPROVED")
        else:
            st.error("🔴 Approval Status: REJECTED")

        st.markdown("### 📘 NDMA Protocol (Mock)")
        st.success(incident.get("protocol", "—"))

        st.markdown("### 🌐 Alert (Selected Language)")
        if preferred_lang == "English":
            chosen_alert = st.text_area(
                "Alert (English)",
                value=st.session_state.alert_en,   # ← session state
                height=120,
                key=f"chosen_en_{incident.get('id', 'cur')}"
            )
        elif preferred_lang == "Hindi":
            chosen_alert = st.text_area(
                "Alert (Hindi)",
                value=st.session_state.alert_hi,   # ← session state
                height=120,
                key=f"chosen_hi_{incident.get('id', 'cur')}"
            )
        else:
            chosen_alert = st.text_area(
                "Alert (Marathi)",
                value=st.session_state.alert_mr,   # ← session state
                height=120,
                key=f"chosen_mr_{incident.get('id', 'cur')}"
            )
        st.markdown("### ✅ Human-in-the-Loop Approval")
        a1, a2 = st.columns(2)
        if a1.button("✅ Approve Alert", key=f"appr_{incident.get('id', 'cur')}"):
            st.session_state.approval_status = "APPROVED"
        if a2.button("❌ Reject Alert", key=f"rej_{incident.get('id', 'cur')}"):
            st.session_state.approval_status = "REJECTED"

        st.markdown("### 🐦 Tweet Preview (Draft)")
        tweet_text = f"{chosen_alert}\n\n#Nivaran #DisasterAlert"
        st.caption(f"Characters: {len(tweet_text)}/280")

        if len(tweet_text) > 280:
            st.error("Tweet is too long! Please shorten the alert.")
        else:
            st.info("Tweet length is OK ✅")

        st.text_area(
            "Tweet Draft (Copy & Paste)",
            value=tweet_text,
            height=120,
            key=f"tweet_{incident.get('id', 'cur')}"
        )

    with tab_flood:
        st.subheader("🌧️ Flood")
        if result is None:
            st.info("Waiting for AI...")
        elif result.get("type") != "Flood":
            st.warning("Current result is not Flood (dummy type is set in code).")
        else:
            render_incident_view({"id": "CURRENT", "time": "NOW", "lat": st.session_state.lat, "lon": st.session_state.lon, **result})

    with tab_landslide:
        st.subheader("⛰️ Landslide")
        if result is None:
            st.info("Waiting for AI...")
        elif result.get("type") != "Landslide":
            st.warning("Current result is not Landslide (dummy type is set in code).")
        else:
            render_incident_view({"id": "CURRENT", "time": "NOW", "lat": st.session_state.lat, "lon": st.session_state.lon, **result})

    with tab_fire:
        st.subheader("🔥 Fire")
        if result is None:
            st.info("Waiting for AI...")
        elif result.get("type") != "Fire":
            st.warning("Current result is not Fire (dummy type is set in code).")
        else:
            render_incident_view({"id": "CURRENT", "time": "NOW", "lat": st.session_state.lat, "lon": st.session_state.lon, **result})

    with tab_all:
        st.subheader("📋 Incident Log")
        if len(st.session_state.incidents) == 0:
            st.info("No incidents yet. Click Analyze to generate a record.")
        else:
            options = [
                f"{i['id']} | {i['time']} | {i.get('location', 'Unknown')} | {i['type']} | {i['severity']}"
                for i in st.session_state.incidents
            ]
            selected = st.selectbox("Select an incident to view:", options=options)
            selected_id = selected.split("|")[0].strip()

            chosen = next((i for i in st.session_state.incidents if i["id"] == selected_id), None)
            if chosen:
                render_incident_view(chosen)