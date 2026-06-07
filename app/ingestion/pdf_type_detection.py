import pymupdf

async def get_pdf_type(pdf_bytes: bytes) -> str:

    doc = pymupdf.open(stream = pdf_bytes)

    max_page = min(3, len(doc))
    total_text = ""

    for i in range(max_page):
        page = doc[i]
        total_text += page.get_text().strip()

    doc.close()
    
    if len(total_text) > 100:
        return "native"
    else: 
        return "vision"