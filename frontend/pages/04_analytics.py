import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from backend.database.incident_store import get_all_incidents

st.set_page_config(page_title="Nivaran - Analytics", layout="wide")

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
    margin-top: 1.5rem;
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
.zone-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid #f0f0f0;
    font-size: 0.82rem;
}
.zone-row:hover {
    background: #fafafa;
}
.zone-name {
    font-weight: 600;
    color: #1a1a1a;
    flex: 2;
}
.zone-stat {
    color: #555;
    flex: 1;
    text-align: center;
}
.zone-score {
    font-weight: 700;
    flex: 1;
    text-align: right;
}
.risk-high    { color: #d32f2f; }
.risk-medium  { color: #f57c00; }
.risk-low     { color: #388e3c; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="page-title">Analytics</div>
    <div class="page-subtitle">
        Incident trends, severity distribution, risk heatmap,
        and zone-level scoring
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
incidents = get_all_incidents()

if not incidents:
    st.markdown("""
    <div style="text-align:center;padding:4rem;color:#aaa;font-size:0.9rem;">
        No incidents recorded yet. Run an analysis first.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

df = pd.DataFrame(incidents)
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df["date"] = df["timestamp"].dt.date
df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0)
df["composite_risk_score"] = pd.to_numeric(
    df.get("composite_risk_score", 0), errors="coerce"
).fillna(0)

total       = len(df)
floods      = len(df[df["type"] == "Flood"])
landslides  = len(df[df["type"] == "Landslide"])
fires       = len(df[df["type"] == "Fire"])
high_sev    = len(df[df["severity"] == "High"])
avg_risk    = df["composite_risk_score"].mean()
avg_conf    = df["confidence"].mean() * 100
pending     = len(df[df["approval_status"] == "PENDING"])

# ─────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────

def kpi(col, value, label, highlight=False):
    color = "#d32f2f" if highlight and float(value) > 0 else "#1a1a1a"
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value" style="color:{color};">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

k1, k2, k3, k4, k5, k6 = st.columns(6)
kpi(k1, total,               "Total Incidents")
kpi(k2, floods,              "Flood")
kpi(k3, high_sev,            "High Severity", highlight=True)
kpi(k4, f"{avg_risk:.0f}",   "Avg Risk Score")
kpi(k5, f"{avg_conf:.0f}%",  "Avg Confidence")
kpi(k6, pending,             "Pending Review", highlight=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TIME FILTER
# ─────────────────────────────────────────────
st.markdown(
    '<div class="section-title">Time Range</div>',
    unsafe_allow_html=True
)

time_filter = st.radio(
    "time_range",
    ["All Time", "Last 30 Days", "Last 7 Days", "Last 24 Hours"],
    horizontal=True,
    label_visibility="collapsed"
)

filtered_df = df.copy()
if time_filter == "Last 7 Days":
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
    filtered_df = df[df["timestamp"] >= cutoff]
elif time_filter == "Last 30 Days":
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
    filtered_df = df[df["timestamp"] >= cutoff]
elif time_filter == "Last 24 Hours":
    cutoff = pd.Timestamp.now() - pd.Timedelta(hours=24)
    filtered_df = df[df["timestamp"] >= cutoff]

if filtered_df.empty:
    st.markdown("""
    <div style="text-align:center;padding:2rem;color:#aaa;font-size:0.85rem;">
        No incidents in the selected time range.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.caption(f"Showing {len(filtered_df)} incident(s) for: {time_filter}")

# ─────────────────────────────────────────────
# ROW 1: TIMELINE + TYPE BREAKDOWN
# ─────────────────────────────────────────────
st.markdown(
    '<div class="section-title">Incident Trends</div>',
    unsafe_allow_html=True
)

chart1, chart2 = st.columns([3, 2], gap="large")

with chart1:
    daily = filtered_df.groupby("date").size().reset_index(name="count")
    fig_time = px.area(
        daily, x="date", y="count",
        labels={"date": "", "count": "Incidents"},
        color_discrete_sequence=["#1a73e8"]
    )
    fig_time.update_traces(
        line=dict(width=2),
        fillcolor="rgba(26, 115, 232, 0.08)"
    )
    fig_time.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=30, b=20),
        title=dict(text="Incidents over time", font=dict(size=12, color="#888")),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(
            gridcolor="#f5f5f5",
            tickfont=dict(size=10, color="#888")
        ),
        yaxis=dict(
            gridcolor="#f0f0f0",
            tickfont=dict(size=10, color="#888")
        )
    )
    st.plotly_chart(fig_time, use_container_width=True)

with chart2:
    type_counts = filtered_df["type"].value_counts().reset_index()
    type_counts.columns = ["type", "count"]
    type_colors = {
        "Flood": "#1a73e8",
        "Landslide": "#e65100",
        "Fire": "#d32f2f",
        "Infrastructure": "#555",
        "None": "#ccc",
        "Unknown": "#ccc",
        "Error": "#ccc"
    }
    colors = [type_colors.get(t, "#888") for t in type_counts["type"]]

    fig_pie = px.pie(
        type_counts, names="type", values="count",
        color_discrete_sequence=colors,
        hole=0.5
    )
    fig_pie.update_traces(
        textposition="inside",
        textinfo="label+value",
        textfont_size=11
    )
    fig_pie.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=30, b=20),
        title=dict(text="By type", font=dict(size=12, color="#888")),
        showlegend=False
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# ─────────────────────────────────────────────
# ROW 2: SEVERITY + CONFIDENCE + RISK SCORE
# ─────────────────────────────────────────────
st.markdown(
    '<div class="section-title">Distribution Analysis</div>',
    unsafe_allow_html=True
)

chart3, chart4, chart5 = st.columns(3, gap="large")

with chart3:
    sev_counts = filtered_df["severity"].value_counts().reset_index()
    sev_counts.columns = ["severity", "count"]
    sev_color_map = {
        "High":    "#d32f2f",
        "Medium":  "#f57c00",
        "Low":     "#388e3c",
        "Unknown": "#ccc"
    }
    fig_bar = px.bar(
        sev_counts, x="severity", y="count",
        color="severity",
        color_discrete_map=sev_color_map,
        labels={"severity": "", "count": "Count"}
    )
    fig_bar.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=30, b=10),
        title=dict(text="Severity", font=dict(size=12, color="#888")),
        showlegend=False,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(tickfont=dict(size=10)),
        yaxis=dict(gridcolor="#f0f0f0", tickfont=dict(size=10))
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with chart4:
    fig_conf = px.histogram(
        filtered_df, x="confidence", nbins=10,
        labels={"confidence": "Score", "count": ""},
        color_discrete_sequence=["#1a73e8"]
    )
    fig_conf.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=30, b=10),
        title=dict(
            text="AI confidence distribution",
            font=dict(size=12, color="#888")
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(
            range=[0, 1],
            tickfont=dict(size=10)
        ),
        yaxis=dict(gridcolor="#f0f0f0", tickfont=dict(size=10))
    )
    st.plotly_chart(fig_conf, use_container_width=True)

with chart5:
    risk_scores = filtered_df[filtered_df["composite_risk_score"] > 0]
    if not risk_scores.empty:
        fig_risk = px.histogram(
            risk_scores, x="composite_risk_score", nbins=10,
            labels={"composite_risk_score": "Score", "count": ""},
            color_discrete_sequence=["#f57c00"]
        )
        fig_risk.update_layout(
            height=250,
            margin=dict(l=10, r=10, t=30, b=10),
            title=dict(
                text="Composite risk distribution",
                font=dict(size=12, color="#888")
            ),
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(
                range=[0, 100],
                tickfont=dict(size=10)
            ),
            yaxis=dict(gridcolor="#f0f0f0", tickfont=dict(size=10))
        )
        st.plotly_chart(fig_risk, use_container_width=True)
    else:
        st.caption("No composite risk data available yet.")

# ─────────────────────────────────────────────
# ROW 3: HEATMAP
# ─────────────────────────────────────────────
st.markdown(
    '<div class="section-title">Incident Heatmap</div>',
    unsafe_allow_html=True
)

valid = filtered_df.dropna(subset=["lat", "lon"])
valid = valid[(valid["lat"] != 0) & (valid["lon"] != 0)]

if valid.empty:
    st.markdown("""
    <div style="text-align:center;padding:2rem;color:#aaa;font-size:0.85rem;">
        No incidents with valid coordinates in this time range.
    </div>
    """, unsafe_allow_html=True)
else:
    m = folium.Map(
        location=[19.0760, 72.8777],
        zoom_start=11,
        tiles="CartoDB positron"
    )

    heat_data = [
        [row["lat"], row["lon"], min(1.0, row.get("composite_risk_score", 50) / 100)]
        for _, row in valid.iterrows()
    ]
    HeatMap(
        heat_data,
        radius=25,
        blur=18,
        max_zoom=13,
        gradient={
            "0.2": "#1a73e8",
            "0.4": "#4fc3f7",
            "0.6": "#f9a825",
            "0.8": "#f57c00",
            "1.0": "#d32f2f"
        }
    ).add_to(m)

    # Individual markers
    for _, row in valid.iterrows():
        risk_score = float(row.get("composite_risk_score", 0) or 0)
        sev = row.get("severity", "")

        if risk_score >= 70:
            marker_color = "#d32f2f"
        elif risk_score >= 50:
            marker_color = "#f57c00"
        else:
            marker_color = "#1a73e8"

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=6,
            color=marker_color,
            fill=True,
            fill_opacity=0.7,
            popup=(
                f"<b>{row.get('id', '')}</b><br>"
                f"Type: {row.get('type', '')}<br>"
                f"Severity: {sev}<br>"
                f"Risk: {risk_score:.0f}/100<br>"
                f"Location: {row.get('location', '')}<br>"
                f"{row.get('timestamp', '')}"
            )
        ).add_to(m)

    st_folium(m, width=None, height=450, use_container_width=True)
    st.caption(
        f"{len(valid)} incident(s) plotted. "
        "Colors indicate composite risk score."
    )

# ─────────────────────────────────────────────
# ROW 4: ZONE RISK SCORING
# ─────────────────────────────────────────────
st.markdown(
    '<div class="section-title">Zone Risk Assessment</div>',
    unsafe_allow_html=True
)

zone_df = filtered_df[
    (filtered_df["location"].notna()) &
    (filtered_df["location"] != "") &
    (filtered_df["location"] != "Unknown")
]

if zone_df.empty:
    st.caption("No location data available for zone scoring.")
else:
    zone_risk = (
        zone_df.groupby("location")
        .agg(
            total=("id", "count"),
            high_count=("severity", lambda x: (x == "High").sum()),
            avg_risk=("composite_risk_score", "mean"),
            avg_conf=("confidence", "mean"),
            latest=("timestamp", "max"),
        )
        .reset_index()
        .sort_values("avg_risk", ascending=False)
        .head(15)
    )
    zone_risk["avg_risk"] = zone_risk["avg_risk"].round(1)
    zone_risk["avg_conf"] = (zone_risk["avg_conf"] * 100).round(0)

    # Table header
    zh1, zh2, zh3, zh4, zh5, zh6 = st.columns([3, 1, 1, 1, 1, 2])
    for col, label in zip(
        [zh1, zh2, zh3, zh4, zh5, zh6],
        ["Zone", "Incidents", "High Sev.", "Avg Risk", "Avg Conf.", "Last Incident"]
    ):
        col.markdown(
            f'<span style="font-size:0.7rem;color:#aaa;'
            f'text-transform:uppercase;letter-spacing:0.5px;">'
            f'{label}</span>',
            unsafe_allow_html=True
        )

    for _, row in zone_risk.iterrows():
        risk_val = row["avg_risk"]
        if risk_val >= 70:
            risk_class = "risk-high"
            risk_label = "HIGH"
        elif risk_val >= 40:
            risk_class = "risk-medium"
            risk_label = "MEDIUM"
        else:
            risk_class = "risk-low"
            risk_label = "LOW"

        latest_str = ""
        if pd.notna(row["latest"]):
            latest_str = row["latest"].strftime("%b %d, %H:%M")

        zc1, zc2, zc3, zc4, zc5, zc6 = st.columns([3, 1, 1, 1, 1, 2])

        zc1.markdown(
            f'<div style="font-size:0.82rem;font-weight:600;'
            f'color:#1a1a1a;padding-top:4px;">'
            f'{row["location"]}</div>',
            unsafe_allow_html=True
        )
        zc2.markdown(
            f'<div style="font-size:0.82rem;color:#555;'
            f'padding-top:4px;text-align:center;">'
            f'{int(row["total"])}</div>',
            unsafe_allow_html=True
        )
        zc3.markdown(
            f'<div style="font-size:0.82rem;color:#555;'
            f'padding-top:4px;text-align:center;">'
            f'{int(row["high_count"])}</div>',
            unsafe_allow_html=True
        )
        zc4.markdown(
            f'<div style="font-size:0.82rem;font-weight:700;'
            f'padding-top:4px;text-align:center;"'
            f'class="{risk_class}">'
            f'{risk_val:.0f}/100</div>',
            unsafe_allow_html=True
        )
        zc5.markdown(
            f'<div style="font-size:0.82rem;color:#555;'
            f'padding-top:4px;text-align:center;">'
            f'{row["avg_conf"]:.0f}%</div>',
            unsafe_allow_html=True
        )
        zc6.markdown(
            f'<div style="font-size:0.78rem;color:#888;'
            f'padding-top:4px;">'
            f'{latest_str}</div>',
            unsafe_allow_html=True
        )

        # Risk bar under each zone
        st.progress(min(1.0, risk_val / 100))

# ─────────────────────────────────────────────
# ROW 5: APPROVAL STATUS BREAKDOWN
# ─────────────────────────────────────────────
st.markdown(
    '<div class="section-title">Approval Status</div>',
    unsafe_allow_html=True
)

approval_col1, approval_col2 = st.columns([1, 2], gap="large")

with approval_col1:
    approval_counts = filtered_df["approval_status"].value_counts().reset_index()
    approval_counts.columns = ["status", "count"]
    approval_colors = {
        "PENDING":  "#f9a825",
        "APPROVED": "#388e3c",
        "REJECTED": "#d32f2f"
    }
    colors = [approval_colors.get(s, "#888") for s in approval_counts["status"]]

    fig_approval = px.pie(
        approval_counts,
        names="status",
        values="count",
        color_discrete_sequence=colors,
        hole=0.5
    )
    fig_approval.update_traces(
        textposition="inside",
        textinfo="label+value",
        textfont_size=11
    )
    fig_approval.update_layout(
        height=220,
        margin=dict(l=10, r=10, t=30, b=10),
        title=dict(
            text="By approval status",
            font=dict(size=12, color="#888")
        ),
        showlegend=False
    )
    st.plotly_chart(fig_approval, use_container_width=True)

with approval_col2:
    # Risk score by approval status
    approval_risk = (
        filtered_df.groupby("approval_status")
        .agg(
            count=("id", "count"),
            avg_risk=("composite_risk_score", "mean"),
            avg_conf=("confidence", "mean"),
        )
        .reset_index()
    )
    approval_risk["avg_risk"] = approval_risk["avg_risk"].round(1)
    approval_risk["avg_conf"] = (approval_risk["avg_conf"] * 100).round(0)

    for _, row in approval_risk.iterrows():
        status = row["approval_status"]
        status_color = approval_colors.get(status, "#888")

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1.5rem;
                    padding:0.5rem 0;border-bottom:1px solid #f0f0f0;">
            <div style="width:100px;font-size:0.82rem;font-weight:600;
                        color:{status_color};">
                {status}
            </div>
            <div style="font-size:0.82rem;color:#555;">
                {int(row['count'])} incident(s)
            </div>
            <div style="font-size:0.82rem;color:#555;">
                Avg risk: <b>{row['avg_risk']:.0f}/100</b>
            </div>
            <div style="font-size:0.82rem;color:#555;">
                Avg confidence: <b>{row['avg_conf']:.0f}%</b>
            </div>
        </div>
        """, unsafe_allow_html=True)