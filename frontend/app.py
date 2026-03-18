import streamlit as st
from PIL import Image
from datetime import datetime
import folium
from streamlit_folium import st_folium
from graph import app as nivaran_graph
import tempfile
import os
import requests


# ---------------- Page config ----------------
st.set_page_config(
    page_title="Nivaran - UI Mockup",
    page_icon="🛡️",
    layout="wide"
)

# ---------------- Stabilize layout (STOP left-right shaking) ----------------
st.markdown(
    """
    <style>
    html { overflow-y: scroll; }
    body, .main, .block-container { overflow-x: hidden !important; }
    iframe { border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🛡️ Nivaran: Disaster Response Dashboard")
st.caption("UI Mockup: Upload image/video + map marker + incident log + language selector (no backend yet).")


# ---------------- Session state (MUST be before usage) ----------------
def ss_init(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


ss_init("result", None)
ss_init("approval_status", "PENDING")
ss_init("incidents", [])
ss_init("location_text", "")
ss_init("lat", 19.0760)       # Mumbai default
ss_init("lon", 72.8777)       # Mumbai default
ss_init("alert_en", "")
ss_init("alert_hi", "")
ss_init("alert_mr", "")
ss_init("tweet_public", "")
ss_init("tweet_authority", "")
ss_init("map_expanded", False)
ss_init("uploader_key", 1)
ss_init("uploaded_once", False)
ss_init("current_file", None)
ss_init("current_file_kind", None)  # "image" or "video"

# NEW: geocoding / map centering
ss_init("map_center_lat", 19.0760)
ss_init("map_center_lon", 72.8777)
ss_init("last_search_name", "")
ss_init("last_search_lat", None)
ss_init("last_search_lon", None)
ss_init("last_search_address", "")


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


def _incidents_hashable(incidents_list):
    return tuple(tuple(sorted(i.items())) for i in incidents_list)


def _save_uploaded_to_temp(uploaded_file, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def _guess_kind_and_suffix(uploaded_file) -> tuple[str, str]:
    name = (uploaded_file.name or "").lower()
    if name.endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
        ext = os.path.splitext(name)[1] or ".mp4"
        return "video", ext
    ext = os.path.splitext(name)[1] or ".jpg"
    return "image", ext


# ---------------- Geocoding (Location name -> Lat/Lon) ----------------
@st.cache_data(show_spinner=False)
def geocode_place(place_name: str):
    """
    Uses OpenStreetMap Nominatim geocoding.
    Returns: (lat, lon, display_name) or (None, None, "")
    """
    place_name = (place_name or "").strip()
    if not place_name:
        return None, None, ""

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place_name,
        "format": "json",
        "limit": 1
    }
    # Nominatim requires a User-Agent
    headers = {
        "User-Agent": "Nivaran-Streamlit-Dashboard/1.0 (educational project)"
    }

    r = requests.get(url, params=params, headers=headers, timeout=12)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None, None, ""

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    display_name = data[0].get("display_name", "")
    return lat, lon, display_name


# ---------------- Map builder (cached) ----------------
@st.cache_data(show_spinner=False)
def build_map_cached(incidents_hashable, center_lat, center_lon, zoom=11, searched_marker=None):
    """
    searched_marker: dict like {"name": "...", "lat":..., "lon":..., "address":...} or None
    """
    incidents = [dict(t) for t in incidents_hashable]
    m = folium.Map(location=[float(center_lat), float(center_lon)], zoom_start=zoom)

    # Searched location marker
    if searched_marker and searched_marker.get("lat") is not None and searched_marker.get("lon") is not None:
        popup = f"""
        <b>Searched:</b> {searched_marker.get('name', '')}<br>
        <b>Lat:</b> {searched_marker.get('lat')}<br>
        <b>Lon:</b> {searched_marker.get('lon')}<br>
        <small>{searched_marker.get('address','')}</small>
        """
        folium.Marker(
            location=[searched_marker["lat"], searched_marker["lon"]],
            popup=popup,
            tooltip="Searched Location",
            icon=folium.Icon(color="green", icon="info-sign"),
        ).add_to(m)

    # Incident markers
    for incident in incidents:
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

    return m


# ---------------- Mock pipeline (Vedant will replace later) ----------------
def run_pipeline(uploaded_file, kind: str, location_text: str) -> dict:
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
        "tweet_public": result.get("tweet_public", ""),
        "tweet_authority": result.get("tweet_authority", ""),
        "media_kind": kind,
        "media_name": getattr(uploaded_file, "name", "unknown"),
    }

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
        "tweet_public": result.get("tweet_public", ""),       # ← NEW
        "tweet_authority": result.get("tweet_authority", ""), # ← NEW
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

# Location search box (this powers map search)
st.session_state.location_text = st.sidebar.text_input(
    "Enter location name (example: Kurla Station / Andheri Subway / Gateway of India)",
    value=st.session_state.location_text
)

# Search button -> geocode -> updates lat/lon + centers map + shows marker
colA, colB = st.sidebar.columns([1, 1])
search_btn = colA.button("🔎 Search Location", use_container_width=True)
clear_search_btn = colB.button("🧽 Clear", use_container_width=True)

if clear_search_btn:
    st.session_state.last_search_name = ""
    st.session_state.last_search_lat = None
    st.session_state.last_search_lon = None
    st.session_state.last_search_address = ""
    st.session_state.map_center_lat = st.session_state.lat
    st.session_state.map_center_lon = st.session_state.lon

if search_btn:
    query = st.session_state.location_text.strip()
    if not query:
        st.sidebar.warning("Please type a location name first.")
    else:
        try:
            with st.sidebar.spinner("Searching location..."):
                lat, lon, display_name = geocode_place(query)
            if lat is None or lon is None:
                st.sidebar.error("Location not found. Try a more famous/complete name.")
            else:
                # Update both coordinate inputs AND map center
                st.session_state.lat = float(lat)
                st.session_state.lon = float(lon)
                st.session_state.map_center_lat = float(lat)
                st.session_state.map_center_lon = float(lon)

                st.session_state.last_search_name = query
                st.session_state.last_search_lat = float(lat)
                st.session_state.last_search_lon = float(lon)
                st.session_state.last_search_address = display_name or ""

                st.sidebar.success("Location found ✅")
        except Exception as e:
            st.sidebar.error(f"Geocoding failed: {e}")

# Coordinates (auto-filled by search, but still editable)
st.sidebar.subheader("📌 Coordinates (auto-filled by search, editable)")
st.session_state.lat = st.sidebar.number_input("Latitude", value=float(st.session_state.lat), format="%.6f")
st.session_state.lon = st.sidebar.number_input("Longitude", value=float(st.session_state.lon), format="%.6f")

# If user edits lat/lon manually, re-center map on those
st.session_state.map_center_lat = float(st.session_state.lat)
st.session_state.map_center_lon = float(st.session_state.lon)

# Show resolved address info
if st.session_state.last_search_lat is not None and st.session_state.last_search_lon is not None:
    st.sidebar.caption("✅ Latest Search Result")
    st.sidebar.write(f"**Place:** {st.session_state.last_search_name}")
    st.sidebar.write(f"**Lat/Lon:** {st.session_state.last_search_lat:.6f}, {st.session_state.last_search_lon:.6f}")
    if st.session_state.last_search_address:
        st.sidebar.caption(st.session_state.last_search_address)

st.sidebar.subheader("🌐 Preferred Alert Language")
preferred_lang = st.sidebar.radio("Select language", ["English", "Hindi", "Marathi"], index=0)

st.sidebar.caption("Tip: Type a famous location name and click Search. Map will center and pin it.")


# --- Sidebar Map (small, stable) ---
st.sidebar.markdown("---")
with st.sidebar.expander("🗺️ Live Map View (click to expand)", expanded=True):
    searched_marker = None
    if st.session_state.last_search_lat is not None and st.session_state.last_search_lon is not None:
        searched_marker = {
            "name": st.session_state.last_search_name,
            "lat": st.session_state.last_search_lat,
            "lon": st.session_state.last_search_lon,
            "address": st.session_state.last_search_address,
        }

    inc_hash = _incidents_hashable(st.session_state.incidents)
    small_map = build_map_cached(
        inc_hash,
        st.session_state.map_center_lat,
        st.session_state.map_center_lon,
        zoom=13 if searched_marker else 11,
        searched_marker=searched_marker
    )

    st_folium(small_map, width=320, height=220, key="sidebar_map_static")

    if st.button("🔍 Expand Map", use_container_width=True):
        st.session_state.map_expanded = True


# ---------------- Expanded Map (Center Popup) ----------------
if st.session_state.map_expanded:
    try:
        @st.dialog("🗺️ Expanded Live Map View")
        def show_big_map():
            searched_marker = None
            if st.session_state.last_search_lat is not None and st.session_state.last_search_lon is not None:
                searched_marker = {
                    "name": st.session_state.last_search_name,
                    "lat": st.session_state.last_search_lat,
                    "lon": st.session_state.last_search_lon,
                    "address": st.session_state.last_search_address,
                }

            inc_hash2 = _incidents_hashable(st.session_state.incidents)
            big_map = build_map_cached(
                inc_hash2,
                st.session_state.map_center_lat,
                st.session_state.map_center_lon,
                zoom=14 if searched_marker else 11,
                searched_marker=searched_marker
            )

            st.caption("Searched location pin is GREEN. Incidents are colored by type.")
            st_folium(big_map, width=1200, height=820, key="big_map_static")

            if st.button("✖ Close Map"):
                st.session_state.map_expanded = False

        show_big_map()
    except Exception:
        st.warning("Your Streamlit version does not support dialog popups. Update Streamlit to latest.")
        st.session_state.map_expanded = False


# ---------------- Main uploader (hide after upload) ----------------
uploaded_file = None
if not st.session_state.uploaded_once:
    uploaded_file = st.file_uploader(
        "Upload a CCTV/Drone/Public image OR video (jpg/png/mp4/mov/mkv/avi/webm)",
        type=["jpg", "jpeg", "png", "mp4", "mov", "mkv", "avi", "webm"],
        key=f"uploader_{st.session_state.uploader_key}",
    )
    if uploaded_file is not None:
        kind, _ = _guess_kind_and_suffix(uploaded_file)
        st.session_state.uploaded_once = True
        st.session_state.current_file = uploaded_file
        st.session_state.current_file_kind = kind
        st.rerun()
else:
    uploaded_file = st.session_state.current_file


left, right = st.columns([1, 1])


# ---------------- LEFT: Preview media + analyze different media button ----------------
with left:
    st.subheader("📎 Uploaded Media")

    if uploaded_file is None:
        st.info("No media uploaded yet.")
    else:
        kind = st.session_state.current_file_kind or _guess_kind_and_suffix(uploaded_file)[0]

        if kind == "video":
            st.video(uploaded_file)
            st.caption(f"🎬 Video: {uploaded_file.name}")
        else:
            img = Image.open(uploaded_file)
            st.image(img, caption="Image received ✅", use_container_width=True)

        if st.button("📤 Analyze different image/video", use_container_width=True):
            st.session_state.result = None
            st.session_state.approval_status = "PENDING"
            st.session_state.uploaded_once = False
            st.session_state.current_file = None
            st.session_state.current_file_kind = None
            st.session_state.uploader_key += 1
            st.rerun()


# ---------------- RIGHT: Output + actions ----------------
with right:
    st.subheader("🤖 AI Output")

    b1, b2 = st.columns([1, 1])
    analyze_btn = b1.button("🚀 Analyze")
    reset_btn = b2.button("🧹 Reset (clear current)")

    if reset_btn:
        st.session_state.result = None
        st.session_state.approval_status = "PENDING"
        st.success("Cleared current result ✅")

    if analyze_btn and uploaded_file is None:
        st.warning("Please upload an image or video first.")

    if analyze_btn and uploaded_file is not None:
        st.session_state.approval_status = "PENDING"
        with st.spinner("AI Agents are thinking..."):
            kind = st.session_state.current_file_kind or _guess_kind_and_suffix(uploaded_file)[0]
            result = run_pipeline(uploaded_file, kind, st.session_state.location_text)
            st.session_state.result = result

            st.session_state.alert_en = result.get("alert_en", "")
            st.session_state.alert_hi = result.get("alert_hi", "")
            st.session_state.alert_mr = result.get("alert_mr", "")
            st.session_state.tweet_public = result.get("tweet_public", "")      # ← ADD
            st.session_state.tweet_authority = result.get("tweet_authority", "") # ← ADD

            incident = {
                "id": f"INC-{len(st.session_state.incidents)+1:03d}",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "location": result.get("location", "Unknown"),
                "lat": float(st.session_state.lat),
                "lon": float(st.session_state.lon),
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
        st.write(f"**📎 Media:** {incident.get('media_kind', '—')} | {incident.get('media_name', '—')}")

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
                value=st.session_state.alert_en,
                height=120,
                key=f"chosen_en_{incident.get('id', 'cur')}"
            )
        elif preferred_lang == "Hindi":
            chosen_alert = st.text_area(
                "Alert (Hindi)",
                value=st.session_state.alert_hi,
                height=120,
                key=f"chosen_hi_{incident.get('id', 'cur')}"
            )
        else:
            chosen_alert = st.text_area(
                "Alert (Marathi)",
                value=st.session_state.alert_mr,
                height=120,
                key=f"chosen_mr_{incident.get('id', 'cur')}"
            )

        st.markdown("### ✅ Human-in-the-Loop Approval")
        a1, a2 = st.columns(2)
        if a1.button("✅ Approve Alert", key=f"appr_{incident.get('id', 'cur')}"):
            st.session_state.approval_status = "APPROVED"
        if a2.button("❌ Reject Alert", key=f"rej_{incident.get('id', 'cur')}"):
            st.session_state.approval_status = "REJECTED"

        st.markdown("### 🐦 Tweet Drafts")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**👥 Public Tweet**")
            public_tweet = st.text_area(
                "For general public",
                value=st.session_state.tweet_public,
                height=140,
                key=f"pub_tweet_{incident.get('id', 'cur')}"
            )
            char1 = len(public_tweet)
            st.caption(f"{char1}/280 characters")
            if char1 > 280:
                st.error("Too long! Shorten it.")
            else:
                st.success("✅ Ready to post")

        with col2:
            st.markdown("**🚨 Authority Tweet**")
            auth_tweet = st.text_area(
                "Tags @RailwayMumbai @MumbaiPolice",
                value=st.session_state.tweet_authority,
                height=140,
                key=f"auth_tweet_{incident.get('id', 'cur')}"
            )
            char2 = len(auth_tweet)
            st.caption(f"{char2}/280 characters")
            if char2 > 280:
                st.error("Too long! Shorten it.")
            else:
                st.success("✅ Ready to post")

        # if len(tweet_text) > 280:
        #     st.error("Tweet is too long! Please shorten the alert.")
        # else:
        #     st.info("Tweet length is OK ✅")

        # st.text_area(
        #     "Tweet Draft (Copy & Paste)",
        #     value=tweet_text,
        #     height=120,
        #     key=f"tweet_{incident.get('id', 'cur')}"
        # )

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
