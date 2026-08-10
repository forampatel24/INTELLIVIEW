import pdfplumber

try:
    # Replace 'sample.pdf' with the path to your PDF file
    with pdfplumber.open("Image Processing and Dataset Creation.pdf") as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        if text:
            print("✅ pdfplumber is working! Here's a preview of the text:\n")
            print(text[:500])  # Print first 500 characters
        else:
            print("⚠️ pdfplumber is working but couldn't extract text. The page may be image-based.")
except Exception as e:
    print(f"❌ Something went wrong: {e}")
