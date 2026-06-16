from google import genai
from google.genai import types
from app.core.settings import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

VISION_SYSTEM_PROMPT = """You are a technical image analyst for an exam prep RAG system.
Your job is to describe images extracted from educational PDFs so they can be stored as searchable text.
Focus on:
- Diagrams: describe structure, components, labels, and relationships
- Charts/graphs: describe axes, values, trends
- Tables: describe headers and key data points
- Flowcharts: describe steps and flow
Be concise but complete. Do not say "this image shows" — just describe directly."""

import time

def describe_image(image_bytes: bytes, image_format: str = "png") -> str:
    max_retries = 3
    base_delay = 2.0  # seconds
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=f"image/{image_format}"
                ),
                config=types.GenerateContentConfig(
                    system_instruction=VISION_SYSTEM_PROMPT,
                    temperature=0.1
                )
            )
            return response.text.strip()
        except Exception as e:
            is_transient = any(status in str(e) for status in ["503", "429", "UNAVAILABLE", "ResourceExhausted"])
            if is_transient and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"Gemini API 503/429 error, retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
            else:
                raise e