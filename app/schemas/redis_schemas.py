from pydantic import BaseModel

class Session(BaseModel):
    user_id: str | None = None
    # session_id: str
    is_guest: bool=True
    tokens_used: int
    messages_count: int


class Message(BaseModel):
    role: str
    content: str

class ChatMessages(BaseModel):
    messages: list[Message] = []