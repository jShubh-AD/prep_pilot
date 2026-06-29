from langchain_core.messages import HumanMessage
from app.core.llm import scanned_llm, base_llm
import base64

VISION_SYSTEM_PROMPT = """You are a technical image analyst for an exam prep RAG system.
Your job is to describe images extracted from educational PDFs so they can be stored as searchable text.
Focus on:
- Diagrams: describe structure, components, labels, and relationships
- Charts/graphs: describe axes, values, trends
- Tables: describe headers and key data points
- Flowcharts: describe steps and flow
Be concise but complete. Do not say "this image shows" — just describe directly."""

async def describe_image(image_bytes: bytes, image_format: str = "png") -> str:    
    response = await base_llm.ainvoke(
        HumanMessage(
            content=[
                {"type": "image_url", "image_url": {"url": f"data:image/{image_format};base64,{base64.b64encode(image_bytes).decode()}"}},
                {"type": "text", "text": VISION_SYSTEM_PROMPT}
            ])
        )
    if isinstance(response.content, str):
        return response.content
    return response.content[0].get("text", "")
        

SCANNED_SYSTEM_PROMPT = """
Your task is to extract content as semantically meaningful chunks ready for RAG indexing.

CHUNKING RULES:
- Split by semantic meaning — each chunk must be a complete, self-contained piece of information
- Never split mid-concept, mid-explanation, or mid-table.
- Make large chunks and try to preserve as much context as possible in 1 chunk.
- Merge short related points together — no chunk should be smaller than 3-4 sentences

FORMATTING RULES:
- Use #/##/### for headings
- Tables: single chunk, columnar format. Ex: "names: name1, name2, name3 | ages: 20, 21, 22"
- Diagrams: describe inline. Ex: "<!-- IMAGE_START --> bar chart showing... <!-- IMAGE_END -->"

IGNORE:
- Repetitive headers/footers, Page numbers, watermarks, roll nnumbers or metadata-level information
"""

async def describe_scanned_pages(page_bytes_list: list[tuple[int, bytes]]) -> list[dict]:
    message = HumanMessage(
        content=[
            *[
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"}}
                for _, image_bytes in page_bytes_list
            ],
            {"type": "text", "text": SCANNED_SYSTEM_PROMPT}
        ])
    try:
        response = await scanned_llm.ainvoke([message])
        return response.chunks
    except Exception as e:
        raise e
