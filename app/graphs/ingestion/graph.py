from langgraph.graph import StateGraph, END, START
from app.graphs.ingestion.state import IngestionState
from app.graphs.ingestion.nodes import (
    get_pdf_type,
    extract_native_batch,
    extract_scanned_batch,
    create_chunks,
    embed_chunks,
    store_embedings
)

builder = StateGraph(IngestionState)

# create nodes
builder.add_node("get_pdf_type", get_pdf_type)
builder.add_node("extract_native_batch", extract_native_batch)
builder.add_node("extract_scanned_batch", extract_scanned_batch)
builder.add_node("create_chunks", create_chunks)
builder.add_node("embed_chunks", embed_chunks)
builder.add_node("store_embedings", store_embedings)

# create edges
builder.add_edge(START, "get_pdf_type")

# Route after getting PDF type
builder.add_conditional_edges(
    "get_pdf_type",
    lambda state: state["pdf_type"],
    {"native": "extract_native_batch", "vision": "extract_scanned_batch"}
)

# Native path
builder.add_edge("extract_native_batch", "create_chunks")
builder.add_edge("create_chunks", "embed_chunks")

# Vision path
builder.add_edge("extract_scanned_batch", "embed_chunks")

# Shared paths
builder.add_edge("embed_chunks", "store_embedings")


# Loop routing after storing embeddings
def route_after_store(state: IngestionState):
    current_page = state.get("current_page", 0)
    total_pages = state.get("total_pages", 0)
    
    if current_page < total_pages:
        return state.get("pdf_type", "native")
    return "done"


builder.add_conditional_edges(
    "store_embedings",
    route_after_store,
    {
        "native": "extract_native_batch",
        "vision": "extract_scanned_batch",
        "done": END
    }
)

ingestion_graph = builder.compile()