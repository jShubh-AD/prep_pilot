import pymupdf4llm
import pymupdf
from app.schemas.md_model import MdModel
import re
from app.ingestion.vision import describe_image

PLACEHOLDER_PATTERN = re.compile(r'==>.*?<==')

async def extract_text(
        pdf_bytes: bytes, 
        source_file: str,
        subject: str, 
        subject_id: str) ->  MdModel:
    """
    Extracts Full Doc from a native PDF in markdown.
    """

    doc = pymupdf.open(stream=pdf_bytes)
    pages_md =[]

    for page_no in range(len(doc)):
        md = pymupdf4llm.to_markdown(doc, pages = [page_no], header =False, footer = False)
        if not md.strip():
            continue

        images = doc[page_no].get_images()

        print(images)

        if images:
            md = re.sub(r'\*\*(==>.*?<==)\*\*', r'\1', md)
            placeholders = PLACEHOLDER_PATTERN.findall(md)
            for img_tuple, placeholder in zip(images, placeholders):
                try:
                    xref = img_tuple[0]
                    image_data = doc.extract_image(xref)
                    image_bytes = image_data["image"]
                    image_format = image_data["ext"]
                    description = describe_image(image_bytes, image_format)
                    print(f"description: {description}")
                    wrapped = f"<!-- IMAGE_START -->\n{description}\n<!-- IMAGE_END -->"
                    md = md.replace(placeholder, wrapped, 1)
                except Exception as e:
                    print(f"Error: {e}")
                    md = md.replace(placeholder, "", 1)

        pages_md.append(f"<!-- page {page_no} -->\n{md}")
    doc.close()

    full_markdown = "\n".join(pages_md)

    return MdModel(
        content=full_markdown,
        source_file=source_file,
        subject=subject,
        subject_id=subject_id
    )