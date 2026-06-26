from langgraph.graph import StateGraph, END, START
from app.graphs.ingestion.state import IngestionState
from app.graphs.ingestion.nodes import get_pdf_type, extract_native, extract_scanned_pdf, create_chunks, embed_chunks, store_embedings

builder = StateGraph(IngestionState)


# create nodes
builder.add_node("get_pdf_type", get_pdf_type)
builder.add_node("extract_native", extract_native)
builder.add_node("extract_scanned_pdf", extract_scanned_pdf)
builder.add_node("create_chunks", create_chunks)
builder.add_node("embed_chunks",embed_chunks)
builder.add_node("store_embedings", store_embedings)

# create edges
builder.add_edge(START, "get_pdf_type")
builder.add_conditional_edges(
    "get_pdf_type",
    lambda state: state["pdf_type"],
    {"native":"extract_native", "vision":"extract_scanned_pdf"}
    )
builder.add_edge("extract_scanned_pdf", "embed_chunks")
builder.add_edge("extract_native", "create_chunks")
builder.add_edge("create_chunks","embed_chunks")
builder.add_edge("embed_chunks", "store_embedings")
builder.add_edge("store_embedings", END)

ingestion_graph = builder.compile()