import streamlit as st
from PIL import Image
import time
from datetime import datetime

st.set_page_config(
    page_title="Nivaran - UI Mockup",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Nivaran: Disaster Response Dashboard")
st.caption("Step 6 UI: Multi-disaster tabs + incident log (no backend yet).")

def severity_badge(severity: str) -> str:
    sev = (severity or "").strip().lower()
    if sev == "high":
        return "🔴 HIGH"
    if sev == "medium":
        return "🟠 MEDIUM"
    if sev == "low":
        return "🟢 LOW"
    return "—"

# Integration point for Vedant later
def run_pipeline(uploaded_file) -> dict:
    time.sleep(2)

    # Dummy output (later: replace with LangGraph output)
    # You can change type here manually to test tabs
    return {
        "detected": "YES",
        "type": "Flood",  # Flood / Landslide / Fire
        "severity": "High",
        "protocol": "Move people to higher ground. Avoid flooded roads. Stop travel in low-lying areas.",
        "alert_en": "⚠️ Flood Alert: Water level is high. Avoid this area and use alternate routes.",
        "alert_hi": "⚠️ बाढ़ चेतावनी: पानी का स्तर ज्यादा है। इस जगह से दूर रहें और दूसरा रास्ता लें।",
        "alert_mr": "⚠️ पूर इशारा: पाण्याची पातळी जास्त आहे. हा भाग टाळा आणि पर्यायी मार्ग वापरा."
    }

# ---- Session state ----
if "result" not in st.session_state:
    st.session_state.result = None
if "approval_status" not in st.session_state:
    st.session_state.approval_status = "PENDING"
if "incidents" not in st.session_state:
    st.session_state.incidents = []  # list of dicts

uploaded_file = st.file_uploader(
    "Upload a CCTV/Drone/Public image (jpg/png)",
    type=["jpg", "jpeg", "png"]
)

st.divider()

left, right = st.columns([1, 1])

# LEFT: image view
with left:
    st.subheader("📷 Uploaded Image")
    if uploaded_file is None:
        st.info("No image uploaded yet.")
    else:
        img = Image.open(uploaded_file)
        st.image(img, caption="Image received ✅", use_container_width=True)

# RIGHT: output + actions
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
            result = run_pipeline(uploaded_file)
            st.session_state.result = result

            # Save incident record
            incident = {
                "id": f"INC-{len(st.session_state.incidents)+1:03d}",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                **result
            }
            st.session_state.incidents.insert(0, incident)  # latest first

    result = st.session_state.result

    # Tabs for multi-disaster view
    tab_flood, tab_landslide, tab_fire, tab_all = st.tabs(
        ["🌧️ Flood", "⛰️ Landslide", "🔥 Fire", "📋 All Incidents"]
    )

    # Helper to show one incident
    def render_incident_view(incident: dict):
        c1, c2, c3 = st.columns(3)
        c1.metric("Disaster Detected", incident.get("detected", "—"))
        c2.metric("Disaster Type", incident.get("type", "—"))
        c3.metric("Severity", severity_badge(incident.get("severity", "—")))

        status = st.session_state.approval_status
        if status == "PENDING":
            st.warning("🟡 Approval Status: PENDING")
        elif status == "APPROVED":
            st.success("🟢 Approval Status: APPROVED")
        else:
            st.error("🔴 Approval Status: REJECTED")

        st.markdown("### 📘 NDMA Protocol")
        st.success(incident.get("protocol", "—"))

        st.markdown("### 🌐 Local Language Alerts")
        alert_en = st.text_area("English Alert", value=incident.get("alert_en", ""), height=80, key=f"en_{incident.get('id','cur')}")
        st.text_area("Hindi Alert", value=incident.get("alert_hi", ""), height=80, key=f"hi_{incident.get('id','cur')}")
        st.text_area("Marathi Alert", value=incident.get("alert_mr", ""), height=80, key=f"mr_{incident.get('id','cur')}")

        st.markdown("### ✅ Human-in-the-Loop Approval")
        a1, a2 = st.columns(2)
        if a1.button("✅ Approve Alert", key=f"appr_{incident.get('id','cur')}"):
            st.session_state.approval_status = "APPROVED"
        if a2.button("❌ Reject Alert", key=f"rej_{incident.get('id','cur')}"):
            st.session_state.approval_status = "REJECTED"

        st.markdown("### 🐦 Tweet Preview (Draft)")
        tweet_text = f"{alert_en}\n\n#Nivaran #DisasterAlert"
        st.caption(f"Characters: {len(tweet_text)}/280")
        if len(tweet_text) > 280:
            st.error("Tweet is too long! Please shorten the alert.")
        else:
            st.info("Tweet length is OK ✅")
        st.text_area("Tweet Draft (Copy & Paste)", value=tweet_text, height=120, key=f"tweet_{incident.get('id','cur')}")

    # Flood tab
    with tab_flood:
        st.subheader("🌧️ Flood Incidents")
        if result is None:
            st.info("Waiting for AI...")
        elif result.get("type") != "Flood":
            st.warning("Current result is not Flood. Try analyzing another image (dummy type is set in code).")
        else:
            render_incident_view({"id": "CURRENT", **result})

    # Landslide tab
    with tab_landslide:
        st.subheader("⛰️ Landslide Incidents")
        if result is None:
            st.info("Waiting for AI...")
        elif result.get("type") != "Landslide":
            st.warning("Current result is not Landslide. Try analyzing another image (dummy type is set in code).")
        else:
            render_incident_view({"id": "CURRENT", **result})

    # Fire tab
    with tab_fire:
        st.subheader("🔥 Fire Incidents")
        if result is None:
            st.info("Waiting for AI...")
        elif result.get("type") != "Fire":
            st.warning("Current result is not Fire. Try analyzing another image (dummy type is set in code).")
        else:
            render_incident_view({"id": "CURRENT", **result})

    # All incidents tab
    with tab_all:
        st.subheader("📋 Incident Log")
        if len(st.session_state.incidents) == 0:
            st.info("No incidents yet. Click Analyze to generate a record.")
        else:
            options = [f"{i['id']} | {i['time']} | {i['type']} | {i['severity']}" for i in st.session_state.incidents]
            selected = st.selectbox("Select an incident to view details:", options=options)
            selected_id = selected.split("|")[0].strip()

            chosen = next((i for i in st.session_state.incidents if i["id"] == selected_id), None)
            if chosen:
                st.write(f"**Incident:** {chosen['id']}  |  **Time:** {chosen['time']}")
                render_incident_view(chosen)