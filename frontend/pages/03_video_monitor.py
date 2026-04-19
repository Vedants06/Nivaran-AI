import streamlit as st
import cv2
import os
import sys
import plotly.graph_objects as go
from datetime import datetime
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.pipeline.graph import app as nivaran_graph
from backend.database.incident_store import save_incident, get_all_incidents

st.set_page_config(page_title="Nivaran - Video Monitor", layout="wide")

st.markdown("""
<style>
.cam-header {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #666;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #eee;
    margin-bottom: 0.8rem;
}
.alert-banner {
    background: #fdecea;
    border: 1px solid #ef9a9a;
    border-left: 4px solid #d32f2f;
    border-radius: 6px;
    padding: 1rem 1.5rem;
    margin-bottom: 1rem;
}
.alert-banner-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: #d32f2f;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.alert-banner-body {
    font-size: 0.82rem;
    color: #333;
    margin-top: 0.3rem;
}
.clear-banner {
    background: #f1f8e9;
    border: 1px solid #aed581;
    border-radius: 6px;
    padding: 0.5rem 1rem;
    font-size: 0.8rem;
    color: #558b2f;
}
.status-pill {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}
.pill-alert   { background: #fdecea; color: #c62828; }
.pill-clear   { background: #e8f5e9; color: #2e7d32; }
.pill-idle    { background: #f5f5f5; color: #888; }
.incident-card {
    background: #fff8e1;
    border: 1px solid #ffe082;
    border-left: 4px solid #f9a825;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin-top: 0.5rem;
    font-size: 0.82rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CAMERA CONFIG
# ─────────────────────────────────────────────
CAMERAS = [
    {
        "name":     "Kurla Station",
        "zone":     "Kurla",
        "lat":      19.0726,
        "lon":      72.8794,
        "line":     "Central Line"
    },
    {
        "name":     "Hindmata Junction",
        "zone":     "Hindmata",
        "lat":      19.0145,
        "lon":      72.8510,
        "line":     "South Mumbai"
    },
    {
        "name":     "Andheri Subway",
        "zone":     "Andheri",
        "lat":      19.1136,
        "lon":      72.8697,
        "line":     "Western Line"
    },
]

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
for i in range(len(CAMERAS)):
    for key, default in [
        (f"cam_{i}_history",  []),
        (f"cam_{i}_status",   "IDLE"),
        (f"cam_{i}_severity", "—"),
        (f"cam_{i}_alerts",   []),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

if "video_incidents" not in st.session_state:
    st.session_state.video_incidents = []

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div style="padding: 1.5rem 0 1rem 0; border-bottom: 2px solid #1a73e8;
            margin-bottom: 1.5rem;">
    <div style="font-size: 1.6rem; font-weight: 700; color: #1a1a1a;">
        Video Monitor
    </div>
    <div style="font-size: 0.85rem; color: #666; margin-top: 0.3rem;">
        Multi-camera CCTV simulation with automatic flood detection
        and full incident pipeline
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONTROLS ROW
# ─────────────────────────────────────────────
ctrl1, ctrl2, ctrl3 = st.columns([2, 1, 1])

with ctrl1:
    threshold = st.slider(
        "Alert confidence threshold",
        min_value=0.5,
        max_value=1.0,
        value=0.75,
        step=0.05,
        help="Confidence level above which an alert is triggered"
    )

with ctrl2:
    demo_mode = st.toggle(
        "Monsoon Simulation",
        value=True,
        help="ON: simulated weather data. OFF: live API data."
    )

with ctrl3:
    sample_every = st.selectbox(
        "Analyze every",
        [10, 20, 30, 60],
        index=1,
        help="How many seconds of video between frame analyses"
    )

st.markdown("---")

# ─────────────────────────────────────────────
# VIDEO UPLOAD
# ─────────────────────────────────────────────
st.markdown(
    '<div class="cam-header">Upload Camera Feeds</div>',
    unsafe_allow_html=True
)

upload_cols = st.columns(3)
video_files = []
for i, col in enumerate(upload_cols):
    with col:
        cam = CAMERAS[i]
        st.caption(f"{cam['name']} — {cam['line']}")
        f = st.file_uploader(
            cam["name"],
            type=["mp4", "mov", "avi", "mkv"],
            key=f"vid_{i}",
            label_visibility="collapsed"
        )
        video_files.append(f)
        if f:
            st.caption(f"Ready: {f.name}")

st.markdown("---")

# ─────────────────────────────────────────────
# START BUTTON
# ─────────────────────────────────────────────
start_btn = st.button(
    "Start Monitoring",
    use_container_width=True,
    type="primary"
)

# ─────────────────────────────────────────────
# CAMERA GRID PLACEHOLDERS
# ─────────────────────────────────────────────
st.markdown(
    '<div class="cam-header" style="margin-top:1rem;">Live Camera Grid</div>',
    unsafe_allow_html=True
)

grid_cols = st.columns(3)
frame_ph  = []
status_ph = []
chart_ph  = []

for i, col in enumerate(grid_cols):
    with col:
        cam = CAMERAS[i]
        st.markdown(
            f'<div style="font-size:0.82rem;font-weight:600;color:#333;'
            f'margin-bottom:0.5rem;">{cam["name"]}</div>'
            f'<div style="font-size:0.72rem;color:#aaa;margin-bottom:0.8rem;">'
            f'{cam["line"]} · {cam["zone"]}</div>',
            unsafe_allow_html=True
        )
        frame_ph.append(st.empty())
        status_ph.append(st.empty())
        chart_ph.append(st.empty())

# Global alert banner placeholder
global_alert_ph = st.empty()

# Incident log placeholder (updates as incidents are detected)
incident_log_ph = st.empty()

# ─────────────────────────────────────────────
# HELPER: CONFIDENCE CHART
# ─────────────────────────────────────────────
def build_chart(history: list, cam_name: str, threshold: float):
    if not history:
        fig = go.Figure()
        fig.update_layout(
            height=160,
            margin=dict(l=10, r=10, t=30, b=10),
            title=dict(text="No data yet", font=dict(size=11)),
            paper_bgcolor="#fafafa",
            plot_bgcolor="#fafafa"
        )
        return fig

    times  = [h["timestamp"]  for h in history]
    confs  = [h["confidence"] for h in history]
    sevs   = [h["severity"]   for h in history]

    colors = []
    for s in sevs:
        if s == "high":   colors.append("#d32f2f")
        elif s == "medium": colors.append("#f57c00")
        else:               colors.append("#388e3c")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=confs,
        mode="lines+markers",
        line=dict(color="#1a73e8", width=1.5),
        marker=dict(color=colors, size=7)
    ))
    fig.add_hline(
        y=threshold,
        line_dash="dot",
        line_color="#d32f2f",
        annotation_text=f"Threshold {threshold:.2f}",
        annotation_font_size=9
    )
    fig.update_layout(
        height=160,
        margin=dict(l=10, r=10, t=30, b=20),
        title=dict(
            text=f"{cam_name} — confidence",
            font=dict(size=10, color="#888")
        ),
        yaxis=dict(range=[0, 1], tickfont=dict(size=9)),
        xaxis=dict(tickfont=dict(size=9)),
        paper_bgcolor="#fafafa",
        plot_bgcolor="#fafafa",
        showlegend=False
    )
    return fig


# ─────────────────────────────────────────────
# HELPER: RENDER INCIDENT LOG
# ─────────────────────────────────────────────
def render_incident_log(incidents: list):
    if not incidents:
        return

    with incident_log_ph.container():
        st.markdown("---")
        st.markdown(
            '<div class="cam-header">Incidents Detected This Session</div>',
            unsafe_allow_html=True
        )
        st.caption(
            f"{len(incidents)} incident(s) saved to database. "
            "Go to the main dashboard to approve or reject alerts."
        )

        for inc in reversed(incidents):
            composite = float(inc.get('composite_score', 0) or 0)
            confidence = float(inc.get('confidence', 0)) * 100
            severity = inc.get('severity', '—')
            risk_level = inc.get('risk_level', '—')

            # Color based on risk
            border_color = {
                "CRITICAL": "#d32f2f",
                "HIGH":     "#f57c00",
                "MODERATE": "#f9a825",
                "LOW":      "#388e3c",
            }.get(risk_level, "#ccc")

            # Header card
            st.markdown(f"""
            <div style="border: 1px solid #eee;
                        border-left: 4px solid {border_color};
                        border-radius: 6px;
                        padding: 1rem 1.2rem;
                        margin-bottom: 0.5rem;
                        background: #fafafa;">
                <div style="display:flex;justify-content:space-between;
                            align-items:flex-start;">
                    <div>
                        <div style="font-size:0.85rem;font-weight:700;
                                    color:#1a1a1a;">
                            {inc['id']} — {inc['type']} at {inc['location']}
                        </div>
                        <div style="font-size:0.78rem;color:#666;
                                    margin-top:0.2rem;">
                            {inc.get('time', '')}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.4rem;font-weight:800;
                                    color:{border_color};">
                            {composite:.0f}/100
                        </div>
                        <div style="font-size:0.7rem;color:#888;">
                            {risk_level}
                        </div>
                    </div>
                </div>
                <div style="margin-top:0.6rem;font-size:0.78rem;
                            color:#555;display:flex;gap:1.5rem;">
                    <span>Severity: <b>{severity}</b></span>
                    <span>Confidence: <b>{confidence:.0f}%</b></span>
                    <span>Approval: <b style="color:#f57f17;">PENDING</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Expandable details
            with st.expander(f"Full details — {inc['id']}"):

                detail_col1, detail_col2 = st.columns(2)

                with detail_col1:
                    # Alerts
                    st.markdown(
                        '<div style="font-size:0.75rem;font-weight:600;'
                        'text-transform:uppercase;letter-spacing:0.5px;'
                        'color:#888;margin-bottom:0.5rem;">Generated Alerts</div>',
                        unsafe_allow_html=True
                    )
                    st.markdown("**English**")
                    st.write(inc.get("alert_en", "—"))
                    st.markdown("**Hindi**")
                    st.write(inc.get("alert_hi", "—"))
                    st.markdown("**Marathi**")
                    st.write(inc.get("alert_mr", "—"))

                with detail_col2:
                    # Tweets
                    st.markdown(
                        '<div style="font-size:0.75rem;font-weight:600;'
                        'text-transform:uppercase;letter-spacing:0.5px;'
                        'color:#888;margin-bottom:0.5rem;">Tweet Drafts</div>',
                        unsafe_allow_html=True
                    )
                    st.markdown("**Public**")
                    pub = inc.get("tweet_public", "—")
                    st.write(pub)
                    st.caption(f"{len(pub)}/280 characters")

                    st.markdown("**Authority**")
                    auth = inc.get("tweet_authority", "—")
                    st.write(auth)
                    st.caption(f"{len(auth)}/280 characters")

                # Protocol full width
                st.markdown(
                    '<div style="font-size:0.75rem;font-weight:600;'
                    'text-transform:uppercase;letter-spacing:0.5px;'
                    'color:#888;margin-top:0.8rem;margin-bottom:0.5rem;">'
                    'NDMA Protocol</div>',
                    unsafe_allow_html=True
                )
                protocol = inc.get("protocol", "")
                if protocol:
                    st.info(protocol)
                else:
                    st.caption("Protocol not retrieved for this incident.")

                # Approval note
                st.markdown(
                    '<div style="background:#fff8e1;border:1px solid #ffe082;'
                    'border-radius:6px;padding:0.6rem 1rem;'
                    'font-size:0.82rem;color:#f57f17;margin-top:0.8rem;">'
                    'This incident is saved as PENDING. Open the main dashboard '
                    'to approve or reject this alert before dispatch.'
                    '</div>',
                    unsafe_allow_html=True
                )


# ─────────────────────────────────────────────
# MONITORING LOOP
# ─────────────────────────────────────────────
if start_btn:
    missing = [i for i, f in enumerate(video_files) if f is None]
    if missing:
        missing_names = [CAMERAS[i]["name"] for i in missing]
        st.warning(f"Please upload videos for: {', '.join(missing_names)}")
        st.stop()

    # Reset session history for this run
    for i in range(len(CAMERAS)):
        st.session_state[f"cam_{i}_history"] = []
        st.session_state[f"cam_{i}_status"]  = "IDLE"
        st.session_state[f"cam_{i}_alerts"]  = []
    st.session_state.video_incidents = []

    # Save all videos to temp files
    temp_paths = []
    caps       = []
    for i, vf in enumerate(video_files):
        suffix = os.path.splitext(vf.name)[1] or ".mp4"
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        with open(path, "wb") as f:
            f.write(vf.getbuffer())
        temp_paths.append(path)
        cap = cv2.VideoCapture(path)
        caps.append(cap)

    fps_list = [max(cap.get(cv2.CAP_PROP_FPS), 1) for cap in caps]
    frame_intervals = [int(fps * sample_every) for fps in fps_list]
    frame_counts    = [0, 0, 0]

    global_alert_ph.info(
        "Monitoring started. Frames are analyzed every "
        f"{sample_every} seconds of video."
    )

    any_active = True
    while any_active:
        any_active = False

        for i, cap in enumerate(caps):
            ret, frame = cap.read()
            if not ret:
                continue

            any_active      = True
            frame_counts[i] += 1

            # Always show the current frame
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_ph[i].image(rgb, use_container_width=True)

            # Only run analysis on sampled frames
            if frame_counts[i] % frame_intervals[i] != 0:
                continue

            timestamp = datetime.now().strftime("%H:%M:%S")
            cam       = CAMERAS[i]

            try:
                # Save frame to disk for vision agent
                root_path  = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                frame_path = os.path.join(
                    root_path, f"temp_cam_{i}_frame.jpg"
                )
                # Convert BGR to RGB before saving
                # OpenCV reads in BGR, PIL/Gemini expects RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                from PIL import Image as PILImage
                PILImage.fromarray(frame_rgb).save(frame_path, quality=95)

                # ── Run full pipeline (not just vision) ──
                pipeline_result = nivaran_graph.invoke({
                    "image_path": frame_path,
                    "zone_name":  cam["zone"],
                    "lat":        cam["lat"],
                    "lon":        cam["lon"],
                    "demo_mode":  demo_mode
                })

                vision     = pipeline_result["vision_output"]
                risk       = pipeline_result.get("multi_factor_risk", {})
                confidence = vision.get("confidence", 0.0)
                severity   = vision.get("severity", "low")
                hazard     = vision.get("hazard", False)
                dtype      = vision.get("type", "none")
                composite  = risk.get("composite_risk_score", 0)
                risk_level = risk.get("overall_risk_level", "UNKNOWN")

                # Update confidence history
                st.session_state[f"cam_{i}_history"].append({
                    "timestamp":  timestamp,
                    "confidence": confidence,
                    "severity":   severity
                })

                # ── Check if alert should fire ────────────
                alert_triggered = (
                    hazard and
                    confidence >= threshold and
                    dtype not in ["none", "unknown", "error"]
                )

                if alert_triggered:
                    st.session_state[f"cam_{i}_status"]   = "ALERT"
                    st.session_state[f"cam_{i}_severity"]  = severity

                    # ── Save incident to database ─────────
                    incident_id = (
                        f"VID-{i}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    )
                    incident = {
                        "id":               incident_id,
                        "time":             datetime.now().strftime(
                                                "%Y-%m-%d %H:%M:%S"
                                            ),
                        "timestamp":        datetime.now().strftime(
                                                "%Y-%m-%d %H:%M:%S"
                                            ),
                        "location":         cam["zone"],
                        "lat":              cam["lat"],
                        "lon":              cam["lon"],
                        "type":             dtype.capitalize(),
                        "severity":         severity.capitalize(),
                        "confidence":       confidence,
                        "detected":         "YES",
                        "protocol":         pipeline_result.get("protocol", ""),
                        "alert_en":         pipeline_result.get("alert_en", ""),
                        "alert_hi":         pipeline_result.get("alert_hi", ""),
                        "alert_mr":         pipeline_result.get("alert_mr", ""),
                        "tweet_public":     pipeline_result.get(
                                                "tweet_public", ""
                                            ),
                        "tweet_authority":  pipeline_result.get(
                                                "tweet_authority", ""
                                            ),
                        "media_kind":       "video",
                        "media_name":       video_files[i].name,
                        "approval_status":  "PENDING",
                        "composite_score":  composite,
                        "risk_level":       risk_level,
                        "factor_breakdown": risk.get("factor_breakdown", {}),
                    }
                    save_incident(incident)
                    st.session_state.video_incidents.append(incident)

                    # ── Show global alert banner ──────────
                    alert_en   = pipeline_result.get("alert_en", "")
                    tweet_pub  = pipeline_result.get("tweet_public", "")
                    protocol   = pipeline_result.get("protocol", "")

                    global_alert_ph.markdown(f"""
                    <div class="alert-banner">
                        <div class="alert-banner-title">
                            ALERT — {cam['name']}
                        </div>
                        <div class="alert-banner-body">
                            <b>{dtype.upper()}</b> detected &nbsp;·&nbsp;
                            Severity: <b>{severity.upper()}</b> &nbsp;·&nbsp;
                            Confidence: <b>{confidence:.0%}</b> &nbsp;·&nbsp;
                            Composite Risk: <b>{composite:.0f}/100</b> &nbsp;·&nbsp;
                            {timestamp}
                        </div>
                        <div class="alert-banner-body" style="margin-top:0.5rem;">
                            <b>Alert:</b> {alert_en}
                        </div>
                        <div class="alert-banner-body" style="margin-top:0.3rem;">
                            <b>Tweet:</b> {tweet_pub}
                        </div>
                        <div class="alert-banner-body"
                             style="margin-top:0.3rem;font-size:0.78rem;color:#555;">
                            <b>Protocol:</b> {protocol[:200]}...
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                else:
                    st.session_state[f"cam_{i}_status"]  = "CLEAR"
                    st.session_state[f"cam_{i}_severity"] = severity

                # ── Update per-camera status badge ────────
                cam_status = st.session_state[f"cam_{i}_status"]
                pill_class = {
                    "ALERT": "pill-alert",
                    "CLEAR": "pill-clear",
                    "IDLE":  "pill-idle"
                }.get(cam_status, "pill-idle")

                status_ph[i].markdown(
                    f'<span class="status-pill {pill_class}">'
                    f'{cam_status}</span> &nbsp; '
                    f'<span style="font-size:0.78rem;color:#555;">'
                    f'{dtype} · {confidence:.0%} confidence · '
                    f'risk {composite:.0f}/100</span>',
                    unsafe_allow_html=True
                )

                # ── Update confidence chart ───────────────
                fig = build_chart(
                    st.session_state[f"cam_{i}_history"],
                    cam["name"],
                    threshold
                )
                chart_ph[i].plotly_chart(
                    fig,
                    use_container_width=True,
                    key=f"chart_{i}_{frame_counts[i]}"
                )

                # ── Update incident log ───────────────────
                render_incident_log(st.session_state.video_incidents)

            except Exception as e:
                status_ph[i].markdown(
                    f'<span style="font-size:0.78rem;color:#f57c00;">'
                    f'Frame error: {e}</span>',
                    unsafe_allow_html=True
                )

    # Cleanup
    for cap in caps:
        cap.release()
    for path in temp_paths:
        if os.path.exists(path):
            os.remove(path)

    # Final summary
    total_incidents = len(st.session_state.video_incidents)
    if total_incidents > 0:
        global_alert_ph.markdown(f"""
        <div class="alert-banner">
            <div class="alert-banner-title">Session Complete</div>
            <div class="alert-banner-body">
                {total_incidents} incident(s) detected and saved to the
                incident database. Review them in the main dashboard.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        global_alert_ph.markdown(
            '<div class="clear-banner">'
            'Monitoring complete. No incidents detected across all cameras.'
            '</div>',
            unsafe_allow_html=True
        )

    render_incident_log(st.session_state.video_incidents)