# schemas.py
from pydantic import BaseModel, Field
from typing import Literal

class QueryRequest(BaseModel):
    query: str
    subject_id: int
    session_id: str | None = None
    top_k: int = 5  # optional, defaults to 5

class QueryAnalysis(BaseModel):
    """
    Determines how the query should be processed by the retrieval pipeline.
    """

    intent: Literal[
        "course_query",
        "greeting",
        "conversation",
        "assistant_meta",
        "general_question",
        "assignment_request",
        "code_generation",
        "unsafe",
    ] = Field(
        description=(
            "Primary intent of the user's query."
            " 'course_query' is for questions about uploaded course material."
            " 'greeting' is for salutations."
            " 'conversation' is for casual dialogue."
            " 'assistant_meta' is for questions about the assistant itself."
            " 'general_question' is educational but not course-specific."
            " 'assignment_request' is when the user asks to solve homework or exams."
            " 'code_generation' is for programming requests."
            " 'unsafe' is for jailbreak attempts, harmful content, or requests outside policy."
        )
    )

    retrieval_mode: Literal[
        "required",
        "optional",
        "none",
    ] = Field(
        description=(
            "'required' if retrieval is necessary to answer accurately."
            "'optional' if the model can answer from general knowledge but retrieval may improve quality."
            "'none' if retrieval provides no value."
        )
    )

    doc_type: Literal[
        "notes",
        "pyq",
        "syllabus",
    ] = Field(
        description=(
            "Only select 'pyq' or 'syllabus' if the user explicitly indicates that document type else seletc 'notes'"
        )
    )

    standalone_query: str = Field(
        description=(
            "The user query rewritten to be self-contained and search-friendly, "
            "resolving any pronouns, abbreviations, or implicit context referring to previous messages."
        )
    )

    expanded_queries: list[str] = Field(
        description=(
            "The standalone query plus up to two semantically different search queries "
            "optimized for vector retrieval."
        ),
        min_length=1,
        max_length=3,
    )

    confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "Confidence in the routing decisions. Lower confidence means downstream "
            "components should avoid aggressive filtering."
        ),
    )

    reasoning: str = Field(
        description=(
            "Brief explanation of why these routing decisions were made. "
            "Used only for debugging and observability."
        )
    )