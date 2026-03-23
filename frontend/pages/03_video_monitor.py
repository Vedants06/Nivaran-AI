# frontend/pages/03_video_monitor.py
import streamlit as st
import cv2
import os
import sys
import plotly.graph_objects as go
from datetime import datetime
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.pipeline.graph import app as nivaran_graph

st.set_page_config(page_title="Nivaran - Video Monitor", layout="wide")
st.title("🎥 Nivaran — Multi-Camera Live Monitor")
st.caption("Simulating 3 CCTV feeds simultaneously. Alert fires when confidence > 0.85.")

# Camera config
CAMERAS = [
    {"name": "Kurla Station",    "zone": "Central Line"},
    {"name": "Hindmata Junction","zone": "South Mumbai"},
    {"name": "Andheri Subway",   "zone": "Western Line"},
]

# Session state per camera
for i, cam in enumerate(CAMERAS):
    if f"cam_{i}_history" not in st.session_state:
        st.session_state[f"cam_{i}_history"] = []
    if f"cam_{i}_status" not in st.session_state:
        st.session_state[f"cam_{i}_status"] = "IDLE"
    if f"cam_{i}_severity" not in st.session_state:
        st.session_state[f"cam_{i}_severity"] = "—"

# Upload section
st.subheader("📁 Upload Videos for Each Camera")
upload_cols = st.columns(3)
video_files = []
for i, col in enumerate(upload_cols):
    with col:
        f = st.file_uploader(
            f"📷 {CAMERAS[i]['name']}",
            type=["mp4", "mov", "avi", "mkv"],
            key=f"vid_{i}"
        )
        video_files.append(f)

st.divider()

# Confidence threshold
threshold = st.slider(
    "🎚️ Alert Confidence Threshold",
    0.5, 1.0, 0.85, 0.05
)

# Start button
start_btn = st.button(
    "▶️ Start Monitoring All Cameras",
    use_container_width=True,
    type="primary"
)

st.divider()

# Grid layout
st.subheader("📡 Live Camera Grid")
grid_cols = st.columns(3)

# Placeholders for each camera cell
frame_placeholders = []
status_placeholders = []
chart_placeholders = []

for i, col in enumerate(grid_cols):
    with col:
        st.markdown(f"**📷 {CAMERAS[i]['name']}** — {CAMERAS[i]['zone']}")
        frame_placeholders.append(st.empty())
        status_placeholders.append(st.empty())
        chart_placeholders.append(st.empty())

def render_confidence_chart(history: list, camera_name: str, threshold: float):
    if not history:
        return go.Figure()

    timestamps = [h["timestamp"] for h in history]
    confidences = [h["confidence"] for h in history]
    severities = [h["severity"] for h in history]

    colors = []
    for s in severities:
        if s == "high":
            colors.append("red")
        elif s == "medium":
            colors.append("orange")
        else:
            colors.append("green")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=confidences,
        mode="lines+markers",
        name="Confidence",
        line=dict(color="royalblue", width=2),
        marker=dict(color=colors, size=8)
    ))

    # Threshold line
    fig.add_hline(
        y=threshold,
        line_dash="dot",
        line_color="red",
        annotation_text=f"Alert Threshold ({threshold})"
    )

    fig.update_layout(
        title=f"{camera_name} — Confidence Over Time",
        xaxis_title="Time",
        yaxis_title="Confidence",
        yaxis=dict(range=[0, 1]),
        height=200,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False
    )

    return fig

def get_severity_color(severity: str) -> str:
    s = severity.lower()
    if s == "high":
        return "🔴"
    if s == "medium":
        return "🟠"
    if s == "low":
        return "🟢"
    return "⚪"

# Run monitoring
if start_btn:
    missing = [i for i, f in enumerate(video_files) if f is None]
    if missing:
        st.warning(f"Please upload videos for all 3 cameras first.")
        st.stop()

    # Save all videos to temp files
    temp_paths = []
    caps = []
    for i, vf in enumerate(video_files):
        suffix = os.path.splitext(vf.name)[1] or ".mp4"
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        with open(path, "wb") as f:
            f.write(vf.getbuffer())
        temp_paths.append(path)
        caps.append(cv2.VideoCapture(path))

    fps_list = [max(cap.get(cv2.CAP_PROP_FPS), 1) for cap in caps]
    sample_interval = 5  # seconds
    frame_intervals = [int(fps * sample_interval) for fps in fps_list]
    frame_counts = [0, 0, 0]

    st.info("🔴 Live monitoring started. Press Stop or wait for videos to finish.")

    global_alert = st.empty()
    any_active = True

    while any_active:
        any_active = False

        for i, cap in enumerate(caps):
            ret, frame = cap.read()
            if not ret:
                continue

            any_active = True
            frame_counts[i] += 1

            # Show current frame regardless
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_placeholders[i].image(rgb, use_container_width=True)

            # Only analyze every Nth frame
            if frame_counts[i] % frame_intervals[i] != 0:
                continue

            timestamp = datetime.now().strftime("%H:%M:%S")

            try:
                temp_frame = f"temp_cam_{i}_frame.jpg"
                cv2.imwrite(temp_frame, frame)

                result = nivaran_graph.invoke({"image_path": temp_frame})
                vision = result["vision_output"]

                confidence = vision.get("confidence", 0.0)
                severity = vision.get("severity", "low")
                hazard = vision.get("hazard", False)
                dtype = vision.get("type", "none")

                # Update history
                st.session_state[f"cam_{i}_history"].append({
                    "timestamp": timestamp,
                    "confidence": confidence,
                    "severity": severity
                })

                # Update status
                if hazard and confidence >= threshold:
                    st.session_state[f"cam_{i}_status"] = "ALERT"
                    st.session_state[f"cam_{i}_severity"] = severity
                    global_alert.error(
                        f"🚨 ALERT — {CAMERAS[i]['name']}: "
                        f"{dtype.upper()} detected! "
                        f"Severity: {severity.upper()} | "
                        f"Confidence: {confidence:.2f}"
                    )
                else:
                    st.session_state[f"cam_{i}_status"] = "CLEAR"
                    st.session_state[f"cam_{i}_severity"] = severity

                # Update status badge
                icon = get_severity_color(severity)
                status_placeholders[i].markdown(
                    f"{icon} **{st.session_state[f'cam_{i}_status']}** | "
                    f"Type: `{dtype}` | "
                    f"Confidence: `{confidence:.2f}`"
                )

                # Update chart
                fig = render_confidence_chart(
                    st.session_state[f"cam_{i}_history"],
                    CAMERAS[i]["name"],
                    threshold
                )
                chart_placeholders[i].plotly_chart(
                    fig,
                    use_container_width=True,
                    key=f"chart_{i}_{frame_counts[i]}"
                )

            except Exception as e:
                status_placeholders[i].warning(f"⚠️ Frame error: {e}")

    # Cleanup
    for cap in caps:
        cap.release()
    for path in temp_paths:
        if os.path.exists(path):
            os.remove(path)

    st.success("✅ All camera feeds completed.")