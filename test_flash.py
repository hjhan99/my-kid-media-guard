import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

for m in ['models/gemini-flash-latest', 'models/gemini-2.5-flash', 'models/gemini-flash-lite-latest']:
    try:
        model = genai.GenerativeModel(m)
        print(f"Testing {m}...")
        resp = model.generate_content("hello")
        print(f"SUCCESS {m}: {resp.text}")
        break # found it!
    except Exception as e:
        print(f"FAILED {m}: {e}")
