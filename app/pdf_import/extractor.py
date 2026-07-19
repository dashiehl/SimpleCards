from __future__ import annotations

from dataclasses import dataclass

import fitz


@dataclass
class TextSpan:
    text: str
    font: str
    size: float
    flags: int
    page_number: int

    @property
    def is_italic(self) -> bool:
        return bool(self.flags & 2**1)


def extract_spans(pdf_path: str) -> list[TextSpan]:
    """Extract every non-empty text span from a PDF, in reading order, with font metadata."""
    spans: list[TextSpan] = []
    doc = fitz.open(pdf_path)
    try:
        for page_number, page in enumerate(doc):
            page_dict = page.get_text("dict")
            for block in page_dict["blocks"]:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                        spans.append(TextSpan(
                            text=text, font=span["font"], size=round(span["size"], 1),
                            flags=span["flags"], page_number=page_number,
                        ))
    finally:
        doc.close()
    return spans


def page_count(pdf_path: str) -> int:
    doc = fitz.open(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()
