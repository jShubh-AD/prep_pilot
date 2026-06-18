from pydantic import BaseModel

class Session(BaseModel):
    user_id: str | None = None
    is_guest: bool=True
    tokens_used: int
    messages_count: int


class Message(BaseModel):
    role: str
    content: str

class ChatMessages(BaseModel):
    messages: list[Message] = []