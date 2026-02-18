import os
import json
import re
from PIL import Image
from dotenv import load_dotenv
from google import genai

# Load API key
load_dotenv()

# Create Gemini client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def analyze_image(image_path: str) -> dict:
    """
    Analyze a single image and return structured disaster detection output.
    """

    try:
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
        print(f"RAW RESPONSE ({image_path}):", text)

        match = re.search(r'\{.*\}', text, re.DOTALL)

        if match:
            result = json.loads(match.group())
        else:
            result = {
                "hazard": False,
                "type": "unknown",
                "severity": "unknown",
                "confidence": 0.0
            }

        return result

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


if __name__ == "__main__":
    # Change this to test single image
    # single_result = analyze_image("flood.jpg")
    # print("FINAL OUTPUT:", single_result)

    # Test multiple images from folder
    results = analyze_multiple_images("test_images")

    print("\nFINAL RESULTS:")
    for r in results:
        print(r)
