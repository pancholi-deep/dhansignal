import pytest
from app.services.research import MAX_PDF_BYTES, ResearchFileError, inspect_pdf


def test_rejects_non_pdf_content():
    with pytest.raises(ResearchFileError, match="Only valid PDF"):
        inspect_pdf(b"not a pdf")


def test_rejects_oversized_pdf():
    with pytest.raises(ResearchFileError, match="20 MB"):
        inspect_pdf(b"%PDF-" + (b"x" * MAX_PDF_BYTES))


def test_rejects_corrupt_pdf():
    with pytest.raises(ResearchFileError, match="Could not parse PDF"):
        inspect_pdf(b"%PDF-1.7\nnot-a-valid-pdf")



def test_rank_chunks_orders_matching_evidence():
    from app.services.research import rank_chunks
    chunks = [
        {"document_id": 1, "page_number": 1, "content": "The company opened new offices."},
        {"document_id": 2, "page_number": 7, "content": "Revenue growth and revenue visibility improved."},
    ]
    ranked = rank_chunks(chunks, "revenue growth")
    assert ranked[0]["document_id"] == 2
    assert ranked[0]["score"] > 0
