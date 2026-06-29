from app.core.settings import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import asyncio
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
    max_retries = 3
    base_delay = 2.0  # seconds

    llm = ChatGoogleGenerativeAI(model= "gemini-2.5-flash-lite", api_key=settings.GEMINI_API_KEY)
    
    for attempt in range(max_retries):
        try:
            response = await llm.ainvoke(
                HumanMessage(content=[
                    {"type": "image_url", "image_url": {"url": f"data:image/{image_format};base64,{base64.b64encode(image_bytes).decode()}"}},
                    {"type": "text", "text": VISION_SYSTEM_PROMPT}
                ])
            )
            return response.content[0]["text"]
        except Exception as e:
            is_transient = any(status in str(e) for status in ["503", "429", "UNAVAILABLE", "ResourceExhausted"])
            if is_transient and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"Gemini API 503/429 error, retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(delay)
            else:
                raise e

SCANNED_SYSTEM_PROMPT = """
Your task is to extract content as semantically meaningful chunks ready for RAG indexing.

CHUNKING RULES:
- Split by semantic meaning — each chunk must be a complete, self-contained piece of information
- Never split mid-concept, mid-explanation, or mid-table
- Merge short related points together — no chunk should be smaller than 3-4 sentences

FORMATTING RULES:
- Use #/##/### for headings
- Tables: single chunk, columnar format. Ex: "names: name1, name2, name3 | ages: 20, 21, 22"
- Diagrams: describe inline. Ex: "<!-- IMAGE_START --> bar chart showing... <!-- IMAGE_END -->"

IGNORE:
- Repetitive headers/footers, Page numbers, watermarks, or metadata-level information
"""

from app.schemas.gemini_chunk import GeminiChunkList

async def describe_scanned_pages(page_bytes_list: list[tuple[int, bytes]]) -> list[dict]:
    message = HumanMessage(
        content=[
            *[
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"}}
                for _, image_bytes in page_bytes_list
            ],
            {"type": "text", "text": SCANNED_SYSTEM_PROMPT}
        ])
    llm = ChatGoogleGenerativeAI(model= "gemini-2.5-flash-lite", api_key=settings.GEMINI_API_KEY)
    structured_llm = llm.with_structured_output(GeminiChunkList)

    max_retries = 3
    base_delay = 2.0  # seconds

    for attempt in range(max_retries):
        try:
            response = await structured_llm.ainvoke([message])
            return response.chunks
        except Exception as e:
            is_transient = any(status in str(e) for status in ["503", "429", "UNAVAILABLE", "ResourceExhausted"])
            if is_transient and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"Gemini API 503/429 error, retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(delay)
            else:
                raise e
