import pdfplumber
from rake_nltk import Rake
import nltk
import google.generativeai as genai
import time

# ========== Setup ==========
nltk.download('punkt')
nltk.download('stopwords')

# API Key Setup
genai.configure(api_key="AIzaSyCgJmOVaa8jZX4REXCcx8X4BQ1TcsBxacg")  # Replace with your actual key
model = genai.GenerativeModel(model_name="models/gemini-2.0-flash")

PDF_PATH = "Foram Patel.pdf"

# ========== PDF Text Extraction ==========
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# ========== Keyword Extraction using RAKE ==========
def extract_keywords(text, max_keywords=15):
    rake = Rake()
    rake.extract_keywords_from_text(text)
    keywords = rake.get_ranked_phrases()
    return keywords[:max_keywords]

# ========== Keyword Filtering ==========
def filter_keywords(keywords):
    return [kw for kw in keywords if len(kw.split()) <= 6 and any(char.isalpha() for char in kw)]

# ========== Question Generation ==========
def generate_questions_from_keywords(keywords, batch_size=3):
    questions = []

    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i + batch_size]
        prompt = "Generate 1 technical interview question for each of the following keywords:\n\n"
        for kw in batch:
            prompt += f"- {kw}\n"
        prompt += "\nMake sure the questions are relevant, challenging, and interview-appropriate."

        try:
            response = model.generate_content(prompt)
            batch_questions = response.text.strip()
            questions.append(batch_questions)
            print(batch_questions)
            print("=" * 60)
            time.sleep(35)
        except Exception as e:
            print(f"❌ API failed for batch {batch}: {e}")
            print("=" * 60)

    return questions

# ========== Run ==========
try:
    print("📄 Extracting text from PDF...")
    resume_text = extract_text_from_pdf(PDF_PATH)

    if not resume_text.strip():
        print("⚠️ No readable text found in PDF.")
    else:
        print("🔍 Extracting keywords...")
        raw_keywords = extract_keywords(resume_text)
        filtered_keywords = filter_keywords(raw_keywords)

        print(f"✨ {len(filtered_keywords)} filtered keywords found. Generating questions...\n")
        generate_questions_from_keywords(filtered_keywords)

except Exception as e:
    print(f"❌ Error: {e}")
