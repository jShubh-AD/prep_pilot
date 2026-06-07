from google import genai
from google.genai import types
from app.models.chunks import Chunk
from app.core.settings import settings
import time

client = genai.Client(api_key=settings.GEMINI_API_KEY)

EMBEDDING_MODEL = "gemini-embedding-001"


def embed_chunk(chunk: Chunk) -> list[float]:
    """
    Embeds a single chunk's text.
    Returns a list of 768 floats.
    """
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=chunk.text,
        config= types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=786
        )
    )
    return result.embeddings[0].values


def embed_chunks(chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
    """
    Embeds a list of chunks.
    Returns list of (chunk, embedding) pairs.
    
    Note: free tier limit is 1500 requests/min for text-embedding-004
    No sleep needed unless you have 1500+ chunks in one PDF.
    """
    embedded = []

    for i, chunk in enumerate(chunks):
        embedding = embed_chunk(chunk)
        embedded.append((chunk, embedding))
        
        # progress log — useful for large PDFs
        if (i + 1) % 10 == 0:
            print(f"[embedder] embedded {i + 1}/{len(chunks)} chunks")
            time.sleep(2)

    return embedded


def embed_query(query: str) -> list[float]:
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=786
        )
    )
    return result.embeddings[0].values