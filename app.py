import streamlit as st
from PIL import Image
import time

st.set_page_config(
    page_title="Nivaran - UI Mockup",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Nivaran: Disaster Response Dashboard")
st.caption("Step 5 UI: Approval workflow + Tweet preview (no backend yet).")

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
    time.sleep(2)  # simulate processing
    return {
        "detected": "YES",
        "type": "Flood",
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
    st.session_state.approval_status = "PENDING"  # PENDING / APPROVED / REJECTED

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
    reset_btn = b2.button("🧹 Reset")

    if reset_btn:
        st.session_state.result = None
        st.session_state.approval_status = "PENDING"
        st.success("Cleared previous result ✅")

    if analyze_btn and uploaded_file is None:
        st.warning("Please upload an image first.")

    if analyze_btn and uploaded_file is not None:
        st.session_state.approval_status = "PENDING"
        with st.spinner("AI Agents are thinking..."):
            st.session_state.result = run_pipeline(uploaded_file)

    result = st.session_state.result

    # Top metrics
    c1, c2, c3 = st.columns(3)

    if result is None:
        c1.metric("Disaster Detected", "—")
        c2.metric("Disaster Type", "—")
        c3.metric("Severity", "—")
        st.info("Waiting for AI...")
    else:
        c1.metric("Disaster Detected", result["detected"])
        c2.metric("Disaster Type", result["type"])
        c3.metric("Severity", severity_badge(result["severity"]))

        # Approval status display
        status = st.session_state.approval_status
        if status == "PENDING":
            st.warning("🟡 Approval Status: PENDING")
        elif status == "APPROVED":
            st.success("🟢 Approval Status: APPROVED")
        else:
            st.error("🔴 Approval Status: REJECTED")

        st.markdown("### 📘 NDMA Protocol")
        st.success(result["protocol"])

        st.markdown("### 🌐 Local Language Alerts")
        tab1, tab2, tab3 = st.tabs(["English", "Hindi", "Marathi"])
        with tab1:
            alert_en = st.text_area("English Alert", value=result["alert_en"], height=80)
        with tab2:
            alert_hi = st.text_area("Hindi Alert", value=result["alert_hi"], height=80)
        with tab3:
            alert_mr = st.text_area("Marathi Alert", value=result["alert_mr"], height=80)

        st.markdown("### ✅ Human-in-the-Loop Approval")
        a1, a2 = st.columns(2)
        if a1.button("✅ Approve Alert"):
            st.session_state.approval_status = "APPROVED"
        if a2.button("❌ Reject Alert"):
            st.session_state.approval_status = "REJECTED"

        st.markdown("### 🐦 Tweet Preview (Draft)")
        # simple tweet draft (you can later add location, hashtag, etc.)
        tweet_text = f"{alert_en}\n\n#Nivaran #DisasterAlert"

        # character counter
        char_count = len(tweet_text)
        st.caption(f"Characters: {char_count}/280")

        # warn if too long
        if char_count > 280:
            st.error("Tweet is too long! Please shorten the alert.")
        else:
            st.info("Tweet length is OK ✅")

        st.text_area("Tweet Draft (Copy & Paste)", value=tweet_text, height=120)
        st.caption("Tip: Press Ctrl+A then Ctrl+C to copy.")