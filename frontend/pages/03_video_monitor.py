import streamlit as st
import cv2
import os
import sys
from datetime import datetime
import tempfile
import plotly.graph_objects as go

# Fix import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.pipeline.graph import app as nivaran_graph

st.set_page_config(page_title="Video Monitor", layout="wide")
st.title("🎥 Nivaran Multi-Camera Monitor")

# Camera names
CAMERAS = ["Kurla", "Hindmata", "Andheri"]

# Upload videos
st.subheader("Upload 3 Camera Videos")
cols = st.columns(3)
videos = []

for i in range(3):
    with cols[i]:
        file = st.file_uploader(f"Camera {i+1}", type=["mp4"], key=i)
        videos.append(file)

# Start button
start = st.button("Start Monitoring")

# Layout
frame_cols = st.columns(3)
charts = [st.empty(), st.empty(), st.empty()]
frames = [st.empty(), st.empty(), st.empty()]
status = [st.empty(), st.empty(), st.empty()]

history = [[], [], []]

if start:

    if any(v is None for v in videos):
        st.warning("Upload all 3 videos")
        st.stop()

    caps = []
    paths = []

    # Save temp videos
    for v in videos:
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp.write(v.read())
        paths.append(temp.name)
        caps.append(cv2.VideoCapture(temp.name))

    while True:
        active = False

        for i, cap in enumerate(caps):
            ret, frame = cap.read()

            if not ret:
                continue

            active = True

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames[i].image(rgb, use_container_width=True)

            # Save frame
            temp_img = f"temp_{i}.jpg"
            cv2.imwrite(temp_img, frame)

            # Run AI
            result = nivaran_graph.invoke({"image_path": temp_img})
            vision = result["vision_output"]

            conf = vision.get("confidence", 0)
            severity = vision.get("severity", "low")
            dtype = vision.get("type", "none")
            hazard = vision.get("hazard", False)

            # Save history
            history[i].append(conf)

            # Status
            if hazard and conf > 0.85:
                status[i].error(f"🚨 {dtype} | {conf:.2f}")
            else:
                status[i].success(f"✅ Safe | {conf:.2f}")

            # Chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=history[i], mode="lines"))
            charts[i].plotly_chart(fig, use_container_width=True)

        if not active:
            break

    st.success("Done")