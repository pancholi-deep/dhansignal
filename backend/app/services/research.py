import hashlib
import io
import os
from pathlib import Path
from pypdf import PdfReader

MAX_PDF_BYTES = 20 * 1024 * 1024
STORAGE_DIR = Path(os.getenv("RESEARCH_STORAGE_DIR", "/data/research"))


class ResearchFileError(ValueError):
    pass


def inspect_pdf(content: bytes) -> tuple[str, int, str]:
    if not content.startswith(b"%PDF-"):
        raise ResearchFileError("Only valid PDF files are supported")
    if len(content) > MAX_PDF_BYTES:
        raise ResearchFileError("PDF exceeds the 20 MB upload limit")
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise ResearchFileError("Encrypted PDFs are not supported yet")
        page_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(page_text).strip()
        if not text:
            raise ResearchFileError("No extractable text found. Scanned PDFs need OCR, which is not enabled yet.")
        return text, len(reader.pages), hashlib.sha256(content).hexdigest()
    except ResearchFileError:
        raise
    except Exception as exc:
        raise ResearchFileError(f"Could not parse PDF: {exc}") from exc


def save_pdf(content: bytes, digest: str) -> str:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    destination = STORAGE_DIR / f"{digest}.pdf"
    if not destination.exists():
        destination.write_bytes(content)
    return str(destination)
