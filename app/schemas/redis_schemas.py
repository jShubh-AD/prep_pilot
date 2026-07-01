from pydantic import BaseModel

class Session(BaseModel):
    user_id: str | None = None
    session_key: str
    is_guest: bool=True
    tokens_used: int
    messages_count: int


class Message(BaseModel):
    r: str
    c: str

class ChatMessages(BaseModel):
    messages: list[Message] = []