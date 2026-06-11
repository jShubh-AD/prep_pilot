from google import genai
from google.genai import types
from app.models.chunks import Chunk
from app.core.settings import settings
import time

client = genai.Client(api_key=settings.GEMINI_API_KEY)

EMBEDDING_MODEL = "gemini-embedding-001"
BATCH_SIZE = 50


def embed_batch_chunks(chunks: list[Chunk]) -> list[list[float]]:
    """
    Embeds chunks's text in batches of 50.
    Returns a list of embeddings(list[float]).
    """
    chunks_text =  [c.text for c in chunks]

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=chunks_text,
        config= types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=768
        )
    )

    return [e.values for e in result.embeddings]


def embed_chunks(chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
    """
    Embeds a list of chunks.
    Returns list of (chunk, embedding) pairs.
    
    Note: free tier limit is 1500 requests/min for embedding-001
    sleep of 2 sec is needed if you have 1500+ chunks in one PDF.
    """
    embedded = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        batch_embedings = embed_batch_chunks(batch)

        embedded.extend(zip(batch, batch_embedings))

        print(i // BATCH_SIZE +1)

    return embedded


def embed_query(query: str) -> list[float]:
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=768
        )
    )
    return result.embeddings[0].values