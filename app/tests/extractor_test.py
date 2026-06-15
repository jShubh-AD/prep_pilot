# test_extractor.py in your root folder
import asyncio
import pymupdf
from app.ingestion.text_extractor import extract_text

async def main():
    with open("data/attention.pdf", "rb") as f:
        pdf_bytes = f.read()
    
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    new_doc = pymupdf.open()
    new_doc.insert_pdf(doc, from_page=3, to_page=3)
    
    import io
    page3_bytes = io.BytesIO()
    new_doc.save(page3_bytes)
    page3_bytes = page3_bytes.getvalue()
    
    result = await extract_text(page3_bytes, "attention.pdf", "attention", "attention")
    print(result.content)

asyncio.run(main())