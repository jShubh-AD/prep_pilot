import pymupdf4llm
import pymupdf
from app.models.md_model import MdModel


async def extract_text(
        pdf_bytes: bytes, 
        source_file: str,
        subject: str, 
        subject_id: str) ->  MdModel:
    """
    Extracts Full Doc from a native PDF in markdown.
    """

    doc = pymupdf.open(stream=pdf_bytes, )
    pages_md =[]

    for page_no in range(len(doc)):
        md = pymupdf4llm.to_markdown(doc, pages = [page_no], header =False, footer = False)
        if not md.strip():
            continue
        pages_md.append(f"<!-- page {page_no} -->\n{md}")
    doc.close()

    full_markdown = "\n".join(pages_md)

    return MdModel(
        content=full_markdown,
        source_file=source_file,
        source_type="native_pdf",
        subject=subject,
        subject_id=subject_id
    )