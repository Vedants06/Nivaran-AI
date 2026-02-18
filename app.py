import streamlit as st
from PIL import Image
import time

st.set_page_config(
    page_title="Nivaran - UI Mockup",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Nivaran: Disaster Response Dashboard")
st.caption("Step 3 UI: Analyze button + spinner + dummy results (no backend yet).")

# Upload
uploaded_file = st.file_uploader(
    "Upload a CCTV/Drone/Public image (jpg/png)",
    type=["jpg", "jpeg", "png"]
)

st.divider()

left, right = st.columns([1, 1])

# LEFT: show image
with left:
    st.subheader("📷 Uploaded Image")
    if uploaded_file is None:
        st.info("No image uploaded yet.")
    else:
        img = Image.open(uploaded_file)
        st.image(img, caption="Image received ✅", use_container_width=True)

# ---- Dummy state storage (so results stay after button click) ----
if "result" not in st.session_state:
    st.session_state.result = None

# RIGHT: outputs + button
with right:
    st.subheader("🤖 AI Output")

    # Button to trigger analysis
    analyze_btn = st.button("🚀 Analyze Image")

    # If clicked without upload
    if analyze_btn and uploaded_file is None:
        st.warning("Please upload an image first.")
    
    # If clicked with image → show spinner and generate dummy result
    if analyze_btn and uploaded_file is not None:
        with st.spinner("AI Agents are thinking..."):
            time.sleep(2)  # simulate processing time

            # Dummy output (later Vedant will replace this with real graph output)
            st.session_state.result = {
                "detected": "YES",
                "type": "Flood",
                "severity": "High",
                "protocol": "Move people to higher ground. Avoid flooded roads. Stop travel in low-lying areas.",
                "alert_en": "⚠️ Flood Alert: Water level is high. Avoid this area and use alternate routes.",
                "alert_hi": "⚠️ बाढ़ चेतावनी: पानी का स्तर ज्यादा है। इस जगह से दूर रहें और दूसरा रास्ता लें।",
                "alert_mr": "⚠️ पूर इशारा: पाण्याची पातळी जास्त आहे. हा भाग टाळा आणि पर्यायी मार्ग वापरा."
            }

    # Display placeholders OR results
    result = st.session_state.result

    c1, c2, c3 = st.columns(3)
    if result is None:
        c1.metric("Disaster Detected", "—")
        c2.metric("Disaster Type", "—")
        c3.metric("Severity", "—")
        st.info("Waiting for AI...")
    else:
        c1.metric("Disaster Detected", result["detected"])
        c2.metric("Disaster Type", result["type"])
        c3.metric("Severity", result["severity"])

        st.markdown("### 📘 NDMA Protocol")
        st.success(result["protocol"])

        st.markdown("### 📢 Alert Draft")
        st.text_area("Alert message", value=result["alert_en"], height=100)

        st.markdown("### 🌐 Local Language Alerts")
        tab1, tab2, tab3 = st.tabs(["English", "Hindi", "Marathi"])
        with tab1:
            st.text_area("English Alert", value=result["alert_en"], height=80)
        with tab2:
            st.text_area("Hindi Alert", value=result["alert_hi"], height=80)
        with tab3:
            st.text_area("Marathi Alert", value=result["alert_mr"], height=80)