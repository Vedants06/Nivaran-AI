import streamlit as st

st.title("🛡️ Rakshak AI: Mumbai Disaster Response")

uploaded_file = st.file_uploader("Upload CCTV/Drone Image", type=['jpg', 'png'])

if uploaded_file:
    st.image(uploaded_file, caption="Analyzing Feed...")
    # Dnyanesh's Task: Create a placeholder for the AI's final answer
    with st.spinner("AI Agents are thinking..."):
        st.info("Waiting for Vedant's Graph logic...")