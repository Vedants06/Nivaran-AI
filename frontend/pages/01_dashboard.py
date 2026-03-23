# frontend/pages/01_dashboard.py
import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.database.incident_store import get_all_incidents, get_stats

st.set_page_config(page_title="Nivaran - Home", page_icon="🛡️", layout="wide")

st.title("🛡️ Nivaran — Disaster Command Center")
st.caption("AI-powered real-time disaster detection for Mumbai.")

st.divider()

# ── Live Stats from DB ──────────────────────────────────
stats = get_stats()
by_type     = stats.get("by_type", {})
by_severity = stats.get("by_severity", {})

st.subheader("📊 System Overview")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📌 Total Incidents",  stats.get("total", 0))
c2.metric("🌧️ Floods",          by_type.get("Flood", 0))
c3.metric("⛰️ Landslides",       by_type.get("Landslide", 0))
c4.metric("🔥 Fires",            by_type.get("Fire", 0))
c5.metric("🔴 High Severity",    by_severity.get("High", 0))

st.divider()

# ── Navigation Cards ────────────────────────────────────
st.subheader("🧭 Navigate to")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    ### 🛡️ Dashboard
    Upload images or videos, analyze disasters, generate alerts and tweets.
    """)
    st.page_link("app.py", label="Go to Dashboard →", icon="🛡️")

with col2:
    st.markdown("""
    ### 🎥 Video Monitor
    Run multi-camera CCTV simulation with live confidence graphs.
    """)
    st.page_link("pages/03_video_monitor.py", label="Go to Video Monitor →", icon="🎥")

with col3:
    st.markdown("""
    ### 📊 Analytics
    View incident heatmap, charts, and zone risk scores.
    """)
    st.page_link("pages/04_analytics.py", label="Go to Analytics →", icon="📊")

with col4:
    st.markdown("""
    ### 📋 Recent Incidents
    View the last 5 incidents logged in the system.
    """)

st.divider()

# ── Recent Incidents Table ──────────────────────────────
st.subheader("📋 Recent Incidents")

incidents = get_all_incidents()

if not incidents:
    st.info("No incidents recorded yet. Go to Dashboard and analyze an image.")
else:
    recent = incidents[:10]

    for inc in recent:
        sev = inc.get("severity", "").lower()
        if sev == "high":
            icon = "🔴"
        elif sev == "medium":
            icon = "🟠"
        else:
            icon = "🟢"

        status = inc.get("approval_status", "PENDING")
        status_icon = "✅" if status == "APPROVED" else ("❌" if status == "REJECTED" else "🟡")

        with st.expander(
            f"{icon} {inc.get('id')} | {inc.get('type','—')} | {inc.get('location','—')} | {inc.get('timestamp') or inc.get('time','—')} | {status_icon} {status}"
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("Type",       inc.get("type", "—"))
            c2.metric("Severity",   inc.get("severity", "—"))
            c3.metric("Confidence", f"{float(inc.get('confidence', 0))*100:.0f}%")

            st.write(f"**📍 Location:** {inc.get('location','—')}")
            st.write(f"**🕒 Time:** {inc.get('timestamp') or inc.get('time','—')}")

            if inc.get("protocol"):
                st.markdown("**📘 Protocol (summary):**")
                st.info(inc["protocol"][:300] + "..." if len(inc.get("protocol","")) > 300 else inc["protocol"])

            if inc.get("alert_en"):
                st.markdown("**🌐 Alert (EN):**")
                st.success(inc["alert_en"])

# ── System Status ───────────────────────────────────────
st.divider()
st.subheader("⚙️ System Status")

s1, s2, s3, s4 = st.columns(4)
s1.success("✅ Vision Agent (Gemini)")
s2.success("✅ RAG Agent (Pinecone + Groq)")
s3.success("✅ Alert Generator (Groq)")
s4.success("✅ Database (SQLite)")