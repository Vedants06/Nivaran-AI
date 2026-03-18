# backend/utils/report_generator.py
from fpdf import FPDF
from datetime import datetime
import os

class IncidentReport(FPDF):
    def header(self):
        # Header with a blue bar
        self.set_fill_color(33, 150, 243)
        self.rect(0, 0, 210, 30, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 15, "NIVARAN AI - EMERGENCY RESPONSE SYSTEM", 0, 1, "C")
        self.set_font("Helvetica", "I", 10)
        self.cell(0, 5, "Official Disaster Incident Report", 0, 1, "C")
        self.ln(15)

    def add_incident_content(self, data):
        self.set_text_color(0, 0, 0)
        # Incident Summary Table
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(240, 240, 240)
        
        # Generate a unique ID if one isn't provided
        report_id = data.get('id', datetime.now().strftime("%Y%m%d-%H%M"))
        self.cell(0, 10, f" Incident ID: {report_id}", 1, 1, 'L', True)
        
        self.set_font("Helvetica", "", 10)
        
        # Safety check for confidence scoring
        raw_conf = data.get('confidence', 0)
        conf_str = f"{float(raw_conf)*100:.1f}%" if raw_conf else "N/A"

        details = [
            ("Timestamp", data.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))),
            ("Location", data.get("location", "Mumbai Central")),
            ("Disaster Type", str(data.get("type", "General Alert")).upper()),
            ("Severity", str(data.get("severity", "Medium")).upper()),
            ("Confidence", conf_str)
        ]
        
        for label, val in details:
            self.set_font("Helvetica", "B", 10)
            self.cell(50, 8, f" {label}:", 1)
            self.set_font("Helvetica", "", 10)
            self.cell(0, 8, f" {val}", 1, 1)

        self.ln(10)
        
        # Protocol Section
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(211, 47, 47) # Red for urgency
        self.cell(0, 10, "OFFICIAL NDMA SAFETY PROTOCOLS", 0, 1)
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 10)
        
        protocol_text = data.get("protocol", "No protocol details available.")
        self.multi_cell(0, 8, protocol_text, border=1)

def generate_report(incident_data):
    """
    Main function to generate the PDF and save it to the backend/reports folder.
    """
    # 1. Target your manually created folder
    # This path works when running from the Nivaran-AI root
    report_dir = os.path.join("backend", "reports")
    
    # 2. Extra Safety: Create it if it's missing (just in case)
    os.makedirs(report_dir, exist_ok=True)

    # 3. Create a unique filename using the hazard type and current time
    timestamp = datetime.now().strftime("%H%M%S")
    hazard_type = incident_data.get('type', 'alert')
    filename = f"report_{hazard_type}_{timestamp}.pdf"
    output_path = os.path.join(report_dir, filename)

    try:
        pdf = IncidentReport()
        pdf.add_page()
        pdf.add_incident_content(incident_data)
        pdf.output(output_path)
        print(f"✅ SUCCESS: PDF generated at {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ PDF Error: {str(e)}")
        return None

# --- TESTING BLOCK ---
# Run this file directly to test if your folder and PDF logic work!
if __name__ == "__main__":
    mock_data = {
        "type": "flood",
        "severity": "high",
        "confidence": 0.98,
        "location": "Dadar, Mumbai",
        "protocol": "1. Evacuate immediately to higher ground.\n2. Do not drive through flooded areas.\n3. Follow local emergency broadcasts."
    }
    generate_report(mock_data)