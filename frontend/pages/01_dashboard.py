import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.database.incident_store import (
    get_all_incidents, get_stats, update_approval
)

st.set_page_config(
    page_title="Nivaran - Command Center",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
<style>
html, body { overflow-x: hidden; }

.page-header {
    padding: 1.5rem 0 1rem 0;
    border-bottom: 2px solid #1a73e8;
    margin-bottom: 1.5rem;
}
.page-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #1a1a1a;
}
.page-subtitle {
    font-size: 0.85rem;
    color: #666;
    margin-top: 0.3rem;
}
.section-title {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #888;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #eee;
    margin-bottom: 1rem;
}
.kpi-card {
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.kpi-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1a1a1a;
    line-height: 1;
}
.kpi-label {
    font-size: 0.72rem;
    color: #888;
    margin-top: 0.3rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.incident-card-pending {
    border: 1px solid #ffe082;
    border-left: 4px solid #f9a825;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    background: #fffdf5;
}
.incident-card-approved {
    border: 1px solid #a5d6a7;
    border-left: 4px solid #388e3c;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    background: #f9fdf9;
}
.incident-card-rejected {
    border: 1px solid #ef9a9a;
    border-left: 4px solid #d32f2f;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    background: #fdf9f9;
}
.data-row {
    display: flex;
    justify-content: space-between;
    padding: 0.3rem 0;
    border-bottom: 1px solid #f5f5f5;
    font-size: 0.82rem;
}
.data-label { color: #888; }
.data-value { font-weight: 600; color: #1a1a1a; }
.status-pending  { color: #f57f17; font-weight: 600; }
.status-approved { color: #2e7d32; font-weight: 600; }
.status-rejected { color: #c62828; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="page-title">Command Center</div>
    <div class="page-subtitle">
        Officer approval queue — review and dispatch flood alerts
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
# Always reload fresh from DB
all_incidents = get_all_incidents()
stats         = get_stats()
by_type       = stats.get("by_type", {})
by_severity   = stats.get("by_severity", {})

pending   = [i for i in all_incidents if i.get("approval_status") == "PENDING"
             and i.get("detected") == "YES"]
approved  = [i for i in all_incidents if i.get("approval_status") == "APPROVED"]
rejected  = [i for i in all_incidents if i.get("approval_status") == "REJECTED"]

# ─────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)

def kpi(col, value, label, highlight=False):
    color = "#d32f2f" if highlight and int(value) > 0 else "#1a1a1a"
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value" style="color:{color};">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

kpi(k1, stats.get("total", 0),     "Total Incidents")
kpi(k2, len(pending),              "Pending Approval", highlight=True)
kpi(k3, len(approved),             "Approved")
kpi(k4, len(rejected),             "Rejected")
kpi(k5, by_type.get("Flood", 0),   "Flood")
kpi(k6, by_severity.get("High", 0),"High Severity", highlight=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab_pending, tab_approved, tab_rejected, tab_all = st.tabs([
    f"Pending ({len(pending)})",
    f"Approved ({len(approved)})",
    f"Rejected ({len(rejected)})",
    f"All Incidents ({len(all_incidents)})"
])


# ─────────────────────────────────────────────
# HELPER: RENDER INCIDENT FOR APPROVAL
# ─────────────────────────────────────────────
def render_approval_card(incident: dict, show_actions: bool = True, tab_key: str = ""):
    inc_id     = incident.get("id", "—")
    status     = incident.get("approval_status", "PENDING")
    risk_level = incident.get("risk_level", "UNKNOWN")
    composite  = float(incident.get("composite_risk_score", 0) or 0)
    confidence = float(incident.get("confidence", 0)) * 100

    risk_colors = {
        "CRITICAL": "#d32f2f",
        "HIGH":     "#f57c00",
        "MODERATE": "#f9a825",
        "LOW":      "#388e3c"
    }
    border_color = risk_colors.get(risk_level, "#ccc")

    card_class = {
        "PENDING":  "incident-card-pending",
        "APPROVED": "incident-card-approved",
        "REJECTED": "incident-card-rejected"
    }.get(status, "incident-card-pending")

    # Card header
    st.markdown(f"""
    <div class="{card_class}">
        <div style="display:flex;justify-content:space-between;
                    align-items:flex-start;">
            <div>
                <div style="font-size:0.9rem;font-weight:700;color:#1a1a1a;">
                    {inc_id}
                </div>
                <div style="font-size:0.78rem;color:#666;margin-top:0.2rem;">
                    {incident.get('location','—')} &nbsp;·&nbsp;
                    {incident.get('time') or incident.get('timestamp','—')}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.6rem;font-weight:800;
                            color:{border_color};line-height:1;">
                    {composite:.0f}
                    <span style="font-size:0.9rem;font-weight:400;
                                 color:#aaa;">/100</span>
                </div>
                <div style="font-size:0.7rem;color:#888;">{risk_level}</div>
            </div>
        </div>
        <div style="margin-top:0.6rem;font-size:0.78rem;color:#555;
                    display:flex;gap:2rem;flex-wrap:wrap;">
            <span>Type: <b>{incident.get('type','—')}</b></span>
            <span>Severity: <b>{incident.get('severity','—')}</b></span>
            <span>Confidence: <b>{confidence:.0f}%</b></span>
            <span>Source: <b>{incident.get('media_kind','—')}</b></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Expandable full details
    with st.expander(f"Review details — {inc_id}"):

        # Row 1: Alerts + Tweets
        al_col, tw_col = st.columns(2, gap="large")

        with al_col:
            st.markdown(
                '<div class="section-title">Generated Alerts</div>',
                unsafe_allow_html=True
            )
            st.markdown("**English**")
            st.write(incident.get("alert_en") or "Not generated")
            st.markdown("**Hindi**")
            st.write(incident.get("alert_hi") or "Not generated")
            st.markdown("**Marathi**")
            st.write(incident.get("alert_mr") or "Not generated")

        with tw_col:
            st.markdown(
                '<div class="section-title">Tweet Drafts</div>',
                unsafe_allow_html=True
            )
            pub  = incident.get("tweet_public", "") or ""
            auth = incident.get("tweet_authority", "") or ""

            st.markdown("**Public**")
            st.write(pub or "Not generated")
            if pub:
                col_len, _ = st.columns([1, 3])
                char_color = "red" if len(pub) > 280 else "#888"
                col_len.markdown(
                    f'<span style="font-size:0.72rem;color:{char_color};">'
                    f'{len(pub)}/280</span>',
                    unsafe_allow_html=True
                )

            st.markdown("**Authority**")
            st.write(auth or "Not generated")
            if auth:
                col_len2, _ = st.columns([1, 3])
                char_color2 = "red" if len(auth) > 280 else "#888"
                col_len2.markdown(
                    f'<span style="font-size:0.72rem;color:{char_color2};">'
                    f'{len(auth)}/280</span>',
                    unsafe_allow_html=True
                )

        # Row 2: Protocol (full width)
        st.markdown(
            '<div class="section-title" style="margin-top:1rem;">'
            'NDMA Protocol</div>',
            unsafe_allow_html=True
        )
        protocol = incident.get("protocol", "")
        if protocol and protocol != "No disaster detected. No action required.":
            st.info(protocol)
        else:
            st.caption("No protocol retrieved for this incident.")

        # Row 3: Data breakdown
        st.markdown(
            '<div class="section-title" style="margin-top:1rem;">'
            'Supporting Data</div>',
            unsafe_allow_html=True
        )

        sd1, sd2, sd3 = st.columns(3)

        with sd1:
            st.markdown(f"""
            <div class="data-row">
                <span class="data-label">Composite Score</span>
                <span class="data-value">{composite:.0f}/100</span>
            </div>
            <div class="data-row">
                <span class="data-label">Risk Level</span>
                <span class="data-value"
                      style="color:{border_color};">{risk_level}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Coordinates</span>
                <span class="data-value">
                    {float(incident.get('lat',0)):.4f},
                    {float(incident.get('lon',0)):.4f}
                </span>
            </div>
            """, unsafe_allow_html=True)

        with sd2:
            wd = incident.get("weather_data", {})
            if isinstance(wd, dict) and wd:
                st.markdown(f"""
                <div class="data-row">
                    <span class="data-label">Rainfall</span>
                    <span class="data-value">
                        {wd.get('rainfall_mm', 0)} mm/hr
                    </span>
                </div>
                <div class="data-row">
                    <span class="data-label">Humidity</span>
                    <span class="data-value">
                        {wd.get('humidity_pct', 0)}%
                    </span>
                </div>
                <div class="data-row">
                    <span class="data-label">Pressure</span>
                    <span class="data-value">
                        {wd.get('pressure_hpa', 0)} hPa
                    </span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption("Weather data not available")

        with sd3:
            gd = incident.get("geo_data", {})
            if isinstance(gd, dict) and gd:
                st.markdown(f"""
                <div class="data-row">
                    <span class="data-label">Soil Moisture</span>
                    <span class="data-value">
                        {float(gd.get('soil_moisture', 0)):.3f}
                    </span>
                </div>
                <div class="data-row">
                    <span class="data-label">Soil Status</span>
                    <span class="data-value">
                        {gd.get('soil_status', '—')}
                    </span>
                </div>
                <div class="data-row">
                    <span class="data-label">Seismic Events</span>
                    <span class="data-value">
                        {gd.get('seismic_events', 0)}
                    </span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption("Ground data not available")

        # Row 4: Approval actions
        if show_actions:
            st.markdown(
                '<div class="section-title" style="margin-top:1rem;">'
                'Officer Decision</div>',
                unsafe_allow_html=True
            )

            current_status = incident.get("approval_status", "PENDING")

            if current_status == "PENDING":
                ac1, ac2, ac3 = st.columns([1, 1, 2])
                if ac1.button(
                "Approve",
                key=f"approve_{inc_id}_{tab_key}",
                type="primary",
                use_container_width=True
            ):
                    update_approval(inc_id, "APPROVED", "Duty Officer")
                    st.success(f"{inc_id} approved. Alert cleared for dispatch.")
                    st.rerun()

                if ac2.button(
                "Reject",
                key=f"reject_{inc_id}_{tab_key}",
                use_container_width=True
            ):
                    update_approval(inc_id, "REJECTED", "Duty Officer")
                    st.warning(f"{inc_id} rejected. Alert suppressed.")
                    st.rerun()

            elif current_status == "APPROVED":
                st.markdown(
                    '<div style="background:#e8f5e9;border:1px solid #a5d6a7;'
                    'border-radius:6px;padding:0.5rem 1rem;'
                    'font-size:0.82rem;color:#2e7d32;">'
                    'Approved — alert cleared for dispatch'
                    '</div>',
                    unsafe_allow_html=True
                )
                # Allow re-review
                if st.button(
                    "Revoke approval",
                    key=f"revoke_{inc_id}_{tab_key}",
                ):
                    update_approval(inc_id, "PENDING", "")
                    st.rerun()

            elif current_status == "REJECTED":
                st.markdown(
                    '<div style="background:#fdecea;border:1px solid #ef9a9a;'
                    'border-radius:6px;padding:0.5rem 1rem;'
                    'font-size:0.82rem;color:#c62828;">'
                    'Rejected — alert suppressed'
                    '</div>',
                    unsafe_allow_html=True
                )
                if st.button(
                "Re-open for review",
                key=f"reopen_{inc_id}_{tab_key}",
            ):
                    update_approval(inc_id, "PENDING", "")
                    st.rerun()


# ─────────────────────────────────────────────
# TAB 1: PENDING
# ─────────────────────────────────────────────
with tab_pending:
    if not pending:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#aaa;
                    font-size:0.9rem;">
            No incidents awaiting approval.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption(
            f"{len(pending)} incident(s) require officer review "
            "before alerts can be dispatched."
        )
        st.markdown("<br>", unsafe_allow_html=True)
        for incident in pending:
            render_approval_card(incident, show_actions=True, tab_key="pending")


# ─────────────────────────────────────────────
# TAB 2: APPROVED
# ─────────────────────────────────────────────
with tab_approved:
    if not approved:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#aaa;
                    font-size:0.9rem;">
            No approved incidents yet.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption(f"{len(approved)} incident(s) approved for dispatch.")
        st.markdown("<br>", unsafe_allow_html=True)
        for incident in approved:
            render_approval_card(incident, show_actions=True, tab_key="approved")


# ─────────────────────────────────────────────
# TAB 3: REJECTED
# ─────────────────────────────────────────────
with tab_rejected:
    if not rejected:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#aaa;
                    font-size:0.9rem;">
            No rejected incidents.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption(f"{len(rejected)} incident(s) rejected.")
        st.markdown("<br>", unsafe_allow_html=True)
        for incident in rejected:
            render_approval_card(incident, show_actions=True, tab_key="rejected")


# ─────────────────────────────────────────────
# TAB 4: ALL INCIDENTS
# ─────────────────────────────────────────────
with tab_all:
    if not all_incidents:
        st.info("No incidents recorded yet.")
    else:
        st.caption(f"{len(all_incidents)} total incident(s) in the database.")
        st.markdown("<br>", unsafe_allow_html=True)
        for incident in all_incidents:
            render_approval_card(incident, show_actions=True, tab_key="all")


# ─────────────────────────────────────────────
# SYSTEM STATUS
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div class="section-title">System Status</div>',
    unsafe_allow_html=True
)

s1, s2, s3, s4, s5 = st.columns(5)
s1.success("Vision Agent")
s2.success("RAG Agent")
s3.success("Alert Generator")
s4.success("Weather Agent")
s5.success("Database")