# video_monitor.py
import cv2
import os
import time
from dotenv import load_dotenv
from graph import app as nivaran_graph

load_dotenv()

def monitor_video(
    video_path: str,
    location: str = "Mumbai Railway Station",
    sample_every_seconds: int = 5,
    alert_on_severity: list = ["high", "medium"]
):
    """
    Analyze a video file frame by frame.
    
    Args:
        video_path: Path to .mp4 or any video file
        location: Human-readable location name
        sample_every_seconds: How often to grab a frame for analysis
        alert_on_severity: Which severity levels trigger an alert
    """

    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        return

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"❌ Could not open video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_seconds = total_frames / fps

    print(f"\n{'='*60}")
    print(f"🎥 NIVARAN VIDEO MONITOR")
    print(f"{'='*60}")
    print(f"📁 Video:    {video_path}")
    print(f"📍 Location: {location}")
    print(f"⏱️  Duration: {duration_seconds:.1f} seconds")
    print(f"🎞️  FPS:      {fps:.1f}")
    print(f"🔍 Sampling: every {sample_every_seconds} seconds")
    print(f"{'='*60}\n")

    frame_interval = int(fps * sample_every_seconds)
    frame_count = 0
    sample_count = 0
    last_alerted_severity = None
    temp_frame_path = "temp_monitor_frame.jpg"

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # Only process every Nth frame
            if frame_count % frame_interval != 0:
                continue

            sample_count += 1
            timestamp = frame_count / fps

            print(f"🔍 [{timestamp:.1f}s] Analyzing frame {frame_count}...")

            # Save frame as image
            cv2.imwrite(temp_frame_path, frame)

            # Run through full Nivaran pipeline
            try:
                result = nivaran_graph.invoke({"image_path": temp_frame_path})
                vision = result["vision_output"]

                hazard = vision.get("hazard", False)
                disaster_type = vision.get("type", "none")
                severity = vision.get("severity", "low")
                confidence = vision.get("confidence", 0.0)

                status_icon = "🚨" if hazard else "✅"
                print(f"   {status_icon} Hazard: {hazard} | Type: {disaster_type} | Severity: {severity} | Confidence: {confidence}")

                # Trigger alert logic
                if hazard and severity.lower() in alert_on_severity:
                    # Only alert if situation changed (avoid spamming same alert)
                    if severity != last_alerted_severity:
                        print(f"\n{'🚨'*20}")
                        print(f"ALERT TRIGGERED at {timestamp:.1f}s")
                        print(f"Location: {location}")
                        print(f"Type: {disaster_type.upper()} | Severity: {severity.upper()}")
                        print(f"\n📘 NDMA Protocol:")
                        print(result["protocol"])
                        print(f"\n🌐 Alert (EN): {result.get('alert_en', '')}")
                        print(f"🌐 Alert (HI): {result.get('alert_hi', '')}")
                        print(f"🌐 Alert (MR): {result.get('alert_mr', '')}")
                        print(f"\n👥 Public Tweet:\n{result.get('tweet_public', '')}")
                        print(f"\n🚨 Authority Tweet:\n{result.get('tweet_authority', '')}")
                        print(f"{'🚨'*20}\n")

                        last_alerted_severity = severity
                else:
                    # Reset alert state when situation clears
                    if last_alerted_severity is not None:
                        print(f"   ✅ Situation cleared at {timestamp:.1f}s")
                        last_alerted_severity = None

            except Exception as e:
                print(f"   ❌ Pipeline error on frame {frame_count}: {e}")
                continue

    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user.")

    finally:
        cap.release()
        if os.path.exists(temp_frame_path):
            os.remove(temp_frame_path)

        print(f"\n{'='*60}")
        print(f"📊 MONITORING COMPLETE")
        print(f"   Frames analyzed: {sample_count}")
        print(f"   Video duration:  {duration_seconds:.1f}s")
        print(f"{'='*60}")


# ------------------------------
# MAIN
# ------------------------------
if __name__ == "__main__":
    monitor_video(
        video_path="test_videos/flood_test.mp4",
        location="Kurla Railway Station",
        sample_every_seconds=5,
        alert_on_severity=["high", "medium"]
    )