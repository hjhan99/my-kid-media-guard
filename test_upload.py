import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

try:
    # 빈 m4a 파일 생성하여 업로드 테스트
    with open("test_audio.m4a", "wb") as f:
        f.write(b'hello world fake audio data')
    
    print("1. Uploading...")
    uploaded_file = genai.upload_file(path="test_audio.m4a", mime_type="audio/mp4")
    print("2. Upload complete. State:", uploaded_file.state.name)
    
    print("3. Generating content...")
    model = genai.GenerativeModel("models/gemini-2.0-flash")
    resp = model.generate_content([uploaded_file, "test"])
    print("4. Response:", resp.text)
    
except Exception as e:
    print("Error:", repr(e))
finally:
    if 'uploaded_file' in locals():
        genai.delete_file(uploaded_file.name)
