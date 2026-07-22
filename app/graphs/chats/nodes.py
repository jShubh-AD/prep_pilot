from langchain_google_genai import GoogleGenerativeAIEmbeddings
from fastapi import Request
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.chroma_db import get_or_create_collection
from app.graphs.chats.states import QueryState
from app.core.settings import settings
from collections import defaultdict
from app.schemas.chunks import Chunk
from app.core.redis_servcie import get_chat_session_key, Redis, get_chat_summary_key
from fastapi import HTTPException
import asyncio
import base64
import json
import time
from app.core.llm import base_llm, intent_llm
from app.schemas.query import QueryAnalysis
from google.genai import types
from google import genai


AUDIO_MODEL="models/gemini-3.1-flash-live-preview"

INTENT_PROMPT = """You are PrepPilot's routing engine.
Analyze the current user query and, if provided, the conversation history.
Do not answer the question.
Return only the structured output.

Rules:
- Default doc_type to "notes". Choose "pyq" or "syllabus" only when explicitly requested.
- Rewrite the query into a standalone query by resolving references from history.
- Generate at most three expanded queries including the standalone query.
- Generate summary of Conversation History while preserving all the key details and the core of conversation.
- Keep the summary in bullet points, whihc may help llm for further reasoning and answering. 
- if there is no conversation keep the related filed None.
- do not include user's current query in summary. only sumaries the previous chats.
"""

# intent node
async def intent_analyser(state: QueryState):
    from app.core.redis_servcie import get_redis
    redis = get_redis()
    chats_key = get_chat_session_key(session_id=state["session_id"], subject_id=state["subject_id"])
    chat_summary_key = get_chat_summary_key(session_id=state["session_id"], subject_id=state["subject_id"])

    chat_summary =  await redis.get(chat_summary_key)

    history_messages = []
    if chat_summary:
        history_messages.append(f"Conversation Summary:\n{chat_summary}\n")
        for msg in await redis.lrange(name=chats_key, start= -4, end= -1):
            data = json.loads(msg)
            role = 'User' if data['r'] == 'u' else "Assistant"
            history_messages. append(f"{role}: {data['c']}")
    else:
        # Fetch last 20 messages for conversational context
        for msg in await redis.lrange(name=chats_key, start=-20, end=-1):
            data = json.loads(msg)
            role = "User" if data["r"] == "u" else "Assistant"
            history_messages.append(f"{role}: {data['c']}")
    
    history_context = "\n".join(history_messages)
    
    system_message = SystemMessage(content=INTENT_PROMPT)
    user_content = f"Conversation History:\n{history_context}\n\nUser Query: {state['query']}"
    human_message = HumanMessage(content=user_content)
    response: QueryAnalysis = await intent_llm.ainvoke([system_message, human_message])
    if response.chat_summary is not None and chat_summary != response.chat_summary:
        result = await redis.set(
            chat_summary_key,
            response.chat_summary,
            keepttl=86400,
        )
        print(result)

    print(f"""
        [INTENT]: {response.intent}
        [REASONING]: {response.reasoning}
        [CONFIDENCE]: {response.confidence}
        [RETRIVAL]: {response.retrieval_mode}
        [DOC_TYPE]: {response.doc_type}
    """)
    print(f"[CHAT SUMMARY]: {response.chat_summary}")
    return {
        "analysis": response,
        "expanded_queries": response.expanded_queries
    }

async def query_embeddings(state: QueryState):
    """
    **Node for QueryGraph**, used to generate batch embeddings for all queries.\n
    **Model used** = gemini-embedding-2
    """
    embedder = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2", api_key=settings.GEMINI_API_KEY)
    embeddings = await embedder.aembed_documents(
        texts=state['expanded_queries'], 
        task_type="RETRIEVAL_QUERY", 
        output_dimensionality= 768
    )
    if not embeddings:
        raise HTTPException(
            status_code=400,
            detail="Could not create embeddings, please try again."
        )
    return {"embeddings": embeddings}

async def retrieve_chunks(state: QueryState):
    """
    **Node for QueryGraph**, used to extract top chunks for each query from ChromaDB.\n
    and returns list[Chunk], with retrieval frequency
    """
    db = get_or_create_collection()
    analysis = state["analysis"]
    
    target_doc_type = analysis.doc_type if analysis else None

    where = {}
    where["subject_id"] = state["subject_id"]
    if target_doc_type:
        where["doc_type"] = target_doc_type
    if len(where) > 1:
        where = {"$and": [{k: v} for k, v in where.items()]}

    results = db.query(
        query_embeddings=state["embeddings"],
        n_results=5,
        where=where
    )

    seen = {}
    freq = defaultdict(int)

    for ids, docs, metas, distances in zip(
        results["ids"],
        results["documents"],
        results["metadatas"],
        results["distances"]
    ):
        for chunk_id, doc, meta, distance in zip(
            ids, docs, metas, distances
        ):
            freq[chunk_id] += 1

            if chunk_id not in seen:
                seen[chunk_id] = {
                    "text": doc,
                    "metadata": meta,
                }

    output = []
    num_queries = len(state["expanded_queries"])

    for chunk_id, chunk in seen.items():
        score = round(freq[chunk_id] / num_queries, 2)
        output.append(
            Chunk(
                text=chunk["text"],
                metadata=chunk["metadata"],
                confidence=score
            )
        )

    # Sort chunks by confidence score descending
    output.sort(key=lambda x: x.confidence or 0.0, reverse=True)

    print(f"[OUTPUTS]: {output}")
    if not output:
        raise HTTPException(400,"I'm sorry, but I couldn't find any relevant information on that topic in my course materials.")
    return {"chunks": output}


SYSTEM_PROMPT = """You are Sakshi (didi), an expert of {subject}.
You are from India and ahve been developer by PrepPilot Team.
You have years of teaching experience, you help students plan, understand, revise and prepare for exams.
Ground your response strictly in the provided course context.
Carefully review the user_intent_reasoning, and understand what and why behind the user's query.
Try to answere based on the context and chat_summary, not sufficient to answer then responde with a polite reply.

If the user's intent is identified as 'assignment_request', explain the concepts and teach the solution using guidance and hints; do NOT generate final, copy-pasteable answers.
If the user's intent is 'assistant_meta', 'greeting', 'conversation', 'general_questions', you may reply directly and helpfully from your own knowledge.
your reply should match the functions of the user query ex: Language, Tone, Mood etc...
"""

async def build_text_messages(state: QueryState):
    chats_key = get_chat_session_key(session_id=state["session_id"], subject_id=state["subject_id"])

    def format_chunk(chunk: Chunk):
        meta = chunk.metadata
        return (
            f"[Source: {meta.source_file}"
            f" | Subject: {meta.subject}"
            f" | Type: {meta.doc_type}"
            f" | Confidence: {chunk.confidence}]\n"
            f"{chunk.text}"
        )
    context = "\n\n".join(format_chunk(chunk) for chunk in state["chunks"])

    print(f"Context: {context}")
    
    query_text = state["analysis"].standalone_query if state.get("analysis") else state["query"]

    return chats_key, [
        HumanMessage(content=f"""
                    user_intent: {state['analysis'].intent}
                    user_intent_reasoning: {state['analysis'].reasoning}
                    reasoning_confidance: {state['analysis'].confidence}
                    chat_summary: {state['analysis'].chat_summary}
                    context: {context}
                    Question: {query_text}""")]

async def stream_llm_response(state: QueryState, redis: Redis, request: Request, start):
    print("[CALLING] stream_llm_response")
    analysis = state.get("analysis")
    intent = analysis.intent if analysis else "course_query"
    
    # Quick Refusals without running model generation
    if intent == "unsafe":
        yield f"event: token\ndata: {json.dumps({'text': 'I cannot help you with that request as it violates safety guidelines.', 'time': time.time()})}\n\n"
        yield "event: done\n\n"
        return
        
    if intent == "code_generation":
        msg = "PrepPilot is designed as a conceptual tutor and does not generate arbitrary programming code. Let me know if you would like me to explain the programming concepts instead!"
        yield f"event: token\ndata: {json.dumps({'text': msg, 'time': time.time()})}\n\n"
        yield "event: done\n\n"
        return

    chats_key, messages = await build_text_messages(state)
    full_text = ""

    usage = None

    if state["format"] == 'text':
        try:
            print("[stream_llm_response]: text")
            async for chunk in base_llm.astream([SystemMessage(content=SYSTEM_PROMPT.format(subject=state["subject_name"])), *messages]):
                print("[stream_llm_response]: Chunk")
                if await request.is_disconnected():
                    print("client disconnected stopping stream.")
                    return
                content = chunk.content
                if isinstance(content, str):
                    full_text += content
                    yield f"event: token\ndata: {json.dumps({'text': content, 'time': time.time()})}\n\n"
                if usage is None and chunk.usage_metadata:
                    usage = chunk.usage_metadata
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}"
            return
    else:
        config = types.LiveConnectConfig(
            system_instruction= SYSTEM_PROMPT.format(subject=state["subject_name"]),
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            media_resolution="MEDIA_RESOLUTION_MEDIUM",
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
                )
            ),
            context_window_compression=types.ContextWindowCompressionConfig(
                trigger_tokens=104857,
                sliding_window=types.SlidingWindow(target_tokens=52428),
            ),
        )
        
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        async with client.aio.live.connect(model= AUDIO_MODEL, config=config) as session:
            await session.send_client_content(
                turns=types.Content(
                    role='user',
                    parts=[types.Part(text=messages[0].content)]
                ),
                turn_complete=True,
            )
            async for event in session.receive():
                event_ot = None
                event_audio = None
                if event.usage_metadata:
                    usage = event.usage_metadata
                if event.server_content:
                    sc = event.server_content
                    if sc.output_transcription:
                        event_ot = sc.output_transcription.text
                        full_text += event_ot
                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if (part.inline_data and part.inline_data.mime_type.startswith("audio/pcm")):
                                audio = part.inline_data.data
                                event_audio = (base64.b64encode(audio).decode("ascii")if audio else None)
                    payload = {
                        "text": event_ot,
                        "audio": event_audio,
                        "time": time.time(),
                    }
                    yield f"event: token\ndata: {json.dumps(payload)}\n\n"

                    if sc.turn_complete or sc.interrupted:
                        break
            

    token_used = 0
    if state["format"] == "text":
        token_used = usage["total_tokens"] if usage else 0
    else:
        token_used = usage.total_token_count
    session = state["session"]
    session.messages_count += 2
    session.tokens_used += token_used
    try:
        await asyncio.gather(
            redis.rpush(
                chats_key,
                json.dumps({"r": "u", "c": state["query"]}),
                json.dumps({"r": "a", "c": full_text}),
            ),
            redis.set(
                name=state["session"].session_key,
                value=session.model_dump_json(),
                keepttl=True
            )
        )
    except Exception as e:
        print(f"Redis persist failed for session {state['session_id']}: {e}")

    print("Sending done event")
    yield f"""event: done\ndata: {json.dumps({
        'session_id': state['session_id'],
        'tokens_used': token_used,
        'tokens_available': 20000 - session.tokens_used,
        'total_time': round(time.time() - start, 2)
    })}\n\n"""

