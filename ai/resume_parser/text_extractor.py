import fitz


class ResumeTextExtractor:
    """Extracts raw text and metadata from a PDF resume using PyMuPDF."""

    @staticmethod
    def extract_text(file_path: str) -> str:
        text_parts: list[str] = []
        with fitz.open(file_path) as doc:
            for page in doc:
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(page_text)
        return "\n".join(text_parts).strip()

    @staticmethod
    def extract_metadata(file_path: str) -> dict:
        with fitz.open(file_path) as doc:
            return {
                "page_count": doc.page_count,
                "title": doc.metadata.get("title"),
                "author": doc.metadata.get("author"),
            }
