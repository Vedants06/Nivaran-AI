import streamlit as st
from PIL import Image
import time
from datetime import datetime
import json
import csv
import io

import folium
from streamlit_folium import st_folium


# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="Nivaran - UI Mockup",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Nivaran: Disaster Response Dashboard")
st.caption("Day-1 UI Mockup: Upload image + map marker + incident log + language selector (no backend yet).")


# -----------------------------
# Session State (MUST be first)
# -----------------------------
if "result" not in st.session_state:
    st.session_state.result = None

if "approval_status" not in st.session_state:
    st.session_state.approval_status = "PENDING"  # PENDING / APPROVED / REJECTED

if "incidents" not in st.session_state:
    st.session_state.incidents = []  # list of dicts

if "location_text" not in st.session_state:
    st.session_state.location_text = ""

if "lat" not in st.session_state:
    st.session_state.lat = 19.0760  # Mumbai default

if "lon" not in st.session_state:
    st.session_state.lon = 72.8777  # Mumbai default


# -----------------------------
# Helper Functions
# -----------------------------
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
    return sum(1 for i in incidents if i.get("type") == disaster_type)


def count_by_severity(incidents, severity: str) -> int:
    return sum(1 for i in incidents if str(i.get("severity", "")).lower() == severity.lower())


def get_marker_color(disaster_type: str) -> str:
    if disaster_type == "Flood":
        return "blue"
    elif disaster_type == "Landslide":
        return "darkred"
    elif disaster_type == "Fire":
        return "red"
    else:
        return "gray"


def run_pipeline_dummy(image_bytes: bytes, location_text: str) -> dict:
    """
    Day-1 dummy pipeline.
    Vedant will replace this later with LangGraph output.
    """
    time.sleep(2)
    return {
        "detected": "YES",
        "type": "Flood",        # Flood / Landslide / Fire
        "severity": "High",     # Low / Medium / High
        "location": location_text or "Unknown",
        "protocol": "Move people to higher ground. Avoid flooded roads. Stop travel in low-lying areas.",
        "alert_en": f"⚠️ Flood Alert at {location_text or 'this location'}: Water level is high. Avoid this area and use alternate routes.",
        "alert_hi": f"⚠️ {location_text or 'इस जगह'} पर बाढ़ चेतावनी: पानी का स्तर ज्यादा है। दूर रहें और दूसरा रास्ता लें।",
        "alert_mr": f"⚠️ {location_text or 'या ठिकाणी'} पूर इशारा: पाण्याची पातळी जास्त आहे. हा भाग टाळा आणि पर्यायी मार्ग वापरा."
    }


def make_csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    output = io.StringIO()
    # pick a stable set of keys (union)
    keys = sorted({k for r in rows for k in r.keys()})
    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return output.getvalue().encode("utf-8")


def add_sample_incidents():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    samples = [
        {
            "id": f"INC-{len(st.session_state.incidents)+1:03d}",
            "time": now,
            "detected": "YES",
            "type": "Flood",
            "severity": "Medium",
            "location": "Kurla Station",
            "lat": 19.0657,
            "lon": 72.8798,
            "protocol": "Avoid flooded tracks. Slow or stop service if water rises. Inform control room.",
            "alert_en": "⚠️ Flood warning at Kurla Station. Water rising. Avoid area.",
            "alert_hi": "⚠️ कुर्ला स्टेशन पर बाढ़ चेतावनी। पानी बढ़ रहा है।",
            "alert_mr": "⚠️ कुर्ला स्टेशन येथे पूर इशारा. पाणी वाढत आहे."
        },
        {
            "id": f"INC-{len(st.session_state.incidents)+2:03d}",
            "time": now,
            "detected": "YES",
            "type": "Landslide",
            "severity": "High",
            "location": "Matheran Ghat Road",
            "lat": 18.9905,
            "lon": 73.2717,
            "protocol": "Block the road, evacuate nearby residents, and deploy clearing equipment.",
            "alert_en": "⛰️ Landslide alert near Matheran Ghat. Do not travel. Follow police instructions.",
            "alert_hi": "⛰️ माथेरान घाट के पास भूस्खलन चेतावनी। यात्रा न करें।",
            "alert_mr": "⛰️ माथेरान घाटाजवळ भूस्खलन इशारा. प्रवास टाळा."
        },
        {
            "id": f"INC-{len(st.session_state.incidents)+3:03d}",
            "time": now,
            "detected": "YES",
            "type": "Fire",
            "severity": "Low",
            "location": "Andheri Market Area",
            "lat": 19.1197,
            "lon": 72.8464,
            "protocol": "Keep distance from smoke area. Inform fire brigade. Evacuate if needed.",
            "alert_en": "🔥 Small fire reported in Andheri Market area. Keep safe distance.",
            "alert_hi": "🔥 अंधेरी मार्केट में आग की सूचना। सुरक्षित दूरी बनाए रखें।",
            "alert_mr": "🔥 अंधेरी मार्केटमध्ये आगीची माहिती. सुरक्षित अंतर ठेवा."
        },
    ]
    # insert newest first
    for s in reversed(samples):
        st.session_state.incidents.insert(0, s)


# -----------------------------
# Sidebar Controls
# -----------------------------
st.sidebar.header("📍 Incident Details")

st.session_state.location_text = st.sidebar.text_input(
    "Enter location name (example: Kurla Station / Andheri Subway)",
    value=st.session_state.location_text
)

st.sidebar.subheader("📌 Coordinates (for marker)")
st.session_state.lat = st.sidebar.number_input("Latitude", value=float(st.session_state.lat), format="%.6f")
st.session_state.lon = st.sidebar.number_input("Longitude", value=float(st.session_state.lon), format="%.6f")

st.sidebar.subheader("🌐 Preferred Alert Language")
preferred_lang = st.sidebar.radio("Select language", ["English", "Hindi", "Marathi"], index=0)

st.sidebar.divider()

if st.sidebar.button("➕ Add Sample Incidents (Demo)"):
    add_sample_incidents()
    st.sidebar.success("Sample incidents added ✅")

if st.sidebar.button("🧹 Clear ALL Incidents"):
    st.session_state.incidents = []
    st.session_state.result = None
    st.session_state.approval_status = "PENDING"
    st.sidebar.success("All cleared ✅")


# -----------------------------
# KPI Row
# -----------------------------
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


# -----------------------------
# Main Uploader
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload a CCTV/Drone/Public image (jpg/png)",
    type=["jpg", "jpeg", "png"]
)

left, right = st.columns([1, 1])


# -----------------------------
# LEFT: Map + Image
# -----------------------------
with left:
    st.subheader("🗺️ Live Map View")

    # Base map (Mumbai)
    m = folium.Map(location=[19.0760, 72.8777], zoom_start=11)

    # Markers for all incidents
    for inc in st.session_state.incidents:
        if inc.get("lat") is None or inc.get("lon") is None:
            continue

        popup_text = f"""
        <b>ID:</b> {inc.get('id')}<br>
        <b>Type:</b> {inc.get('type')}<br>
        <b>Severity:</b> {inc.get('severity')}<br>
        <b>Location:</b> {inc.get('location')}<br>
        <b>Time:</b> {inc.get('time')}
        """

        folium.Marker(
            location=[inc.get("lat"), inc.get("lon")],
            popup=popup_text,
            tooltip=inc.get("type"),
            icon=folium.Icon(color=get_marker_color(inc.get("type")))
        ).add_to(m)

    st_folium(m, width=700, height=420)

    st.subheader("📷 Uploaded Image")
    if uploaded_file is None:
        st.info("No image uploaded yet.")
    else:
        img = Image.open(uploaded_file)
        st.image(img, caption="Image received ✅", use_container_width=True)


# -----------------------------
# RIGHT: Output + Actions
# -----------------------------
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

    # Run dummy pipeline and store incident
    if analyze_btn and uploaded_file is not None:
        st.session_state.approval_status = "PENDING"
        with st.spinner("AI Agents are thinking..."):
            image_bytes = uploaded_file.getvalue()
            result = run_pipeline_dummy(image_bytes, st.session_state.location_text)
            st.session_state.result = result

            incident = {
                "id": f"INC-{len(st.session_state.incidents)+1:03d}",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "lat": st.session_state.lat,
                "lon": st.session_state.lon,
                **result
            }
            st.session_state.incidents.insert(0, incident)

    result = st.session_state.result

    if result is None:
        st.info("Waiting for AI...")
    else:
        # Metrics
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Detected", result.get("detected", "—"))
        mc2.metric("Type", result.get("type", "—"))
        mc3.metric("Severity", severity_badge(result.get("severity", "—")))

        st.write(f"**📍 Location:** {result.get('location','Unknown')}")
        st.write(f"**🧭 Coordinates:** {st.session_state.lat}, {st.session_state.lon}")

        # Protocol
        st.markdown("### 📘 NDMA Protocol (Mock)")
        st.success(result.get("protocol", "—"))

        # Selected Language Alert
        st.markdown("### 🌐 Alert (Selected Language)")
        if preferred_lang == "English":
            chosen_alert = st.text_area("Alert (English)", value=result.get("alert_en", ""), height=120)
        elif preferred_lang == "Hindi":
            chosen_alert = st.text_area("Alert (Hindi)", value=result.get("alert_hi", ""), height=120)
        else:
            chosen_alert = st.text_area("Alert (Marathi)", value=result.get("alert_mr", ""), height=120)

        # Show all languages (optional)
        with st.expander("See alerts in all languages"):
            st.write("**English**")
            st.code(result.get("alert_en", ""), language="text")
            st.write("**Hindi**")
            st.code(result.get("alert_hi", ""), language="text")
            st.write("**Marathi**")
            st.code(result.get("alert_mr", ""), language="text")

        # Approval Buttons
        st.markdown("### ✅ Human-in-the-Loop Approval")
        a1, a2 = st.columns(2)
        if a1.button("✅ Approve Alert"):
            st.session_state.approval_status = "APPROVED"
        if a2.button("❌ Reject Alert"):
            st.session_state.approval_status = "REJECTED"

        if st.session_state.approval_status == "PENDING":
            st.warning("🟡 Approval Status: PENDING")
        elif st.session_state.approval_status == "APPROVED":
            st.success("🟢 Approval Status: APPROVED")
        else:
            st.error("🔴 Approval Status: REJECTED")

        # Tweet Draft (copy/paste)
        st.markdown("### 🐦 Tweet Preview (Draft)")
        tweet_text = f"{chosen_alert}\n\n#Nivaran #DisasterAlert"
        st.caption(f"Characters: {len(tweet_text)}/280")

        if len(tweet_text) > 280:
            st.error("Tweet is too long! Please shorten the alert.")
        else:
            st.info("Tweet length is OK ✅")

        st.text_area("Tweet Draft (Copy & Paste)", value=tweet_text, height=120)

    st.divider()

    # Incident Log + Downloads
    st.subheader("📋 Incident Log")

    if len(st.session_state.incidents) == 0:
        st.info("No incidents yet. Click Analyze or Add Sample Incidents.")
    else:
        options = [
            f"{i['id']} | {i['time']} | {i.get('location','Unknown')} | {i.get('type','—')} | {i.get('severity','—')}"
            for i in st.session_state.incidents
        ]
        selected = st.selectbox("Select an incident to view:", options=options)
        selected_id = selected.split("|")[0].strip()
        chosen = next((i for i in st.session_state.incidents if i["id"] == selected_id), None)

        if chosen:
            st.json(chosen)

        # Downloads
        json_bytes = json.dumps(st.session_state.incidents, indent=2).encode("utf-8")
        csv_bytes = make_csv_bytes(st.session_state.incidents)

        d1, d2 = st.columns(2)
        d1.download_button("⬇️ Download JSON", data=json_bytes, file_name="nivaran_incidents.json", mime="application/json")
        d2.download_button("⬇️ Download CSV", data=csv_bytes, file_name="nivaran_incidents.csv", mime="text/csv")
