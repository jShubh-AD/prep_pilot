import asyncio
import pymupdf
from app.ingestion.scanned_extractor import extract_scanned_pdf

async def main():
    doc = pymupdf.open("data/DBMS_OCR.pdf")

     # only take first 10 pages
    new_doc = pymupdf.open()
    new_doc.insert_pdf(doc, from_page=0, to_page=12)

    import io
    page_bytes = io.BytesIO()
    new_doc.save(page_bytes)
    pdf_bytes = page_bytes.getvalue()
    
    chunks = await extract_scanned_pdf(pdf_bytes, "DBMS_OCR.pdf", "DBMS_OCR", "DBMS_OCR")
    
    print(f"Total chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i} ---")
        print(chunk.text)

asyncio.run(main())