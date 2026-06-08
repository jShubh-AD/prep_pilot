import pymupdf
from app.models.raw_text_blocks import RawTextBlock, Metadata


async def extract_text(pdf_bytes: bytes, source_file: str, subject: str):
    """
    Extracts text blocks from a native PDF.
    Each block becomes a raw chunk candidate before splitting.
    """

    doc = pymupdf.open(stream = pdf_bytes)
    raw_blocks = []

    for page_no in range(len(doc)):
        page = doc[page_no]
        text = page.get_text()

        if not text.strip():
            continue

        raw_blocks.append(
            RawTextBlock(
                text=text.strip(),
                metadata=Metadata(
                    source_file= source_file,
                    page_no= page_no,
                    source_type= "native_pdf",
                    content_type= "text",
                    subject= subject
                    )
                )
            )
    
    doc.close()
    return raw_blocks