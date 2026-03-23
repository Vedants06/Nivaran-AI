# scripts/seed_incidents.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.incident_store import save_incident

incidents = [
    {
        "id": "INC-20240801120000", "timestamp": "2024-08-01 12:00:00", "time": "2024-08-01 12:00:00",
        "location": "Kurla Station", "lat": 19.0726, "lon": 72.8797,
        "type": "Flood", "severity": "High", "confidence": 0.97, "detected": "YES",
        "protocol": "Evacuate immediately. Move to higher ground. Avoid flooded roads.",
        "alert_en": "⚠️ Severe flooding at Kurla Station. Avoid the area.",
        "alert_hi": "⚠️ कुर्ला स्टेशन पर बाढ़। क्षेत्र से दूर रहें।",
        "alert_mr": "⚠️ कुर्ला स्थानकावर पूर. परिसर टाळा.",
        "tweet_public": "⚠️ Flooding at Kurla Station. Seek alternate routes. #MumbaiRains #Nivaran",
        "tweet_authority": "@RailwayMumbai @MumbaiPolice 🚨 Kurla Station flooding. Immediate action needed. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Officer Patil",
        "media_kind": "image", "media_name": "kurla_flood.jpg", "image_path": ""
    },
    {
        "id": "INC-20240802093000", "timestamp": "2024-08-02 09:30:00", "time": "2024-08-02 09:30:00",
        "location": "Hindmata Junction", "lat": 19.0178, "lon": 72.8478,
        "type": "Flood", "severity": "High", "confidence": 0.95, "detected": "YES",
        "protocol": "Deploy pumps immediately. Redirect traffic. Evacuate low-lying areas.",
        "alert_en": "⚠️ Hindmata Junction submerged. Do not enter.",
        "alert_hi": "⚠️ हिंदमाता जंक्शन जलमग्न। प्रवेश न करें।",
        "alert_mr": "⚠️ हिंदमाता जंक्शन बुडाले. आत जाऊ नका.",
        "tweet_public": "⚠️ Hindmata Junction flooded. Use alternate routes. #MumbaiRains #Nivaran",
        "tweet_authority": "@MumbaiPolice @NDMA_India 🚨 Hindmata flooding HIGH severity. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Officer Sharma",
        "media_kind": "image", "media_name": "hindmata_flood.jpg", "image_path": ""
    },
    {
        "id": "INC-20240803143000", "timestamp": "2024-08-03 14:30:00", "time": "2024-08-03 14:30:00",
        "location": "Andheri Subway", "lat": 19.1136, "lon": 72.8697,
        "type": "Flood", "severity": "Medium", "confidence": 0.88, "detected": "YES",
        "protocol": "Monitor water levels. Alert commuters. Deploy traffic police.",
        "alert_en": "⚠️ Andheri Subway waterlogged. Use FOB.",
        "alert_hi": "⚠️ अंधेरी सबवे जलभराव। FOB का उपयोग करें।",
        "alert_mr": "⚠️ अंधेरी सबवे पाण्याने भरले. FOB वापरा.",
        "tweet_public": "⚠️ Andheri Subway flooded. Use the foot overbridge. #MumbaiRains #Nivaran",
        "tweet_authority": "@RailwayMumbai @MumbaiPolice Andheri Subway waterlogged. Deploy personnel. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Officer Mehta",
        "media_kind": "image", "media_name": "andheri_flood.jpg", "image_path": ""
    },
    {
        "id": "INC-20240804080000", "timestamp": "2024-08-04 08:00:00", "time": "2024-08-04 08:00:00",
        "location": "Sion Hospital Road", "lat": 19.0388, "lon": 72.8613,
        "type": "Flood", "severity": "High", "confidence": 0.93, "detected": "YES",
        "protocol": "Emergency medical access must be maintained. Deploy QRMT teams.",
        "alert_en": "⚠️ Sion Hospital Road flooded. Emergency vehicles affected.",
        "alert_hi": "⚠️ सायन अस्पताल रोड बाढ़। आपातकालीन वाहन प्रभावित।",
        "alert_mr": "⚠️ सायन रुग्णालय रस्ता पूर. आपत्कालीन वाहने अडकली.",
        "tweet_public": "⚠️ Sion Hospital Road flooded. Emergency access blocked. #MumbaiRains #Nivaran",
        "tweet_authority": "@MumbaiPolice @NDMA_India 🚨 Sion Hospital Road flooding. Clear immediately. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Officer Patil",
        "media_kind": "image", "media_name": "sion_flood.jpg", "image_path": ""
    },
    {
        "id": "INC-20240805110000", "timestamp": "2024-08-05 11:00:00", "time": "2024-08-05 11:00:00",
        "location": "Dadar Station", "lat": 19.0178, "lon": 72.8422,
        "type": "Flood", "severity": "Medium", "confidence": 0.85, "detected": "YES",
        "protocol": "Increase platform monitoring. Deploy drainage teams.",
        "alert_en": "⚠️ Dadar Station platforms flooded. Exercise caution.",
        "alert_hi": "⚠️ दादर स्टेशन प्लेटफॉर्म जलमग्न। सावधानी बरतें।",
        "alert_mr": "⚠️ दादर स्थानक प्लॅटफॉर्म पाण्याखाली. काळजी घ्या.",
        "tweet_public": "⚠️ Dadar Station flooded. Delays expected. #MumbaiRains #Nivaran",
        "tweet_authority": "@RailwayMumbai Dadar Station flooding. Immediate drainage needed. #NivaranAlert",
        "approval_status": "PENDING", "approved_by": "",
        "media_kind": "image", "media_name": "dadar_flood.jpg", "image_path": ""
    },
    {
        "id": "INC-20240806150000", "timestamp": "2024-08-06 15:00:00", "time": "2024-08-06 15:00:00",
        "location": "Malad Poisar Depot", "lat": 19.1874, "lon": 72.8483,
        "type": "Landslide", "severity": "High", "confidence": 0.91, "detected": "YES",
        "protocol": "Block road immediately. Evacuate nearby residents. Deploy NDRF.",
        "alert_en": "🚨 Landslide near Malad. Road blocked. Evacuate.",
        "alert_hi": "🚨 मालाड के पास भूस्खलन। सड़क बंद। निकासी करें।",
        "alert_mr": "🚨 मालाडजवळ भूस्खलन. रस्ता बंद. स्थलांतर करा.",
        "tweet_public": "🚨 Landslide near Malad Poisar. Road blocked. Avoid area. #MumbaiRains #Nivaran",
        "tweet_authority": "@MumbaiPolice @NDMA_India 🚨 Landslide Malad HIGH severity. Deploy NDRF. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Commander Singh",
        "media_kind": "image", "media_name": "malad_landslide.jpg", "image_path": ""
    },
    {
        "id": "INC-20240807073000", "timestamp": "2024-08-07 07:30:00", "time": "2024-08-07 07:30:00",
        "location": "Vikhroli Parksite", "lat": 19.1041, "lon": 72.9244,
        "type": "Landslide", "severity": "Medium", "confidence": 0.82, "detected": "YES",
        "protocol": "Evacuate hillside residents. Monitor slope stability.",
        "alert_en": "⚠️ Landslide risk at Vikhroli. Residents evacuate.",
        "alert_hi": "⚠️ विक्रोली में भूस्खलन का खतरा। निवासी निकलें।",
        "alert_mr": "⚠️ विक्रोलीत भूस्खलनाचा धोका. रहिवासी बाहेर पडा.",
        "tweet_public": "⚠️ Landslide risk at Vikhroli Parksite. Evacuate hillside areas. #MumbaiRains #Nivaran",
        "tweet_authority": "@MumbaiPolice Vikhroli landslide risk. Deploy monitoring teams. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Officer Desai",
        "media_kind": "image", "media_name": "vikhroli_landslide.jpg", "image_path": ""
    },
    {
        "id": "INC-20240808190000", "timestamp": "2024-08-08 19:00:00", "time": "2024-08-08 19:00:00",
        "location": "Dharavi Koliwada", "lat": 19.0444, "lon": 72.8536,
        "type": "Fire", "severity": "High", "confidence": 0.96, "detected": "YES",
        "protocol": "Deploy fire brigade immediately. Evacuate 500m radius.",
        "alert_en": "🔥 Fire at Dharavi Koliwada. Evacuate immediately.",
        "alert_hi": "🔥 धारावी कोलीवाड़ा में आग। तुरंत निकलें।",
        "alert_mr": "🔥 धारावी कोळीवाड्यात आग. तातडीने बाहेर पडा.",
        "tweet_public": "🔥 Fire reported at Dharavi Koliwada. Evacuate immediately. #MumbaiAlert #Nivaran",
        "tweet_authority": "@MumbaiPolice @MumbaiFireBrigade 🚨 Fire Dharavi HIGH severity. Deploy immediately. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Commander Singh",
        "media_kind": "image", "media_name": "dharavi_fire.jpg", "image_path": ""
    },
    {
        "id": "INC-20240809210000", "timestamp": "2024-08-09 21:00:00", "time": "2024-08-09 21:00:00",
        "location": "Bhandup Industrial Area", "lat": 19.1544, "lon": 72.9422,
        "type": "Fire", "severity": "High", "confidence": 0.94, "detected": "YES",
        "protocol": "Chemical fire protocol. 1km evacuation radius. Hazmat team required.",
        "alert_en": "🔥 Industrial fire at Bhandup. 1km evacuation zone active.",
        "alert_hi": "🔥 भांडुप में औद्योगिक आग। 1 किमी निकासी क्षेत्र।",
        "alert_mr": "🔥 भांडुपमध्ये औद्योगिक आग. 1 किमी स्थलांतर क्षेत्र.",
        "tweet_public": "🔥 Industrial fire at Bhandup. Stay 1km away. #MumbaiAlert #Nivaran",
        "tweet_authority": "@MumbaiPolice @MumbaiFireBrigade 🚨 Bhandup industrial fire. Hazmat needed. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Commander Singh",
        "media_kind": "image", "media_name": "bhandup_fire.jpg", "image_path": ""
    },
    {
        "id": "INC-20240810063000", "timestamp": "2024-08-10 06:30:00", "time": "2024-08-10 06:30:00",
        "location": "Kings Circle Subway", "lat": 19.0258, "lon": 72.8594,
        "type": "Flood", "severity": "High", "confidence": 0.92, "detected": "YES",
        "protocol": "Close subway. Deploy traffic police. Alert commuters.",
        "alert_en": "⚠️ Kings Circle Subway flooded. Closed for safety.",
        "alert_hi": "⚠️ किंग्स सर्कल सबवे जलमग्न। सुरक्षा के लिए बंद।",
        "alert_mr": "⚠️ किंग्ज सर्कल सबवे पूरग्रस्त. सुरक्षेसाठी बंद.",
        "tweet_public": "⚠️ Kings Circle Subway closed due to flooding. Use alternate route. #MumbaiRains #Nivaran",
        "tweet_authority": "@MumbaiPolice Kings Circle Subway flooded. Deploy personnel. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Officer Mehta",
        "media_kind": "image", "media_name": "kingscircle_flood.jpg", "image_path": ""
    },
    {
        "id": "INC-20240811120000", "timestamp": "2024-08-11 12:00:00", "time": "2024-08-11 12:00:00",
        "location": "Ghatkopar Station", "lat": 19.0863, "lon": 72.9081,
        "type": "Flood", "severity": "Low", "confidence": 0.78, "detected": "YES",
        "protocol": "Monitor platform. Alert station master. Deploy drainage.",
        "alert_en": "ℹ️ Minor waterlogging at Ghatkopar Station. Monitor situation.",
        "alert_hi": "ℹ️ घाटकोपर स्टेशन पर मामूली जलभराव।",
        "alert_mr": "ℹ️ घाटकोपर स्थानकावर किरकोळ पाणी साचले.",
        "tweet_public": "ℹ️ Minor waterlogging at Ghatkopar Station. Situation being monitored. #MumbaiRains #Nivaran",
        "tweet_authority": "@RailwayMumbai Minor waterlogging at Ghatkopar. Monitor and drain. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Officer Patil",
        "media_kind": "image", "media_name": "ghatkopar_flood.jpg", "image_path": ""
    },
    {
        "id": "INC-20240812090000", "timestamp": "2024-08-12 09:00:00", "time": "2024-08-12 09:00:00",
        "location": "Chembur Naka", "lat": 19.0622, "lon": 72.8994,
        "type": "Flood", "severity": "Medium", "confidence": 0.86, "detected": "YES",
        "protocol": "Deploy pumps. Redirect traffic. Monitor drainage.",
        "alert_en": "⚠️ Chembur Naka waterlogged. Traffic diverted.",
        "alert_hi": "⚠️ चेंबूर नाका जलभराव। यातायात मोड़ा गया।",
        "alert_mr": "⚠️ चेंबूर नाका पाण्याने भरले. वाहतूक वळवली.",
        "tweet_public": "⚠️ Chembur Naka flooded. Traffic diverted via Eastern Express Highway. #MumbaiRains #Nivaran",
        "tweet_authority": "@MumbaiPolice Chembur Naka flooding. Traffic management needed. #NivaranAlert",
        "approval_status": "PENDING", "approved_by": "",
        "media_kind": "image", "media_name": "chembur_flood.jpg", "image_path": ""
    },
    {
        "id": "INC-20240813170000", "timestamp": "2024-08-13 17:00:00", "time": "2024-08-13 17:00:00",
        "location": "Powai Lake Area", "lat": 19.1225, "lon": 72.9057,
        "type": "Flood", "severity": "High", "confidence": 0.94, "detected": "YES",
        "protocol": "Alert downstream residents. Monitor lake overflow. Deploy NDRF.",
        "alert_en": "🚨 Powai Lake overflowing. Downstream residents evacuate.",
        "alert_hi": "🚨 पवई झील उफान पर। निचले इलाके खाली करें।",
        "alert_mr": "🚨 पवई तलाव दुथडी भरला. खालच्या भागातील रहिवासी स्थलांतरित व्हा.",
        "tweet_public": "🚨 Powai Lake overflowing! Downstream areas at risk. Evacuate immediately. #MumbaiRains #Nivaran",
        "tweet_authority": "@NDMA_India @MumbaiPolice 🚨 Powai Lake overflow HIGH severity. Deploy NDRF. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Commander Singh",
        "media_kind": "image", "media_name": "powai_flood.jpg", "image_path": ""
    },
    {
        "id": "INC-20240814080000", "timestamp": "2024-08-14 08:00:00", "time": "2024-08-14 08:00:00",
        "location": "Mankhurd Bridge", "lat": 19.0436, "lon": 72.9236,
        "type": "Landslide", "severity": "High", "confidence": 0.89, "detected": "YES",
        "protocol": "Close bridge immediately. Structural assessment required.",
        "alert_en": "🚨 Landslide near Mankhurd Bridge. Bridge closed.",
        "alert_hi": "🚨 मानखुर्द पुल के पास भूस्खलन। पुल बंद।",
        "alert_mr": "🚨 मानखुर्द पुलाजवळ भूस्खलन. पूल बंद.",
        "tweet_public": "🚨 Landslide near Mankhurd Bridge. Bridge closed. Use alternate routes. #MumbaiRains #Nivaran",
        "tweet_authority": "@MumbaiPolice @RailwayMumbai 🚨 Mankhurd Bridge landslide. Close immediately. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Officer Desai",
        "media_kind": "image", "media_name": "mankhurd_landslide.jpg", "image_path": ""
    },
    {
        "id": "INC-20240815150000", "timestamp": "2024-08-15 15:00:00", "time": "2024-08-15 15:00:00",
        "location": "Bandra Reclamation", "lat": 19.0550, "lon": 72.8197,
        "type": "Flood", "severity": "Medium", "confidence": 0.83, "detected": "YES",
        "protocol": "Monitor sea level. Alert coastal residents. Deploy coastal police.",
        "alert_en": "⚠️ Bandra Reclamation flooded due to high tide.",
        "alert_hi": "⚠️ बांद्रा रिक्लेमेशन ज्वार के कारण जलमग्न।",
        "alert_mr": "⚠️ बांद्रा रिक्लेमेशन भरतीमुळे पूरग्रस्त.",
        "tweet_public": "⚠️ Bandra Reclamation flooded. High tide alert. #MumbaiRains #Nivaran",
        "tweet_authority": "@MumbaiPolice Bandra coastal flooding. Deploy coastal patrol. #NivaranAlert",
        "approval_status": "APPROVED", "approved_by": "Officer Sharma",
        "media_kind": "image", "media_name": "bandra_flood.jpg", "image_path": ""
    },
]

if __name__ == "__main__":
    print("🌱 Seeding database with Mumbai incidents...")
    for inc in incidents:
        save_incident(inc)
        print(f"  ✅ Saved: {inc['id']} | {inc['location']} | {inc['type']} | {inc['severity']}")
    print(f"\n🎉 Done! {len(incidents)} incidents added to database.")