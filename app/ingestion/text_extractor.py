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
        blocks = page.get_text("blocks")

        for block in blocks:
            x0, y0, x1, y1, text, block_no, block_type = block

            if block_type == 0 and text.strip():
                raw_blocks.append(
                    RawTextBlock(
                    text=text.strip(),
                    metadata=Metadata(
                        source_file= source_file,
                        page_no= page_no,
                        block_no= block_no,
                        source_type= "native_pdf",
                        content_type= "text",
                        subject= subject
                        )
                    )
                )
    
    doc.close()
    return raw_blocks


        


