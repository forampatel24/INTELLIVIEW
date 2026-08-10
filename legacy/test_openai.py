import google.generativeai as genai

# ✅ Replace with your actual key
genai.configure(api_key="AIzaSyCqVMPp4ZvWeJt8vAd58XeK7WEMUpCjodU")

model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

try:
    print("Testing Gemini API...")
    response = model.generate_content("Explain Newton's laws of motion in simple terms.")
    print("\n✅ Gemini Response:\n")
    print(response.text)
except Exception as e:
    print("\n❌ Error contacting Gemini API:", e)
    