import os
import json
import re
from PIL import Image
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

# Create Gemini client
client = genai.Client(api_key=API_KEY)


def analyze_image(image_path: str) -> dict:
    """
    Analyze a single image and return structured disaster detection output.
    """

    try:
        if not os.path.exists(image_path):
            return {
                "hazard": False,
                "type": "file_not_found",
                "severity": "unknown",
                "confidence": 0.0
            }

        img = Image.open(image_path)

        prompt = """
        You are an advanced disaster detection AI.

        Analyze the image carefully.

        Detect if there is:
        - Flood
        - Landslide
        - Fire
        - Infrastructure damage
        - Or no disaster

        Determine:
        - hazard (true/false)
        - type (flood/landslide/fire/infrastructure/none)
        - severity (low/medium/high)
        - confidence (0.0 to 1.0)

        Severity Guidelines:
        - low: minor issue
        - medium: visible hazard but manageable
        - high: severe damage, danger to life

        Respond ONLY in valid JSON format:

        {
            "hazard": true,
            "type": "flood",
            "severity": "high",
            "confidence": 0.95
        }
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, img]
        )

        text = response.text.strip()
        print(f"\nRAW RESPONSE ({image_path}):", text)

        match = re.search(r'\{.*\}', text, re.DOTALL)

        if match:
            return json.loads(match.group())
        else:
            return {
                "hazard": False,
                "type": "unknown",
                "severity": "unknown",
                "confidence": 0.0
            }

    except Exception as e:
        print("Vision Agent Error:", e)
        return {
            "hazard": False,
            "type": "error",
            "severity": "unknown",
            "confidence": 0.0
        }


def analyze_multiple_images(folder_path: str):
    """
    Analyze all images inside a folder.
    """

    results = []

    if not os.path.exists(folder_path):
        print("Folder not found:", folder_path)
        return results

    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            full_path = os.path.join(folder_path, filename)
            print(f"\nAnalyzing: {filename}")

            result = analyze_image(full_path)

            results.append({
                "image": filename,
                "result": result
            })

    return results


# ------------------------------
# MAIN EXECUTION
# ------------------------------

if __name__ == "__main__":

    print("Vision Agent Testing Mode")

    # OPTION 1: Test Single Image
    # Uncomment this if you want single test
    # single_result = analyze_image("flood.jpg")
    # print("\nFINAL OUTPUT (Single Image):")
    # print(single_result)

    # OPTION 2: Test Multiple Images
    results = analyze_multiple_images("test_images")

    print("\nFINAL RESULTS (Multiple Images):")
    for r in results:
        print(r)
