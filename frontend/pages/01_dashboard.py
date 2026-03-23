# # Add this inside render_incident_view() after the approval section
# from backend.utils.report_generator import generate_incident_pdf
# import tempfile

# st.markdown("### 📄 Export Report")
# if st.button("📥 Download PDF Report", key=f"pdf_{incident.get('id', 'cur')}"):
#     with st.spinner("Generating PDF..."):
#         out_path = f"data/incidents/report_{incident.get('id', 'cur')}.pdf"
#         generate_incident_pdf(incident, out_path)
#         with open(out_path, "rb") as f:
#             st.download_button(
#                 label="⬇️ Click to Download",
#                 data=f,
#                 file_name=f"Nivaran_Report_{incident.get('id')}.pdf",
#                 mime="application/pdf",
#                 key=f"dl_{incident.get('id', 'cur')}"
#             )