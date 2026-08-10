from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext
import pdfplumber
from rake_nltk import Rake
import google.generativeai as genai
import nltk
import tempfile
import os
import re
import logging
from dotenv import load_dotenv
from sqlalchemy import ForeignKey
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from passlib.context import CryptContext



# python -m uvicorn maindb:app --reload
# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- NLTK Data ----------
nltk.download('punkt')
nltk.download('stopwords')

# ---------- Load Env ----------
load_dotenv()

# ---------- Gemini Configuration ----------
genai.configure(api_key="AIzaSyDQJmLXBcSar6jhW1pS0zeWs06zcdyj_gc")
model = genai.GenerativeModel(model_name="models/gemini-2.0-flash")

# ---------- FastAPI Setup ----------
app = FastAPI()

origins = [
    "http://localhost:3000",  # Change this to where your frontend runs
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://127.0.0.1:5500",
    # Or just ["*"] if you want to allow all origins for quick testing (not recommended in prod)
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Database Setup ----------
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from passlib.context import CryptContext

# ---------- Database Setup ----------
DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------- User Table ----------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    
    # Relationship with keywords
    keywords = relationship("Keyword", back_populates="user", cascade="all, delete-orphan")

# ---------- Keyword Table ----------
class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Relationship back to user
    user = relationship("User", back_populates="keywords")

# ---------- Create Tables ----------
Base.metadata.create_all(bind=engine)

# ---------- DB Dependency ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Password Hashing Context ----------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



# ---------- Helper Functions ----------
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



# ---------- Auth Routes ----------
@app.post("/signup")
def signup(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = pwd_context.hash(password)
    db.add(User(email=email, password=hashed_password))
    db.commit()
    return {"status": "success", "message": "Signup successful"}

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"status": "success", "message": "Login successful"}

# ---------- Resume Upload ----------
@app.post("/upload-resume")
async def upload_resume(
    resume: UploadFile = File(...),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    global keywords, current_question

    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await resume.read())
            tmp_path = tmp.name

        text = extract_text_from_pdf(tmp_path)
        if not text.strip():
            return JSONResponse({"error": "No text found in resume."}, status_code=400)

        keywords = extract_keywords(text)
        if not keywords:
            return JSONResponse({"error": "No keywords extracted."}, status_code=400)

        print("✅ Extracted Keywords:", keywords)

        current_question = generate_question(keywords[0])  # Only generate question now
        print("📨 Generated Question:", current_question)

        if not current_question or not current_question.strip():
            return JSONResponse({"error": "Question generation failed."}, status_code=500)

        # ✅ Don't save keywords to DB yet — delay until interview ends
        return {"question": current_question}

    except Exception as e:
        print("❌ Exception occurred:", str(e))
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------- Answer Submission & Feedback ----------
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

@app.post("/end-interview")
def end_interview(email: str = Form(...), db: Session = Depends(get_db)):
    global keywords

    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        for kw in keywords:
            existing = db.query(Keyword).filter(Keyword.user_id == user.id, Keyword.keyword == kw).first()
            if not existing:
                db.add(Keyword(keyword=kw, user=user))
        db.commit()
        keywords.clear()  # Optionally clear memory
        return {"status": "success", "message": "Keywords saved after interview."}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)