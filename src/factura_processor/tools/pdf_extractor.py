"""Local PDF text extraction with pypdfium2 — no API costs."""

import logging

import pypdfium2 as pdfium

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Concatenate the text from every page of a PDF.

    Backed by PDFium, so it works on PDFs with a real text layer. Scanned
    image-only PDFs will come back empty — caller decides what to do.
    """
    doc = pdfium.PdfDocument(pdf_bytes)
    page_texts: list[str] = []

    for i in range(len(doc)):
        try:
            page = doc[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            if text.strip():
                page_texts.append(text.strip())
        except Exception:
            logger.warning("Could not extract text from page %d", i)

    full_text = "\n\n".join(page_texts)
    logger.debug("Extracted %d characters across %d pages", len(full_text), len(doc))
    return full_text
