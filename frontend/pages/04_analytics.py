# frontend/pages/04_analytics.py
import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from backend.database.incident_store import get_all_incidents

st.set_page_config(page_title="Nivaran - Analytics", layout="wide")
st.title("📊 Nivaran — Incident Analytics")

incidents = get_all_incidents()

if not incidents:
    st.info("No incidents recorded yet. Analyze some images first.")
    st.stop()

df = pd.DataFrame(incidents)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date

# ── KPI Row ──────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📌 Total Incidents", len(df))
k2.metric("🌧️ Floods",          len(df[df["type"] == "Flood"]))
k3.metric("⛰️ Landslides",       len(df[df["type"] == "Landslide"]))
k4.metric("🔥 Fires",            len(df[df["type"] == "Fire"]))
k5.metric("🔴 High Severity",    len(df[df["severity"] == "High"]))

st.divider()

# ── Row 1: Timeline + Type Breakdown ─────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 Incidents Over Time")
    daily = df.groupby("date").size().reset_index(name="count")
    fig_time = px.line(
        daily, x="date", y="count",
        markers=True,
        labels={"date": "Date", "count": "Incidents"},
        color_discrete_sequence=["#4A90D9"]
    )
    fig_time.update_layout(height=300)
    st.plotly_chart(fig_time, use_container_width=True)

with col2:
    st.subheader("🥧 By Disaster Type")
    type_counts = df["type"].value_counts().reset_index()
    type_counts.columns = ["type", "count"]
    fig_pie = px.pie(
        type_counts, names="type", values="count",
        color_discrete_sequence=px.colors.qualitative.Set2,
        hole=0.4
    )
    fig_pie.update_layout(height=300)
    st.plotly_chart(fig_pie, use_container_width=True)

# ── Row 2: Severity Bar + Confidence Distribution ────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("📊 Severity Distribution")
    sev_counts = df["severity"].value_counts().reset_index()
    sev_counts.columns = ["severity", "count"]
    color_map = {"High": "#E74C3C", "Medium": "#F39C12", "Low": "#2ECC71"}
    fig_bar = px.bar(
        sev_counts, x="severity", y="count",
        color="severity",
        color_discrete_map=color_map,
        labels={"severity": "Severity", "count": "Count"}
    )
    fig_bar.update_layout(height=300, showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

with col4:
    st.subheader("🎯 AI Confidence Distribution")
    fig_hist = px.histogram(
        df, x="confidence", nbins=10,
        labels={"confidence": "Confidence Score", "count": "Incidents"},
        color_discrete_sequence=["#8E44AD"]
    )
    fig_hist.update_layout(height=300)
    st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

# ── Row 3: Heatmap ────────────────────────────────────────
st.subheader("🗺️ Historical Incident Heatmap — Mumbai")

time_filter = st.radio(
    "Filter by time range",
    ["All Time", "Last 30 Days", "Last 7 Days"],
    horizontal=True
)

filtered_df = df.copy()
if time_filter == "Last 7 Days":
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
    filtered_df = df[df["timestamp"] >= cutoff]
elif time_filter == "Last 30 Days":
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
    filtered_df = df[df["timestamp"] >= cutoff]

valid = filtered_df.dropna(subset=["lat", "lon"])

if valid.empty:
    st.warning("No incidents with coordinates in selected time range.")
else:
    m = folium.Map(location=[19.0760, 72.8777], zoom_start=11)

    heat_data = [[row["lat"], row["lon"]] for _, row in valid.iterrows()]
    HeatMap(
        heat_data,
        radius=25,
        blur=15,
        gradient={"0.4": "blue", "0.65": "orange", "1": "red"}
    ).add_to(m)

    # Also add individual markers
    for _, row in valid.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=5,
            color="red" if row["severity"] == "High" else "orange",
            fill=True,
            popup=f"{row['id']} | {row['type']} | {row['severity']}"
        ).add_to(m)

    st_folium(m, width=1200, height=500)

st.divider()

# ── Row 4: Zone Risk Scoring ──────────────────────────────
st.subheader("🏙️ Zone Risk Scores")
st.caption("Based on incident frequency per location.")

zone_risk = (
    df.groupby("location")
    .agg(total=("id", "count"), high_count=("severity", lambda x: (x == "High").sum()))
    .reset_index()
    .sort_values("total", ascending=False)
    .head(10)
)
zone_risk["risk_score"] = (zone_risk["total"] * 0.6 + zone_risk["high_count"] * 0.4).round(1)
zone_risk["risk_label"] = zone_risk["risk_score"].apply(
    lambda x: "🔴 HIGH RISK" if x >= 3 else ("🟠 MEDIUM RISK" if x >= 1.5 else "🟢 LOW RISK")
)

st.dataframe(
    zone_risk[["location", "total", "high_count", "risk_score", "risk_label"]].rename(columns={
        "location":   "Location",
        "total":      "Total Incidents",
        "high_count": "High Severity",
        "risk_score": "Risk Score",
        "risk_label": "Risk Level"
    }),
    use_container_width=True,
    hide_index=True
)