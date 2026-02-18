import os
import json
from PIL import Image
from dotenv import load_dotenv
from google import genai

# Load API key
load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def analyze_image(image_path: str):
    img = Image.open(image_path)

    prompt = """
    You are a disaster detection AI.

    Analyze the image.

    Respond ONLY in raw JSON format:
    {
        "hazard": true/false,
        "type": "flood/landslide/fire/none"
    }
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, img]
    )

    try:
        text = response.text.strip()
        result = json.loads(text)
        return result
    except:
        return {"hazard": False, "type": "unknown"}


if __name__ == "__main__":
    result = analyze_image("flood.jpg")
    print(result)
