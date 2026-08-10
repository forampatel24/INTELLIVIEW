#python -m uvicorn main2:app --reload

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pdfplumber
from rake_nltk import Rake
import google.generativeai as genai
import nltk
import os
import tempfile
import time
import re
nltk.download('punkt')
nltk.download('stopwords')

app = FastAPI()

# CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow from any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini API
genai.configure(api_key="AIzaSyDQJmLXBcSar6jhW1pS0zeWs06zcdyj_gc")  # 🔐 Replace with your actual Gemini API Key

# Globals for session
current_question = ""
keywords = []

def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            if page_text := page.extract_text():
                text += page_text + "\n"
    return text

def extract_keywords(text, max_keywords=15):
    rake = Rake()
    rake.extract_keywords_from_text(text)
    return rake.get_ranked_phrases()[:max_keywords]

def generate_question(keyword):
    model = genai.GenerativeModel(model_name="models/gemini-2.0-flash")
    prompt = f"Generate one moderate technical interview question based on {keyword}. Only questions should be generated. There shouldnt be any other text in the response. Length of the question should be less than 30 words. "
    response = model.generate_content(prompt)
    return response.text.strip()

@app.post("/upload-resume")
async def upload_resume(resume: UploadFile = File(...)):
    global keywords, current_question

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await resume.read())
            tmp_path = tmp.name

        text = extract_text_from_pdf(tmp_path)
        if not text.strip():
            return JSONResponse({"error": "No text found in resume."}, status_code=400)

        keywords = extract_keywords(text)
        if not keywords:
            return JSONResponse({"error": "No keywords extracted."}, status_code=400)

        current_question = generate_question(keywords[0])
        return {"question": current_question}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/submit-answer")
async def submit_answer(payload: dict):
    global keywords, current_question

    user_answer = payload.get("answer")

    if not user_answer:
        return JSONResponse({"error": "Answer is required"}, status_code=400)

    # Pick next keyword for next question if any
    try:
        next_keyword = keywords[1] if len(keywords) > 1 else None
    except:
        next_keyword = None

    # Construct prompt
    prompt = f"""
You are an interview bot. Here's the candidate's answer: "{user_answer}"

1. Provide brief, clear, and constructive feedback on their answer.
2. Ask the next relevant technical question under 30 words {f"based on {next_keyword}" if next_keyword else ""}.

Format your response as:
Feedback: ...
Next Question: ...
"""

    try:
        model = genai.GenerativeModel(model_name="models/gemini-2.0-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Extract using improved regex
        feedback_match = re.search(r"Feedback:\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
        question_match = re.search(r"Next Question:\s*(.*)", text, re.IGNORECASE | re.DOTALL)

        feedback = feedback_match.group(1).strip() if feedback_match else "Feedback not found."
        question = question_match.group(1).strip() if question_match else "Next question not found."

        return {
            "response": {
                "feedback": feedback,
                "question": question
            }
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
