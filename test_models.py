from dotenv import load_dotenv
import os
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)

print("Available models:")
for m in genai.list_models():
    print(f"Name: {m.name}, Default Version: {m.version}")
