from google import genai
import os
from dotenv import load_dotenv

# Load env
folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(folder, '.env')
load_dotenv(env_path)

key = os.getenv("GEMINI_API_KEY")

if not key:
    print("NO KEY")
else:
    client = genai.Client(api_key=key)
    print("MODELS:")
    # Synchronous iteration
    for model in client.models.list():
        name = model.name
        if "flash" in name or "gemini" in name:
            print(f"- {name}")
