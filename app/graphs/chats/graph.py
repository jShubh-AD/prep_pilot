from langgraph.graph import StateGraph, START, END
from app.graphs.chats.states import QueryState
from app.graphs.chats.nodes import query_expansion, query_embedings, retrive_chunks, generate_response

# query graph builder
build_query_graph = StateGraph(QueryState)

# create nodes
build_query_graph.add_node("query_expansion", query_expansion)
build_query_graph.add_node("query_embedings", query_embedings)
build_query_graph.add_node("retrive_chunks", retrive_chunks)
build_query_graph.add_node("generate_response", generate_response)


# create edges
build_query_graph.add_edge(START, "query_expansion")
build_query_graph.add_edge("query_expansion", "query_embedings")
build_query_graph.add_edge("query_embedings", "retrive_chunks")
build_query_graph.add_edge("retrive_chunks","generate_response")
build_query_graph.add_edge("generate_response", END)

query_graph = build_query_graph.compile()