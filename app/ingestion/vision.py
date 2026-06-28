from app.core.settings import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

VISION_SYSTEM_PROMPT = """You are a technical image analyst for an exam prep RAG system.
Your job is to describe images extracted from educational PDFs so they can be stored as searchable text.
Focus on:
- Diagrams: describe structure, components, labels, and relationships
- Charts/graphs: describe axes, values, trends
- Tables: describe headers and key data points
- Flowcharts: describe steps and flow
Be concise but complete. Do not say "this image shows" — just describe directly."""

import time

async def describe_image(image_bytes: bytes, image_format: str = "png") -> str:
    max_retries = 3
    base_delay = 2.0  # seconds
    
    for attempt in range(max_retries):
        try:
            llm = ChatGoogleGenerativeAI(model= "gemini-2.5-flash-lite", api_key=settings.GEMINI_API_KEY)
            response = await llm.ainvoke(
                HumanMessage(content=[
                    {"type": "image_url", "image_url": {"url": f"data:image/{image_format};base64,{image_bytes}"}},
                    {"type": "text", "text": VISION_SYSTEM_PROMPT}
                ])
            )
            return response.content[0]["text"]
        except Exception as e:
            is_transient = any(status in str(e) for status in ["503", "429", "UNAVAILABLE", "ResourceExhausted"])
            if is_transient and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"Gemini API 503/429 error, retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
            else:
                raise e
            

from google import genai
from google.genai import types
from app.schemas.gemini_chunk import GeminiChunk
import json
from app.core.settings import  settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

SCANNED_SYSTEM_PROMPT = """You are a technical document analyst for an exam prep RAG system.
You will receive multiple scanned PDF pages as images.

Your task is to extract content as semantically meaningful chunks ready for RAG indexing.

CHUNKING RULES:
- Split by semantic meaning — each chunk must be a complete, self-contained piece of information
- Each heading and its full content form one chunk
- Never split mid-concept, mid-explanation, or mid-table
- Merge short related points together — no chunk should be smaller than 3-4 sentences

FORMATTING RULES:
- Use # for main headings, ## for subheadings, ### for topics/subtopics
- For tables, convert to a compact columnar format in a single chunk: start with "Table: [title/topic]", then list each column name followed by its values
- For diagrams or images, describe them inline where they appear, wrapped in <!-- IMAGE_START --> and <!-- IMAGE_END --> tags

IGNORE:
- Repetitive headers or footers that do not add context
- Page numbers, watermarks, or metadata-level information

Return ONLY a JSON array of chunk objects, no other text."""

import asyncio

async def describe_scanned_pages(page_bytes_list: list[tuple[int, bytes]]) -> list[dict]:
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        for _, image_bytes in page_bytes_list
    ]

    max_retries = 3
    base_delay = 2.0  # seconds

    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SCANNED_SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=list[GeminiChunk]
                )
            )
            return json.loads(response.text.strip())
        except Exception as e:
            is_transient = any(status in str(e) for status in ["503", "429", "UNAVAILABLE", "ResourceExhausted"])
            if is_transient and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"Gemini API 503/429 error, retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(delay)
            else:
                raise e
