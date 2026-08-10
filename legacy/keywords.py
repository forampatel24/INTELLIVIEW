import pdfplumber
from rake_nltk import Rake
import nltk

# Make sure stopwords are downloaded
nltk.download('punkt_tab')
nltk.download('stopwords')

# Extract text using pdfplumber
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# Extract keywords using RAKE
def extract_keywords(text, max_keywords=15):
    rake = Rake()  # uses NLTK stopwords
    rake.extract_keywords_from_text(text)
    keywords = rake.get_ranked_phrases()
    return keywords[:max_keywords]

# Main function
pdf_path = "Foram Patel.pdf"  # Replace with your PDF file path

try:
    print("\n🔍 Extracting text from the PDF...")
    resume_text = extract_text_from_pdf(pdf_path)

    if not resume_text.strip():
        print("❌ No readable text found in the PDF.")
    else:
        print("\n🧠 Extracting keywords from resume...\n")
        keywords = extract_keywords(resume_text)

        print("✅ Keywords Found:")
        for i, keyword in enumerate(keywords, 1):
            print(f"{i}. {keyword}")

except Exception as e:
    print(f"❌ Error: {e}")
