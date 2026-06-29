# app/core/llm.py

from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.settings import settings
from app.schemas.gemini_chunk import GeminiChunkList

_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite", 
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash",
]

def _make_chain(schema=None):
    llms = [
        ChatGoogleGenerativeAI(model=m, api_key=settings.GEMINI_API_KEY)
        for m in _MODELS
    ]
    if schema:
        chains = [llm.with_structured_output(schema) for llm in llms]
    else:
        chains = llms  # plain chat, no structured output

    return chains[0].with_fallbacks(chains[1:])


# one instance per use-case, created once at import time
base_llm = _make_chain()                          # plain generation (query node, etc)
scanned_llm = _make_chain(GeminiChunkList)        # scanned page extraction