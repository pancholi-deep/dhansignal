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


def chunk_pdf(content: bytes, chunk_size: int = 1400, overlap: int = 220) -> list[dict]:
    """Extract page-preserving text chunks. Page numbers are 1-based for citations."""
    reader = PdfReader(io.BytesIO(content), strict=False)
    chunks = []
    chunk_index = 0
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            if end < len(text):
                boundary = text.rfind(" ", start + chunk_size // 2, end)
                if boundary > start:
                    end = boundary
            piece = text[start:end].strip()
            if piece:
                chunks.append({"page_number": page_number, "chunk_index": chunk_index, "content": piece})
                chunk_index += 1
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return chunks


def rank_chunks(chunks: list[dict], query: str) -> list[dict]:
    """Small dependency-free lexical ranker; semantic embeddings are a later adapter."""
    import re
    terms = list(dict.fromkeys(re.findall(r"[a-zA-Z0-9₹]+", query.lower())))
    terms = [term for term in terms if len(term) > 1]
    ranked = []
    for chunk in chunks:
        content = chunk["content"]
        lowered = content.lower()
        counts = {term: lowered.count(term) for term in terms}
        score = sum(min(count, 4) * (2.0 if count else 0.0) for count in counts.values())
        if score:
            ranked.append({**chunk, "score": round(score, 2), "matched_terms": [term for term, count in counts.items() if count]})
    return sorted(ranked, key=lambda item: (-item["score"], item["document_id"], item["page_number"]))
