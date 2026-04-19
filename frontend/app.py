import streamlit as st
from PIL import Image
from datetime import datetime
import folium
from streamlit_folium import st_folium
import os
import sys
import json
import cv2
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.pipeline.graph import app as nivaran_graph
from backend.database.incident_store import save_incident, get_all_incidents

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Nivaran — Mumbai Flood Intelligence",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
<style>
/* ── Base ── */
html, body { overflow-x: hidden; }

/* ── Header ── */
.nivaran-header {
    padding: 2rem 0 1rem 0;
    border-bottom: 2px solid #1a73e8;
    margin-bottom: 2rem;
}
.nivaran-title {
    font-size: 2rem;
    font-weight: 700;
    color: #888888;
    letter-spacing: -0.5px;
    margin: 0;
}
.nivaran-subtitle {
    font-size: 0.9rem;
    color: #666;
    margin-top: 0.3rem;
}

/* ── KPI Cards ── */
.kpi-card {
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    text-align: center;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #1a1a1a;
    line-height: 1;
}
.kpi-label {
    font-size: 0.78rem;
    color: #888;
    margin-top: 0.4rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Section headers ── */
.section-title {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #888;
    margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #eee;
}

/* ── Risk score display ── */
.risk-score-block {
    background: #f8f9fa;
    border-left: 4px solid #ccc;
    border-radius: 4px;
    padding: 1rem 1.5rem;
    margin-bottom: 1rem;
}
.risk-score-block.critical { border-left-color: #d32f2f; }
.risk-score-block.high     { border-left-color: #f57c00; }
.risk-score-block.moderate { border-left-color: #f9a825; }
.risk-score-block.low      { border-left-color: #388e3c; }
.risk-score-block.minimal  { border-left-color: #1976d2; }

.risk-number {
    font-size: 3rem;
    font-weight: 800;
    line-height: 1;
    color: #1a1a1a;
}
.risk-level-text {
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #555;
    margin-top: 0.2rem;
}
.risk-action {
    font-size: 0.8rem;
    color: #888;
    margin-top: 0.3rem;
}

/* ── Factor rows ── */
.factor-row {
    display: flex;
    align-items: center;
    padding: 0.6rem 0;
    border-bottom: 1px solid #f0f0f0;
    gap: 1rem;
}
.factor-name {
    font-size: 0.82rem;
    font-weight: 600;
    color: #333;
    width: 140px;
    flex-shrink: 0;
}
.factor-source {
    font-size: 0.72rem;
    color: #aaa;
}
.factor-score {
    font-size: 0.85rem;
    font-weight: 700;
    color: #1a1a1a;
    width: 55px;
    text-align: right;
    flex-shrink: 0;
}
.factor-contribution {
    font-size: 0.75rem;
    color: #888;
    width: 45px;
    text-align: right;
    flex-shrink: 0;
}

/* ── Detection badge ── */
.detection-badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}
.badge-yes { background: #fdecea; color: #c62828; }
.badge-no  { background: #e8f5e9; color: #2e7d32; }

/* ── Data table style ── */
.data-row {
    display: flex;
    justify-content: space-between;
    padding: 0.4rem 0;
    border-bottom: 1px solid #f5f5f5;
    font-size: 0.85rem;
}
.data-label { color: #888; }
.data-value { font-weight: 600; color: #8B8B8B; }

/* ── Mode banner ── */
.mode-banner {
    padding: 0.5rem 1rem;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 500;
    margin-bottom: 1rem;
    text-align: center;
}
.mode-sim  { background: #fff3e0; color: #e65100; border: 1px solid #ffcc80; }
.mode-live { background: #e8f5e9; color: #1b5e20; border: 1px solid #a5d6a7; }

/* ── Approval bar ── */
.approval-pending  { background: #fff8e1; border: 1px solid #ffe082;
                     border-radius: 6px; padding: 0.6rem 1rem;
                     font-size: 0.85rem; color: #f57f17; }
.approval-approved { background: #e8f5e9; border: 1px solid #a5d6a7;
                     border-radius: 6px; padding: 0.6rem 1rem;
                     font-size: 0.85rem; color: #2e7d32; }
.approval-rejected { background: #fdecea; border: 1px solid #ef9a9a;
                     border-radius: 6px; padding: 0.6rem 1rem;
                     font-size: 0.85rem; color: #c62828; }

/* ── Streamlit overrides ── */
div[data-testid="stMetric"] {
    background: transparent !important;
    border: none !important;
}
.stProgress > div > div {
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
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

if not st.session_state.incidents:
    st.session_state.incidents = get_all_incidents()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def count_by_type(incidents, t):
    return sum(1 for i in incidents if i.get("type") == t)

def count_by_severity(incidents, s):
    return sum(1 for i in incidents
               if str(i.get("severity", "")).lower() == s.lower())

def risk_css_class(level: str) -> str:
    m = {"CRITICAL": "critical", "HIGH": "high",
         "MODERATE": "moderate", "LOW": "low", "MINIMAL": "minimal"}
    return m.get((level or "").upper(), "low")

def risk_color_hex(level: str) -> str:
    m = {"CRITICAL": "#d32f2f", "HIGH": "#f57c00",
         "MODERATE": "#f9a825", "LOW": "#388e3c", "MINIMAL": "#1976d2"}
    return m.get((level or "").upper(), "#888")

def get_marker_color(t):
    return {"Flood": "blue", "Landslide": "darkred",
            "Fire": "red"}.get(t, "gray")

def _incidents_hashable(lst):
    return tuple(tuple(sorted((k, str(v)) for k, v in i.items())) for i in lst)

def _guess_kind(uploaded_file):
    name = (uploaded_file.name or "").lower()
    if name.endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
        return "video"
    return "image"


# ─────────────────────────────────────────────
# GEOCODING
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# MAP
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def build_map(incidents_hashable, clat, clon, zoom=11, searched=None):
    incidents = [dict(t) for t in incidents_hashable]
    m = folium.Map(location=[clat, clon], zoom_start=zoom,
                   tiles="CartoDB positron")

    if searched and searched.get("lat"):
        folium.Marker(
            [searched["lat"], searched["lon"]],
            popup=searched.get("name", ""),
            tooltip="Searched location",
            icon=folium.Icon(color="green", icon="info-sign")
        ).add_to(m)

    for inc in incidents:
        if inc.get("lat") and inc.get("lon"):
            folium.CircleMarker(
                location=[inc["lat"], inc["lon"]],
                radius=8,
                color=risk_color_hex(inc.get("risk_level", "")),
                fill=True,
                fill_opacity=0.8,
                popup=(f"<b>{inc.get('id','')}</b><br>"
                   f"{inc.get('type','')} — {inc.get('severity','')}<br>"
                   f"Risk: {float(inc.get('composite_risk_score', 0) or 0):.0f}/100<br>"
                   f"{inc.get('location','')}"),
                tooltip=f"{inc.get('type','')} | {inc.get('location','')}"
            ).add_to(m)
    return m


# ─────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────
def run_pipeline(uploaded_file, kind, location_text,
                 lat=19.076, lon=72.877, demo_mode=True):

    temp_path = "temp_upload.jpg"

    if kind == "video":
        # Extract first meaningful frame from video
        import tempfile as tmpfile
        suffix = os.path.splitext(uploaded_file.name)[1] or ".mp4"
        fd, vid_path = tmpfile.mkstemp(suffix=suffix)
        os.close(fd)
        with open(vid_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        cap = cv2.VideoCapture(vid_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = max(cap.get(cv2.CAP_PROP_FPS), 1)

        # Jump to 10% into the video to skip intros/dark frames
        target_frame = max(1, int(total_frames * 0.10))
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        ret, frame = cap.read()
        cap.release()
        os.remove(vid_path)

        if ret:
            from PIL import Image as PILImage
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            PILImage.fromarray(frame_rgb).save(temp_path, quality=95)
        else:
            # Fallback: try first frame
            cap2 = cv2.VideoCapture(vid_path)
            ret2, frame2 = cap2.read()
            cap2.release()
            if ret2:
                from PIL import Image as PILImage
                frame_rgb = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
                PILImage.fromarray(frame_rgb).save(temp_path, quality=95)
    else:
        # Image upload — save directly
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    zone_name = location_text if location_text else "Dadar"

    result = nivaran_graph.invoke({
        "image_path": temp_path,
        "zone_name":  zone_name,
        "lat":        lat,
        "lon":        lon,
        "demo_mode":  demo_mode
    })

    vision = result["vision_output"]
    risk   = result.get("multi_factor_risk", {})

    return {
        "detected":          "YES" if vision.get("hazard") else "NO",
        "type":              vision.get("type", "unknown").capitalize(),
        "severity":          vision.get("severity", "unknown").capitalize(),
        "confidence":        vision.get("confidence", 0.0),
        "location":          location_text or "Unknown",
        "lat":               lat,
        "lon":               lon,
        "protocol":          result.get("protocol", ""),
        "alert_en":          result.get("alert_en", ""),
        "alert_hi":          result.get("alert_hi", ""),
        "alert_mr":          result.get("alert_mr", ""),
        "tweet_public":      result.get("tweet_public", ""),
        "tweet_authority":   result.get("tweet_authority", ""),
        "media_kind":        kind,
        "media_name":        getattr(uploaded_file, "name", "unknown"),
        "multi_factor_risk": risk,
        "composite_score":   risk.get("composite_risk_score", 0),
        "risk_level":        risk.get("overall_risk_level", "UNKNOWN"),
        "factor_breakdown":  risk.get("factor_breakdown", {}),
        "risk_explanation":  risk.get("explanation", ""),
        "data_quality":      risk.get("data_quality", {}),
    }

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="nivaran-header">
    <div class="nivaran-title">Nivaran</div>
    <div class="nivaran-subtitle">
        Mumbai Flood Intelligence System &nbsp;·&nbsp;
        Multi-factor risk detection &nbsp;·&nbsp;
        NDMA protocol retrieval &nbsp;·&nbsp;
        Human-in-the-loop approval
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────
incidents = st.session_state.incidents

k1, k2, k3, k4, k5 = st.columns(5)

def kpi_card(col, value, label):
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

kpi_card(k1, len(incidents),                           "Total Incidents")
kpi_card(k2, count_by_type(incidents, "Flood"),        "Flood")
kpi_card(k3, count_by_type(incidents, "Landslide"),    "Landslide")
kpi_card(k4, count_by_type(incidents, "Fire"),         "Fire")
kpi_card(k5, count_by_severity(incidents, "High"),     "High Severity")

st.markdown("<br>", unsafe_allow_html=True)

# ── Pending alerts notification ──────────────
pending = [
    i for i in st.session_state.incidents
    if i.get("approval_status") == "PENDING"
    and i.get("detected") == "YES"
]

if pending:
    st.markdown(f"""
    <div style="background:#fff3e0;border:1px solid #ffcc80;
                border-left:4px solid #f57c00;border-radius:6px;
                padding:0.8rem 1.2rem;margin-bottom:1rem;">
        <div style="font-size:0.85rem;font-weight:700;color:#e65100;">
            {len(pending)} incident(s) awaiting officer approval
        </div>
        <div style="font-size:0.78rem;color:#555;margin-top:0.3rem;">
            Review the incident log below or check the All Incidents tab
            to approve or reject pending alerts.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Location")

    st.session_state.location_text = st.text_input(
        "Area name",
        value=st.session_state.location_text,
        placeholder="e.g. Hindmata, Dadar, Sion"
    )

    col_a, col_b = st.columns(2)
    search_btn = col_a.button("Search", use_container_width=True)
    clear_btn  = col_b.button("Clear",  use_container_width=True)

    if clear_btn:
        st.session_state.last_search_name    = ""
        st.session_state.last_search_lat     = None
        st.session_state.last_search_lon     = None
        st.session_state.last_search_address = ""

    if search_btn:
        q = st.session_state.location_text.strip()
        if not q:
            st.warning("Enter a location name first.")
        else:
            try:
                with st.spinner("Searching..."):
                    lat, lon, addr = geocode_place(q)
                if lat is None:
                    st.error("Location not found.")
                else:
                    st.session_state.lat               = lat
                    st.session_state.lon               = lon
                    st.session_state.map_center_lat    = lat
                    st.session_state.map_center_lon    = lon
                    st.session_state.last_search_name  = q
                    st.session_state.last_search_lat   = lat
                    st.session_state.last_search_lon   = lon
                    st.session_state.last_search_address = addr
                    st.success("Found")
            except Exception as e:
                st.error(f"Geocoding failed: {e}")

    if st.session_state.last_search_lat:
        st.caption(f"{st.session_state.last_search_name}")
        st.caption(st.session_state.last_search_address[:70] + "...")

    st.markdown("---")
    st.markdown("### Coordinates")
    st.session_state.lat = st.number_input(
        "Latitude",  value=float(st.session_state.lat),  format="%.6f")
    st.session_state.lon = st.number_input(
        "Longitude", value=float(st.session_state.lon), format="%.6f")

    st.markdown("---")
    st.markdown("### Alert Language")
    preferred_lang = st.radio(
        "Language", ["English", "Hindi", "Marathi"],
        index=0, label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("### Data Mode")
    st.session_state.demo_mode = st.toggle(
        "Monsoon Simulation",
        value=st.session_state.demo_mode,
        help=(
            "ON: Uses simulated monsoon data for demos.\n"
            "OFF: Pulls real-time weather and soil data from APIs."
        )
    )

    if st.session_state.demo_mode:
        st.markdown(
            '<div class="mode-banner mode-sim">'
            'Simulation mode — monsoon conditions'
            '</div>', unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="mode-banner mode-live">'
            'Live mode — real-time API data'
            '</div>', unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("### Incident Map")
    searched_marker = None
    if st.session_state.last_search_lat:
        searched_marker = {
            "name": st.session_state.last_search_name,
            "lat":  st.session_state.last_search_lat,
            "lon":  st.session_state.last_search_lon,
        }
    inc_hash = _incidents_hashable(st.session_state.incidents)
    sidebar_map = build_map(
        inc_hash,
        float(st.session_state.lat),
        float(st.session_state.lon),
        zoom=13 if searched_marker else 11,
        searched=searched_marker
    )
    st_folium(sidebar_map, width=300, height=200, key="sidebar_map")


# ─────────────────────────────────────────────
# MAIN CONTENT — TWO COLUMNS
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# UPLOAD SECTION (Full Width)
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">Media Input</div>',
            unsafe_allow_html=True)

uploaded_file = None
if not st.session_state.uploaded_once:
    uploaded_file = st.file_uploader(
        "Upload an image or video from CCTV, drone, or public source",
        type=["jpg", "jpeg", "png", "mp4", "mov", "mkv", "avi", "webm"],
        key=f"uploader_{st.session_state.uploader_key}",
        label_visibility="collapsed"
    )
    if uploaded_file is not None:
        kind = _guess_kind(uploaded_file)
        st.session_state.uploaded_once     = True
        st.session_state.current_file      = uploaded_file
        st.session_state.current_file_kind = kind
        st.rerun()
else:
    uploaded_file = st.session_state.current_file

if uploaded_file is None:
    analyze_btn_top = False
    st.markdown("""
    <div style="border: 2px dashed #ddd; border-radius: 8px;
                padding: 2rem; text-align: center; color: #aaa;
                font-size: 0.9rem; margin-bottom: 1rem;">
        No media uploaded yet. Drag and drop or use the uploader above.
    </div>
    """, unsafe_allow_html=True)
else:
    # Show media preview + controls side by side
    prev_col, ctrl_col = st.columns([3, 1])
    with prev_col:
        kind = st.session_state.current_file_kind or _guess_kind(uploaded_file)
        if kind == "video":
            st.video(uploaded_file)
        else:
            st.image(Image.open(uploaded_file), use_container_width=True)
        st.caption(f"File: {uploaded_file.name}")

    with ctrl_col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        analyze_btn_top = st.button(
            "Run Analysis",
            type="primary",
            use_container_width=True,
            key="analyze_top"
        )
        if st.button("Upload different file",
                     use_container_width=True,
                     key="upload_diff"):
            st.session_state.result            = None
            st.session_state.approval_status   = "PENDING"
            st.session_state.uploaded_once     = False
            st.session_state.current_file      = None
            st.session_state.current_file_kind = None
            st.session_state.uploader_key     += 1
            st.rerun()
        if st.button("Reset Results",
                     use_container_width=True,
                     key="reset_top"):
            st.session_state.result          = None
            st.session_state.approval_status = "PENDING"
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.demo_mode:
            st.markdown(
                '<div class="mode-banner mode-sim">Simulation mode</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="mode-banner mode-live">Live data mode</div>',
                unsafe_allow_html=True
            )

# Handle analyze button
if uploaded_file is not None and analyze_btn_top:
    st.session_state.approval_status = "PENDING"
    with st.spinner("Running analysis across all data sources..."):
        kind   = st.session_state.current_file_kind or _guess_kind(uploaded_file)
        result = run_pipeline(
            uploaded_file, kind,
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

st.markdown("---")

# ─────────────────────────────────────────────
# RESULTS SECTION (Full Width)
# ─────────────────────────────────────────────
result = st.session_state.result

if result is None:
    st.markdown("""
    <div style="color: #aaa; font-size: 0.9rem;
                padding: 1.5rem 0; text-align: center;">
        Results will appear here after analysis.
    </div>
    """, unsafe_allow_html=True)
else:
    tab_result, tab_log = st.tabs(["Current Result", "Incident Log"])

    # ══════════════════════════════════════════
    # TAB 1: CURRENT RESULT
    # ══════════════════════════════════════════
    with tab_result:

        # ── Row 1: Detection + Risk Score side by side ──
        det_col, risk_col = st.columns([1, 1], gap="large")

        with det_col:
            st.markdown(
                '<div class="section-title">Visual Detection</div>',
                unsafe_allow_html=True
            )
            detected    = result.get("detected", "NO")
            badge_class = "badge-yes" if detected == "YES" else "badge-no"
            conf_pct    = float(result.get("confidence", 0)) * 100

            st.markdown(f"""
            <div class="data-row">
                <span class="data-label">Detected</span>
                <span class="detection-badge {badge_class}">{detected}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Type</span>
                <span class="data-value">{result.get('type', '—')}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Severity</span>
                <span class="data-value">{result.get('severity', '—')}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Confidence</span>
                <span class="data-value">{conf_pct:.0f}%</span>
            </div>
            <div class="data-row">
                <span class="data-label">Location</span>
                <span class="data-value">{result.get('location', '—')}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Coordinates</span>
                <span class="data-value">
                    {float(result.get('lat', 0)):.4f},
                    {float(result.get('lon', 0)):.4f}
                </span>
            </div>
            """, unsafe_allow_html=True)

        with risk_col:
            st.markdown(
                '<div class="section-title">Composite Risk Score</div>',
                unsafe_allow_html=True
            )
            composite  = float(result.get("composite_score", 0))
            r_level    = result.get("risk_level", "UNKNOWN")
            dq         = result.get("data_quality", {})
            css_cls    = risk_css_class(r_level)

            action_map = {
                "CRITICAL": "Immediate evacuation required",
                "HIGH":     "Alert authorities and prepare evacuation",
                "MODERATE": "Monitor closely, prepare response",
                "LOW":      "Routine monitoring",
                "MINIMAL":  "No action needed",
                "UNKNOWN":  "—"
            }
            action_text = action_map.get(r_level.upper(), "—")
            data_source_label = (
                "Simulation data" if dq.get("demo_mode")
                else f"Live — {dq.get('successful', 0)}/{dq.get('total_factors', 0)} sources active"
            )

            st.markdown(f"""
            <div class="risk-score-block {css_cls}">
                <div class="risk-number">{composite:.0f}
                    <span style="font-size:1.2rem;font-weight:400;color:#888;">
                        /100
                    </span>
                </div>
                <div class="risk-level-text"
                     style="color:{risk_color_hex(r_level)};">
                    {r_level}
                </div>
                <div class="risk-action">{action_text}</div>
                <div class="risk-action"
                     style="margin-top:0.4rem;font-size:0.72rem;">
                    {data_source_label}
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(min(1.0, composite / 100))

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Row 2: Factor Breakdown (Full Width) ────────
        factors = result.get("factor_breakdown", {})

        if factors:
            st.markdown(
                '<div class="section-title">Factor Breakdown</div>',
                unsafe_allow_html=True
            )

            factor_meta = {
                "visual":     ("Visual Detection",  "Gemini 2.5 Flash"),
                "weather":    ("Weather",            "OpenWeatherMap"),
                "geological": ("Ground Conditions",  "Open-Meteo + USGS"),
                "historical": ("Historical Pattern", "BMC Records"),
                "forecast":   ("Rain Forecast",      "OpenWeatherMap"),
            }

            # Header row
            hc1, hc2, hc3, hc4 = st.columns([2, 4, 1, 1])
            for col, label in zip(
                [hc1, hc2, hc3, hc4],
                ["Factor", "Score", "Weight", "Contributes"]
            ):
                col.markdown(
                    f'<span style="font-size:0.72rem;color:#aaa;'
                    f'text-transform:uppercase;letter-spacing:0.5px;">'
                    f'{label}</span>',
                    unsafe_allow_html=True
                )

            for key, (label, source) in factor_meta.items():
                fd           = factors.get(key, {})
                score        = float(fd.get("score", 0))
                weight       = float(fd.get("weight", 0))
                has_error    = "error" in fd
                contribution = score * weight
                desc         = fd.get("description", "")

                fc1, fc2, fc3, fc4 = st.columns([2, 4, 1, 1])

                with fc1:
                    st.markdown(
                        f'<div style="font-size:0.83rem;font-weight:600;'
                        f'color:#333;padding-top:6px;">{label}</div>'
                        f'<div style="font-size:0.7rem;color:#aaa;">'
                        f'{source}</div>',
                        unsafe_allow_html=True
                    )
                with fc2:
                    if has_error:
                        st.markdown(
                            '<span style="font-size:0.75rem;color:#f57c00;">'
                            'Unavailable</span>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.progress(
                            min(1.0, score / 100),
                            text=f"{score:.0f}/100"
                        )
                with fc3:
                    st.markdown(
                        f'<div style="font-size:0.82rem;color:#666;'
                        f'padding-top:6px;">{weight:.0%}</div>',
                        unsafe_allow_html=True
                    )
                with fc4:
                    st.markdown(
                        f'<div style="font-size:0.82rem;font-weight:600;'
                        f'color:#555;padding-top:6px;">'
                        f'+{contribution:.1f}</div>',
                        unsafe_allow_html=True
                    )

                if desc and not has_error:
                    st.caption(desc)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Detailed breakdowns (two columns) ────────
            detail_col1, detail_col2 = st.columns(2, gap="large")

            with detail_col1:
                wf = factors.get("weather", {})
                wr = wf.get("raw", {})
                if wr:
                    with st.expander("Weather breakdown"):
                        wc1, wc2 = st.columns(2)
                        wc1.metric("Rainfall",
                                   f"{wr.get('rainfall_mm', 0)} mm/hr")
                        wc2.metric("Humidity",
                                   f"{wr.get('humidity_pct', 0)}%")
                        wc3, wc4 = st.columns(2)
                        wc3.metric("Pressure",
                                   f"{wr.get('pressure_hpa', 0)} hPa")
                        wc4.metric("Wind",
                                   f"{wr.get('wind_speed_ms', 0)} m/s")
                        st.caption(
                            f"Condition: {wr.get('condition', 'N/A')}"
                        )

            with detail_col2:
                gf = factors.get("geological", {})
                gd = gf.get("details", {})
                if gd:
                    with st.expander("Ground conditions breakdown"):
                        gc1, gc2 = st.columns(2)
                        gc1.metric("Soil Moisture",
                                   f"{gd.get('soil_moisture', 0):.3f}")
                        gc2.metric("Status",
                                   gd.get("soil_status", "N/A"))
                        gc3, gc4 = st.columns(2)
                        gc3.metric("Seismic Events",
                                   str(gd.get("seismic_events", 0)))
                        gc4.metric("Max Magnitude",
                                   f"M{gd.get('max_magnitude', 0)}")

            expl = result.get("risk_explanation", "")
            if expl:
                with st.expander("Full scoring explanation"):
                    st.code(expl, language=None)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Row 3: Approval + Protocol side by side ──────
        appr_col, proto_col = st.columns([1, 2], gap="large")

        with appr_col:
            st.markdown(
                '<div class="section-title">Officer Approval</div>',
                unsafe_allow_html=True
            )
            status = st.session_state.approval_status
            status_classes = {
                "PENDING":  "approval-pending",
                "APPROVED": "approval-approved",
                "REJECTED": "approval-rejected"
            }
            status_labels = {
                "PENDING":  "Awaiting officer review",
                "APPROVED": "Approved — cleared for dispatch",
                "REJECTED": "Rejected — alert suppressed"
            }
            st.markdown(
                f'<div class="{status_classes.get(status, "approval-pending")}">'
                f'{status_labels.get(status, status)}'
                f'</div>',
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)
            ap1, ap2 = st.columns(2)
            if ap1.button("Approve", key="approve_btn",
                          use_container_width=True, type="primary"):
                st.session_state.approval_status = "APPROVED"
                st.rerun()
            if ap2.button("Reject", key="reject_btn",
                          use_container_width=True):
                st.session_state.approval_status = "REJECTED"
                st.rerun()

        with proto_col:
            st.markdown(
                '<div class="section-title">NDMA Protocol</div>',
                unsafe_allow_html=True
            )
            protocol_text = result.get("protocol", "")
            if protocol_text:
                st.info(protocol_text)
            else:
                st.markdown(
                    '<span style="font-size:0.85rem;color:#aaa;">'
                    'No protocol retrieved — risk below threshold '
                    'or no hazard detected.</span>',
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Row 4: Alerts + Tweets side by side ──────────
        alert_col, tweet_col = st.columns([1, 1], gap="large")

        with alert_col:
            st.markdown(
                '<div class="section-title">Generated Alert</div>',
                unsafe_allow_html=True
            )
            alert_map = {
                "English": st.session_state.alert_en,
                "Hindi":   st.session_state.alert_hi,
                "Marathi": st.session_state.alert_mr,
            }
            alert_text = alert_map.get(preferred_lang, "")

            if alert_text:
                st.text_area(
                    "alert_display",
                    value=alert_text,
                    height=100,
                    label_visibility="collapsed"
                )
                st.caption(f"{preferred_lang} · {len(alert_text)} characters")
            else:
                st.markdown(
                    '<span style="font-size:0.85rem;color:#aaa;">'
                    'No alert generated.</span>',
                    unsafe_allow_html=True
                )

            with st.expander("All languages"):
                st.markdown("**English**")
                st.write(st.session_state.alert_en or "—")
                st.markdown("**Hindi**")
                st.write(st.session_state.alert_hi or "—")
                st.markdown("**Marathi**")
                st.write(st.session_state.alert_mr or "—")

        with tweet_col:
            st.markdown(
                '<div class="section-title">Social Media Drafts</div>',
                unsafe_allow_html=True
            )
            st.caption("Public")
            pub = st.text_area(
                "public_tweet",
                value=st.session_state.tweet_public,
                height=80,
                label_visibility="collapsed",
                key="pub_tweet"
            )
            char_color = "red" if len(pub) > 280 else "#888"
            st.markdown(
                f'<span style="font-size:0.75rem;color:{char_color};">'
                f'{len(pub)}/280</span>',
                unsafe_allow_html=True
            )
            st.caption("Authority")
            auth = st.text_area(
                "auth_tweet",
                value=st.session_state.tweet_authority,
                height=80,
                label_visibility="collapsed",
                key="auth_tweet"
            )
            char_color = "red" if len(auth) > 280 else "#888"
            st.markdown(
                f'<span style="font-size:0.75rem;color:{char_color};">'
                f'{len(auth)}/280</span>',
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Row 5: PDF Export ─────────────────────────────
        st.markdown(
            '<div class="section-title">Export</div>',
            unsafe_allow_html=True
        )
        exp_col, _ = st.columns([1, 3])
        with exp_col:
            if st.button("Generate PDF Report", use_container_width=True):
                with st.spinner("Generating..."):
                    try:
                        from backend.utils.report_generator import generate_report
                        out_path = generate_report(result)
                        if out_path and os.path.exists(out_path):
                            with open(out_path, "rb") as f:
                                st.download_button(
                                    "Download Report",
                                    data=f,
                                    file_name=os.path.basename(out_path),
                                    mime="application/pdf",
                                    key="dl_pdf"
                                )
                        else:
                            st.error("PDF generation failed.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ══════════════════════════════════════════
    # TAB 2: INCIDENT LOG
    # ══════════════════════════════════════════
    with tab_log:
        if not st.session_state.incidents:
            st.info("No incidents recorded yet.")
        else:
            options = [
                f"{i['id']}  |  "
                f"{i.get('time') or i.get('timestamp', '')}  |  "
                f"{i.get('location', '—')}  |  "
                f"{i.get('type', '—')}  |  "
                f"Risk {float(i.get('composite_risk_score', 0) or 0):.0f}/100"
                for i in st.session_state.incidents
            ]
            selected    = st.selectbox(
                "Select incident", options,
                label_visibility="collapsed"
            )
            selected_id = selected.split("|")[0].strip()
            chosen = next(
                (i for i in st.session_state.incidents
                 if i["id"] == selected_id), None
            )

            if chosen:
                lc1, lc2, lc3, lc4 = st.columns(4)
                lc1.metric("Type",      chosen.get("type", "—"))
                lc2.metric("Severity",  chosen.get("severity", "—"))
                lc3.metric("Confidence",
                           f"{float(chosen.get('confidence', 0))*100:.0f}%")
                lc4.metric("Risk Score",
                           f"{float(chosen.get('composite_risk_score', 0) or 0):.0f}/100")

                st.markdown(f"""
                <div class="data-row">
                    <span class="data-label">Location</span>
                    <span class="data-value">{chosen.get('location', '—')}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Time</span>
                    <span class="data-value">
                        {chosen.get('time') or chosen.get('timestamp', '—')}
                    </span>
                </div>
                <div class="data-row">
                    <span class="data-label">Risk Level</span>
                    <span class="data-value"
                          style="color:{risk_color_hex(chosen.get('risk_level', ''))};">
                        {chosen.get('risk_level', '—')}
                    </span>
                </div>
                <div class="data-row">
                    <span class="data-label">Approval</span>
                    <span class="data-value">
                        {chosen.get('approval_status', '—')}
                    </span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                log_d1, log_d2 = st.columns(2, gap="large")

                wd = chosen.get("weather_data", {})
                gd = chosen.get("geo_data", {})

                with log_d1:
                    if wd and isinstance(wd, dict):
                        with st.expander("Weather at time of incident"):
                            wc1, wc2 = st.columns(2)
                            wc1.metric("Rainfall",
                                       f"{wd.get('rainfall_mm', 0)} mm/hr")
                            wc2.metric("Humidity",
                                       f"{wd.get('humidity_pct', 0)}%")
                            wc3, wc4 = st.columns(2)
                            wc3.metric("Pressure",
                                       f"{wd.get('pressure_hpa', 0)} hPa")
                            wc4.metric("Wind",
                                       f"{wd.get('wind_speed_ms', 0)} m/s")

                with log_d2:
                    if gd and isinstance(gd, dict):
                        with st.expander("Ground conditions at time of incident"):
                            gc1, gc2 = st.columns(2)
                            gc1.metric("Soil Moisture",
                                       f"{gd.get('soil_moisture', 0):.3f}")
                            gc2.metric("Status",
                                       gd.get("soil_status", "N/A"))
                            gc3, _ = st.columns(2)
                            gc3.metric("Seismic Events",
                                       str(gd.get("seismic_events", 0)))

                if chosen.get("protocol"):
                    with st.expander("NDMA Protocol"):
                        st.info(chosen["protocol"])

                if chosen.get("alert_en"):
                    with st.expander("Generated alerts"):
                        st.markdown("**English**")
                        st.write(chosen.get("alert_en", "—"))
                        st.markdown("**Hindi**")
                        st.write(chosen.get("alert_hi", "—"))
                        st.markdown("**Marathi**")
                        st.write(chosen.get("alert_mr", "—"))