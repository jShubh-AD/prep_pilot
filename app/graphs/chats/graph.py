from langgraph.graph import StateGraph, START, END
from app.graphs.chats.states import QueryState
from app.graphs.chats.nodes import query_embeddings, retrieve_chunks, intent_analyser


def route_query(state: QueryState):
    analysis = state.get("analysis")
    if not analysis:
        return END
    
    # Direct bypass for safety, code refusal, or non-retrieval modes
    if analysis.retrieval_mode == "none" or analysis.intent in ("unsafe", "code_generation"):
        return END
        
    return "query_embeddings"


# query graph builder
build_query_graph = StateGraph(QueryState)

# create nodes
build_query_graph.add_node("intent_analyser", intent_analyser)
build_query_graph.add_node("query_embeddings", query_embeddings)
build_query_graph.add_node("retrieve_chunks", retrieve_chunks)

# create edges
build_query_graph.add_edge(START, "intent_analyser")
build_query_graph.add_conditional_edges(
    "intent_analyser",
    route_query,
    {
        "query_embeddings": "query_embeddings",
        END: END
    }
)
build_query_graph.add_edge("query_embeddings", "retrieve_chunks")
build_query_graph.add_edge("retrieve_chunks", END)

query_graph = build_query_graph.compile()